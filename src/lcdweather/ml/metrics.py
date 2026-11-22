"""Spark-side evaluation: regression errors, confusion counts and score histograms."""

from __future__ import annotations

from collections.abc import Sequence

from pyspark.ml.evaluation import BinaryClassificationEvaluator
from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from lcdweather.ml.binary_metrics import CURVE_BINS, curve_from_histogram
from lcdweather.ml.settings import LABEL_COL


def regression_metrics(
    scored: DataFrame, prediction_col: str, group_cols: Sequence[str] = ()
) -> list[dict]:
    """n, RMSE, MAE and R2 of one prediction column, optionally per group."""
    valid = scored.where(F.col(prediction_col).isNotNull() & F.col(LABEL_COL).isNotNull())
    error = F.col(prediction_col) - F.col(LABEL_COL)
    squared_error = F.sum(error * error)
    total_variation = F.count(F.lit(1)) * F.var_pop(F.col(LABEL_COL))
    r2 = F.when(total_variation > 0, 1.0 - squared_error / total_variation)
    aggregated = valid.groupBy(*group_cols).agg(
        F.count(F.lit(1)).alias("n"),
        F.sqrt(F.avg(error * error)).alias("rmse"),
        F.avg(F.abs(error)).alias("mae"),
        r2.alias("r2"),
    )
    return _collect_sorted(aggregated, group_cols)


def _collect_sorted(aggregated: DataFrame, group_cols: Sequence[str]) -> list[dict]:
    ordered = aggregated.orderBy(*group_cols) if group_cols else aggregated
    return [row.asDict() for row in ordered.collect()]


def _count_where(condition, name: str):
    return F.sum(F.when(condition, 1).otherwise(0)).alias(name)


def score_histogram(
    scored: DataFrame, score_col: str, n_bins: int = CURVE_BINS
) -> dict[int, tuple[int, int]]:
    """Per score bin: (positive labels, rows). Small enough to collect."""
    valid = scored.where(F.col(score_col).isNotNull() & F.col(LABEL_COL).isNotNull())
    bin_index = F.least(F.floor(F.col(score_col) * n_bins), F.lit(n_bins - 1)).cast("int")
    rows = (
        valid.groupBy(bin_index.alias("bin"))
        .agg(
            F.sum(F.col(LABEL_COL)).cast("long").alias("positives"),
            F.count(F.lit(1)).alias("total"),
        )
        .collect()
    )
    return {row["bin"]: (row["positives"], row["total"]) for row in rows}


def threshold_curve(scored: DataFrame, score_col: str, n_bins: int = CURVE_BINS) -> list[dict]:
    return curve_from_histogram(score_histogram(scored, score_col, n_bins), n_bins)


def confusion_by_group(
    scored: DataFrame, score_col: str, threshold: float, group_cols: Sequence[str]
) -> list[dict]:
    """tp / fp / tn / fn per group at one decision threshold."""
    valid = scored.where(F.col(score_col).isNotNull() & F.col(LABEL_COL).isNotNull())
    predicted = F.col(score_col) >= threshold
    actual = F.col(LABEL_COL) == 1.0
    aggregated = valid.groupBy(*group_cols).agg(
        _count_where(predicted & actual, "tp"),
        _count_where(predicted & ~actual, "fp"),
        _count_where(~predicted & ~actual, "tn"),
        _count_where(~predicted & actual, "fn"),
    )
    return _collect_sorted(aggregated, group_cols)


def area_under_curves(scored: DataFrame, score_col: str) -> dict[str, float]:
    """Exact areas under the ROC and precision-recall curves."""
    valid = scored.where(F.col(score_col).isNotNull() & F.col(LABEL_COL).isNotNull())
    evaluator = BinaryClassificationEvaluator(rawPredictionCol=score_col, labelCol=LABEL_COL)
    return {
        "auc_roc": evaluator.evaluate(valid, {evaluator.metricName: "areaUnderROC"}),
        "auc_pr": evaluator.evaluate(valid, {evaluator.metricName: "areaUnderPR"}),
    }
