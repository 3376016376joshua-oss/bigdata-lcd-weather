"""Question 7: linear regression vs gradient-boosted trees for next-day maximum."""

from __future__ import annotations

from pyspark.ml.regression import GBTRegressor, LinearRegression
from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from lcdweather.ml.daily_features import CITY_KEY
from lcdweather.ml.export import ResultTable
from lcdweather.ml.metrics import regression_metrics
from lcdweather.ml.pipelines import FEATURES_COL, feature_weights, usable_feature_set
from lcdweather.ml.regression_features import (
    KEY_COLUMNS,
    PERSISTENCE_COL,
    REGRESSION_FEATURES,
    build_regression_dataset,
)
from lcdweather.ml.settings import (
    DEFAULT_SPLIT_YEARS,
    LABEL_COL,
    MODEL_DATA_PARTITIONS,
    RANDOM_SEED,
    SplitYears,
)
from lcdweather.ml.splits import split_by_target_year
from lcdweather.ml.tuning import ModelSpec, TunedModel, append_model_output, tune_model

TUNING_METRIC = "rmse"
BASELINE_NAME = "persistence"
LINEAR_GRIDS = {
    "full": [
        {"regParam": reg, "elasticNetParam": mix} for reg in (0.0, 0.01, 0.1) for mix in (0.0, 0.5)
    ],
    "quick": [{"regParam": 0.01, "elasticNetParam": 0.0}],
}
GBT_GRIDS = {
    "full": [
        {"maxDepth": depth, "maxIter": iterations, "stepSize": 0.1}
        for depth in (3, 5)
        for iterations in (50, 100)
    ],
    "quick": [{"maxDepth": 3, "maxIter": 10, "stepSize": 0.1}],
}


def regression_specs(grid: str) -> list[ModelSpec]:
    def linear(**params):
        return LinearRegression(featuresCol=FEATURES_COL, labelCol=LABEL_COL, **params)

    def gbt(**params):
        return GBTRegressor(
            featuresCol=FEATURES_COL, labelCol=LABEL_COL, seed=RANDOM_SEED, **params
        )

    return [
        ModelSpec("linear_regression", linear, LINEAR_GRIDS[grid]),
        ModelSpec("gbt_regressor", gbt, GBT_GRIDS[grid]),
    ]


def _validation_rmse(scored: DataFrame) -> float:
    return regression_metrics(scored, "prediction")[0]["rmse"]


def _score(split: DataFrame, tuned: list[TunedModel], stage: str) -> DataFrame:
    scored = split
    for item in tuned:
        model = getattr(item, stage)
        scored = append_model_output(scored, model, F.col("prediction"), f"pred_{item.spec.name}")
    return scored


def _prediction_columns(tuned: list[TunedModel]) -> dict[str, str]:
    columns = {item.spec.name: f"pred_{item.spec.name}" for item in tuned}
    columns[BASELINE_NAME] = PERSISTENCE_COL
    return columns


def _metric_rows(scored: DataFrame, columns: dict[str, str], split: str) -> list[dict]:
    rows = []
    for model_name, column in columns.items():
        for metrics in regression_metrics(scored, column):
            rows.append({"model": model_name, "split": split, **metrics})
    return rows


def _city_rows(scored: DataFrame, columns: dict[str, str]) -> list[dict]:
    rows = []
    for model_name, column in columns.items():
        for metrics in regression_metrics(scored, column, [CITY_KEY]):
            rows.append({"model": model_name, "split": "test", **metrics})
    return rows


def run_regression(
    daily: DataFrame,
    hourly: DataFrame,
    grid: str = "full",
    split_years: SplitYears = DEFAULT_SPLIT_YEARS,
) -> dict[str, ResultTable]:
    """Tune both models on validation, evaluate on test, return result tables."""
    dataset = build_regression_dataset(daily, hourly)
    dataset = dataset.repartition(MODEL_DATA_PARTITIONS).cache()
    splits = split_by_target_year(dataset, split_years)
    features = usable_feature_set(splits.train, REGRESSION_FEATURES)
    tuned = [
        tune_model(spec, features, splits, _validation_rmse, TUNING_METRIC, False)
        for spec in regression_specs(grid)
    ]
    columns = _prediction_columns(tuned)
    validation_scored = _score(splits.validation, tuned, "validation_model")
    test_scored = _score(splits.test, tuned, "final_model").cache()
    weights = [
        row
        for item in tuned
        for row in feature_weights(item.final_model, splits.test, item.spec.name)
    ]
    predictions = test_scored.select(*KEY_COLUMNS, LABEL_COL, *columns.values()).orderBy(
        CITY_KEY, "obs_date"
    )
    return {
        "q7_tuning": [trial for item in tuned for trial in item.trials],
        "q7_metrics": _metric_rows(validation_scored, columns, "validation")
        + _metric_rows(test_scored, columns, "test"),
        "q7_metrics_by_city": _city_rows(test_scored, columns),
        "q7_feature_importance": weights,
        "q7_predictions": predictions,
    }
