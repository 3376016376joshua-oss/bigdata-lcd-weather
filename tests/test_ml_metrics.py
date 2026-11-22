import math

import pytest

pytest.importorskip("pyspark")

from lcdweather.ml.binary_metrics import point_at_threshold  # noqa: E402
from lcdweather.ml.metrics import (  # noqa: E402
    area_under_curves,
    confusion_by_group,
    regression_metrics,
    threshold_curve,
)


def test_regression_metrics_match_hand_computation(spark):
    scored = spark.createDataFrame(
        [("A", 10.0, 12.0), ("A", 20.0, 18.0), ("B", 30.0, 30.0), ("B", 40.0, None)],
        "city_code string, label double, prediction double",
    )

    overall = regression_metrics(scored, "prediction")[0]

    assert overall["n"] == 3
    assert overall["rmse"] == pytest.approx(math.sqrt(8 / 3))
    assert overall["mae"] == pytest.approx(4 / 3)
    assert overall["r2"] == pytest.approx(1 - 8 / 200)


def test_regression_metrics_per_group(spark):
    scored = spark.createDataFrame(
        [("A", 10.0, 11.0), ("A", 20.0, 19.0), ("B", 5.0, 5.0), ("B", 7.0, 7.0)],
        "city_code string, label double, prediction double",
    )

    by_city = regression_metrics(scored, "prediction", ["city_code"])

    assert [row["city_code"] for row in by_city] == ["A", "B"]
    assert by_city[0]["rmse"] == pytest.approx(1.0)
    assert by_city[1]["rmse"] == pytest.approx(0.0)
    assert by_city[1]["r2"] == pytest.approx(1.0)


@pytest.fixture(scope="module")
def scored_binary(spark):
    rows = [
        ("A", 1.0, 0.9),
        ("A", 1.0, 0.6),
        ("A", 0.0, 0.7),
        ("A", 0.0, 0.2),
        ("B", 1.0, 0.4),
        ("B", 0.0, 0.1),
        ("B", 1.0, 1.0),
        ("B", 0.0, None),
    ]
    return spark.createDataFrame(rows, "city_code string, label double, score double")


def test_threshold_curve_counts_at_default_threshold(scored_binary):
    point = point_at_threshold(threshold_curve(scored_binary, "score"), 0.5)

    assert (point["tp"], point["fp"], point["tn"], point["fn"]) == (3, 1, 2, 1)
    assert point["precision"] == pytest.approx(0.75)
    assert point["recall"] == pytest.approx(0.75)


def test_confusion_by_group_agrees_with_the_curve(scored_binary):
    by_city = confusion_by_group(scored_binary, "score", 0.5, ["city_code"])

    assert by_city == [
        {"city_code": "A", "tp": 2, "fp": 1, "tn": 1, "fn": 0},
        {"city_code": "B", "tp": 1, "fp": 0, "tn": 1, "fn": 1},
    ]


def test_area_under_curves_for_a_perfect_and_a_real_ranking(spark, scored_binary):
    perfect = spark.createDataFrame(
        [(1.0, 0.9), (1.0, 0.8), (0.0, 0.3), (0.0, 0.1)], "label double, score double"
    )

    assert area_under_curves(perfect, "score")["auc_roc"] == pytest.approx(1.0)
    # 12 positive-negative pairs, 10 ranked correctly.
    assert area_under_curves(scored_binary, "score")["auc_roc"] == pytest.approx(10 / 12)
