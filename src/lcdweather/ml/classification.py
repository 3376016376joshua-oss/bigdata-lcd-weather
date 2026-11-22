"""Question 8: logistic regression vs random forest for next-day precipitation."""

from __future__ import annotations

from pyspark.ml.classification import LogisticRegression, RandomForestClassifier
from pyspark.ml.functions import vector_to_array
from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from lcdweather.ml.binary_metrics import (
    DEFAULT_THRESHOLD,
    derive_binary_metrics,
    point_at_threshold,
)
from lcdweather.ml.classification_features import (
    CLASSIFICATION_FEATURES,
    PERSISTENCE_COL,
    build_classification_dataset,
)
from lcdweather.ml.daily_features import CITY_KEY
from lcdweather.ml.export import ResultTable
from lcdweather.ml.metrics import area_under_curves, confusion_by_group, threshold_curve
from lcdweather.ml.pipelines import FEATURES_COL, feature_weights, usable_feature_set
from lcdweather.ml.settings import (
    DEFAULT_SPLIT_YEARS,
    LABEL_COL,
    MODEL_DATA_PARTITIONS,
    RANDOM_SEED,
    SplitYears,
)
from lcdweather.ml.splits import Splits, split_by_target_year
from lcdweather.ml.tuning import ModelSpec, TunedModel, append_model_output, tune_model

TUNING_METRIC = "auc_roc"
BASELINE_NAME = "persistence"
POSITIVE_CLASS_INDEX = 1
CURVE_COLUMNS = ("threshold", "fpr", "recall", "precision", "f1")
LOGISTIC_GRIDS = {
    "full": [
        {"regParam": reg, "elasticNetParam": mix} for reg in (0.0, 0.01, 0.1) for mix in (0.0, 0.5)
    ],
    "quick": [{"regParam": 0.01, "elasticNetParam": 0.0}],
}
FOREST_GRIDS = {
    "full": [{"numTrees": trees, "maxDepth": depth} for trees in (100, 200) for depth in (5, 10)],
    "quick": [{"numTrees": 10, "maxDepth": 4}],
}


def classification_specs(grid: str) -> list[ModelSpec]:
    def logistic(**params):
        return LogisticRegression(featuresCol=FEATURES_COL, labelCol=LABEL_COL, **params)

    def forest(**params):
        return RandomForestClassifier(
            featuresCol=FEATURES_COL, labelCol=LABEL_COL, seed=RANDOM_SEED, **params
        )

    return [
        ModelSpec("logistic_regression", logistic, LOGISTIC_GRIDS[grid]),
        ModelSpec("random_forest", forest, FOREST_GRIDS[grid]),
    ]


def _wet_probability():
    return vector_to_array(F.col("probability")).getItem(POSITIVE_CLASS_INDEX)


def _validation_auc(scored: DataFrame) -> float:
    with_score = scored.withColumn("p_wet", _wet_probability())
    return area_under_curves(with_score, "p_wet")[TUNING_METRIC]


def _score(split: DataFrame, tuned: list[TunedModel], stage: str) -> DataFrame:
    scored = split
    for item in tuned:
        model = getattr(item, stage)
        scored = append_model_output(scored, model, _wet_probability(), f"p_{item.spec.name}")
    return scored.cache()


def _score_columns(tuned: list[TunedModel]) -> dict[str, str]:
    columns = {item.spec.name: f"p_{item.spec.name}" for item in tuned}
    columns[BASELINE_NAME] = PERSISTENCE_COL
    return columns


def _metric_row(model: str, split: str, point: dict, areas: dict) -> dict:
    counts = {key: point[key] for key in ("tp", "fp", "tn", "fn")}
    derived = {key: point[key] for key in ("precision", "recall", "f1", "accuracy")}
    return {
        "model": model,
        "split": split,
        "threshold": point["threshold"],
        **areas,
        **derived,
        **counts,
        "n": sum(counts.values()),
    }


def _evaluate_model(model: str, column: str, validation: DataFrame, test: DataFrame) -> dict:
    """Metrics at the 0.5 decision threshold on both splits, plus the test curve.

    Rows without a score (the persistence baseline on days with unknown
    precipitation) are left out of that model's metrics only.
    """
    splits = {"validation": validation, "test": test}
    curves = {name: threshold_curve(frame, column) for name, frame in splits.items()}
    metrics = [
        _metric_row(
            model,
            name,
            point_at_threshold(curves[name], DEFAULT_THRESHOLD),
            area_under_curves(frame, column),
        )
        for name, frame in splits.items()
    ]
    curve = [
        {"model": model, **{name: point[name] for name in CURVE_COLUMNS}}
        for point in curves["test"]
    ]
    by_city = []
    for counts in confusion_by_group(test, column, DEFAULT_THRESHOLD, [CITY_KEY]):
        derived = derive_binary_metrics(counts["tp"], counts["fp"], counts["tn"], counts["fn"])
        by_city.append({"model": model, "threshold": DEFAULT_THRESHOLD, **counts, **derived})
    return {"metrics": metrics, "curve": curve, "by_city": by_city}


def _confusion_rows(metric_rows: list[dict]) -> list[dict]:
    """Long-format confusion matrix of the test split for every model."""
    cells = (
        ("wet", "wet", "tp"),
        ("dry", "wet", "fp"),
        ("dry", "dry", "tn"),
        ("wet", "dry", "fn"),
    )
    return [
        {
            "model": row["model"],
            "threshold": row["threshold"],
            "actual": actual,
            "predicted": predicted,
            "count": row[key],
        }
        for row in metric_rows
        if row["split"] == "test"
        for actual, predicted, key in cells
    ]


def class_balance(splits: Splits) -> list[dict]:
    """Share of wet target days per split and city."""
    rows = []
    for split_name in ("train", "validation", "test"):
        grouped = (
            getattr(splits, split_name)
            .groupBy(CITY_KEY)
            .agg(
                F.count(F.lit(1)).alias("n_days"),
                F.sum(LABEL_COL).cast("long").alias("n_wet"),
            )
            .orderBy(CITY_KEY)
        )
        for row in grouped.collect():
            fraction = row["n_wet"] / row["n_days"]
            rows.append({"split": split_name, **row.asDict(), "wet_fraction": fraction})
    return rows


def run_classification(
    daily: DataFrame,
    hourly: DataFrame,
    grid: str = "full",
    split_years: SplitYears = DEFAULT_SPLIT_YEARS,
) -> dict[str, ResultTable]:
    """Tune both classifiers on validation, evaluate on test, return result tables."""
    dataset = build_classification_dataset(daily, hourly)
    dataset = dataset.repartition(MODEL_DATA_PARTITIONS).cache()
    splits = split_by_target_year(dataset, split_years)
    features = usable_feature_set(splits.train, CLASSIFICATION_FEATURES)
    tuned = [
        tune_model(spec, features, splits, _validation_auc, TUNING_METRIC, True)
        for spec in classification_specs(grid)
    ]
    validation_scored = _score(splits.validation, tuned, "validation_model")
    test_scored = _score(splits.test, tuned, "final_model")
    evaluations = [
        _evaluate_model(model, column, validation_scored, test_scored)
        for model, column in _score_columns(tuned).items()
    ]
    metrics = [row for evaluation in evaluations for row in evaluation["metrics"]]
    weights = [
        row
        for item in tuned
        for row in feature_weights(item.final_model, splits.test, item.spec.name)
    ]
    return {
        "q8_tuning": [trial for item in tuned for trial in item.trials],
        "q8_metrics": metrics,
        "q8_confusion_matrix": _confusion_rows(metrics),
        "q8_metrics_by_city": [row for ev in evaluations for row in ev["by_city"]],
        "q8_roc_curve": [row for ev in evaluations for row in ev["curve"]],
        "q8_feature_importance": weights,
        "q8_class_balance": class_balance(splits),
    }
