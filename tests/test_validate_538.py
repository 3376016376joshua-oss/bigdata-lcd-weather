"""Phase 3 validation against the FiveThirtyEight fixture, in local Spark."""

from __future__ import annotations

import csv

import pytest

pytest.importorskip("pyspark")

from ingest_support import FIVETHIRTYEIGHT_DIR, LA_DOWNTOWN, NEW_YORK, ingest_fixture  # noqa: E402
from lcdweather.ingest.contract import DAILY_TABLE  # noqa: E402
from lcdweather.ingest.phase3 import run_validation  # noqa: E402
from lcdweather.ingest.validate_538 import DAILY_EXPORT_COLUMNS, SUMMARY_COLUMNS  # noqa: E402

DATABASE = "lcd_test_validate"
NEW_YORK_DAYS = 9
LOS_ANGELES_DAYS = 4


def _read(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


@pytest.fixture(scope="module")
def lcd_daily(spark, tmp_path_factory):
    ingest_fixture(spark, tmp_path_factory.mktemp("clean"), DATABASE)
    return spark.table(f"{DATABASE}.{DAILY_TABLE}")


@pytest.fixture(scope="module")
def results_dir(spark, lcd_daily, tmp_path_factory):
    results = tmp_path_factory.mktemp("results")
    written = run_validation(spark, lcd_daily, str(FIVETHIRTYEIGHT_DIR), str(results))
    assert written == [
        str(results / "validation_538.csv"),
        str(results / "validation_538_daily.csv"),
    ]
    return results


def test_daily_export_joins_each_city_day_once(results_dir):
    days = _read(results_dir / "validation_538_daily.csv")

    assert tuple(days[0]) == DAILY_EXPORT_COLUMNS
    assert len(days) == NEW_YORK_DAYS + LOS_ANGELES_DAYS
    assert [(day["city_code"], day["obs_date"]) for day in days] == sorted(
        (day["city_code"], day["obs_date"]) for day in days
    )
    assert {day["station"] for day in days} == {NEW_YORK, LA_DOWNTOWN}


def test_daily_export_holds_both_sources_and_their_difference(results_dir):
    days = {
        (day["city_code"], day["obs_date"]): day
        for day in _read(results_dir / "validation_538_daily.csv")
    }
    day = days[("KNYC", "2014-07-02")]

    assert float(day["tmax_538"]) == 91.0
    assert float(day["tmax_lcd"]) == pytest.approx(91.04)
    assert float(day["tmax_diff"]) == pytest.approx(0.04)
    assert float(day["tmin_538"]) == 72.0
    assert float(day["tavg_538"]) == 82.0
    assert float(day["prcp_538"]) == 0.96
    assert float(day["prcp_lcd"]) == pytest.approx(24.4 / 25.4)
    assert days[("KCQT", "2015-06-28")]["city"] == "Los Angeles"


def test_summary_reports_correlation_and_mean_absolute_difference_per_city(results_dir):
    summary = {row["city_code"]: row for row in _read(results_dir / "validation_538.csv")}
    new_york = summary["KNYC"]

    assert tuple(new_york) == SUMMARY_COLUMNS
    assert list(summary) == ["KCQT", "KNYC"]
    assert int(new_york["n_days"]) == NEW_YORK_DAYS
    assert int(summary["KCQT"]["n_days"]) == LOS_ANGELES_DAYS
    for metric in ("tmax", "tmin", "tavg"):
        assert int(new_york[f"{metric}_n"]) == NEW_YORK_DAYS
        assert float(new_york[f"{metric}_corr"]) > 0.99
        assert float(new_york[f"{metric}_mae"]) < 0.6
        assert abs(float(new_york[f"{metric}_bias"])) <= float(new_york[f"{metric}_mae"])
    assert float(new_york["prcp_corr"]) > 0.999
    assert float(new_york["prcp_mae"]) < 0.005


def test_summary_matches_the_daily_export(results_dir):
    days = [
        day for day in _read(results_dir / "validation_538_daily.csv") if day["city_code"] == "KNYC"
    ]
    summary = {row["city_code"]: row for row in _read(results_dir / "validation_538.csv")}
    differences = [float(day["tmax_diff"]) for day in days]

    expected_mae = sum(abs(difference) for difference in differences) / len(differences)
    expected_bias = sum(differences) / len(differences)
    assert float(summary["KNYC"]["tmax_mae"]) == pytest.approx(expected_mae)
    assert float(summary["KNYC"]["tmax_bias"]) == pytest.approx(expected_bias)


def test_only_the_primary_station_is_compared(spark, lcd_daily, tmp_path):
    # Los Angeles Intl has no row in the validation year; relabel New York as a secondary
    # station to show that a non-primary station never reaches the comparison.
    from pyspark.sql import functions as F

    secondary = lcd_daily.withColumn("is_primary_station", F.col("station") != NEW_YORK)

    run_validation(spark, secondary, str(FIVETHIRTYEIGHT_DIR), str(tmp_path))

    assert {row["city_code"] for row in _read(tmp_path / "validation_538.csv")} == {"KCQT"}


def test_fails_when_no_day_matches(spark, lcd_daily, tmp_path):
    empty = tmp_path / "fivethirtyeight"
    empty.mkdir()
    (empty / "KNYC.csv").write_text(
        (FIVETHIRTYEIGHT_DIR / "KNYC.csv").read_text(encoding="utf-8").splitlines()[0] + "\n",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="no day of lcd_daily matches"):
        run_validation(spark, lcd_daily, str(empty), str(tmp_path / "results"))
