"""Phase 3 profiling of the raw fixture and the tables built from it, in local Spark."""

from __future__ import annotations

import csv

import pytest

pytest.importorskip("pyspark")

from ingest_support import (  # noqa: E402
    FIXTURE_YEARS,
    LA_AIRPORT,
    LA_DOWNTOWN,
    NEW_YORK,
    RAW_DIR,
    SEATTLE,
    UNLISTED_STATION,
    expected_row_count,
    ingest_fixture,
    raw_fixture_rows,
)
from lcdweather.ingest import profile  # noqa: E402
from lcdweather.ingest.contract import (  # noqa: E402
    DAILY_TABLE,
    HOURLY_REPORT_TYPES,
    HOURLY_TABLE,
    MONTHLY_TABLE,
    TABLE_COLUMNS,
)
from lcdweather.ingest.phase3 import run_profile  # noqa: E402
from lcdweather.ingest.reader import read_raw  # noqa: E402

DATABASE = "lcd_test_profile"
LA_DOWNTOWN_2024_DAYS = 3


def _read(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


@pytest.fixture(scope="module")
def results_dir(spark, tmp_path_factory):
    ingest_fixture(spark, tmp_path_factory.mktemp("clean"), DATABASE)
    tables = {name: spark.table(f"{DATABASE}.{name}") for name in TABLE_COLUMNS}
    results = tmp_path_factory.mktemp("results")
    written = run_profile(spark, read_raw(spark, str(RAW_DIR), FIXTURE_YEARS), tables, str(results))
    assert written == [
        str(results / f"{name}.csv")
        for name in (
            "profile_report_types",
            "profile_missing",
            "profile_ranges",
            "table_row_counts",
        )
    ]
    return results


def test_report_type_mix_counts_every_raw_row(results_dir):
    mix = _read(results_dir / "profile_report_types.csv")
    counts = {(row["station"], row["yr"], row["report_type"]): int(row["n_rows"]) for row in mix}

    assert tuple(mix[0]) == profile.REPORT_TYPE_HEADER
    assert sum(counts.values()) == len(raw_fixture_rows())
    assert counts[(SEATTLE, "2010", "FM-12")] == 3
    assert counts[(SEATTLE, "2010", "SY-MT")] == 2
    assert counts[(LA_AIRPORT, "2024", "")] == 1
    assert counts[(NEW_YORK, "2014", "SOM")] == 3
    assert counts[(NEW_YORK, "", "FM-15")] == 1
    assert counts[(UNLISTED_STATION, "2014", "SOD")] == 2


def test_row_counts_are_exact(results_dir):
    counts = {row["table"]: row for row in _read(results_dir / "table_row_counts.csv")}

    assert tuple(counts[DAILY_TABLE]) == profile.ROW_COUNT_HEADER
    assert list(counts) == list(TABLE_COLUMNS)
    assert int(counts[HOURLY_TABLE]["n_rows"]) == expected_row_count(HOURLY_REPORT_TYPES)
    assert int(counts[DAILY_TABLE]["n_rows"]) == expected_row_count({"SOD"})
    assert int(counts[MONTHLY_TABLE]["n_rows"]) == expected_row_count({"SOM"})
    assert (
        int(counts[DAILY_TABLE]["n_primary_rows"])
        == expected_row_count({"SOD"}) - LA_DOWNTOWN_2024_DAYS
    )
    assert int(counts[MONTHLY_TABLE]["n_primary_rows"]) == expected_row_count({"SOM"}) - 1
    for row in counts.values():
        assert (row["n_stations"], row["n_station_years"]) == ("4", "5")
        assert (row["first_yr"], row["last_yr"]) == ("2010", "2024")


def test_missing_values_per_station_and_column(results_dir):
    missing = _read(results_dir / "profile_missing.csv")
    by_key = {(row["table"], row["station"], row["column"]): row for row in missing}

    assert tuple(missing[0]) == profile.MISSING_HEADER
    downtown_snow = by_key[(DAILY_TABLE, LA_DOWNTOWN, "snow_in")]
    assert downtown_snow["city_code"] == "KCQT"
    assert downtown_snow["n_missing"] == downtown_snow["n_rows"] == "8"
    assert float(downtown_snow["pct_missing"]) == 100.0
    new_york_tmax = by_key[(DAILY_TABLE, NEW_YORK, "tmax_f")]
    assert (new_york_tmax["n_missing"], float(new_york_tmax["pct_missing"])) == ("0", 0.0)
    assert int(by_key[(HOURLY_TABLE, NEW_YORK, "sea_level_pressure_hpa")]["n_missing"]) > 0
    profiled = {row["column"] for row in missing if row["table"] == DAILY_TABLE}
    assert profiled == set(TABLE_COLUMNS[DAILY_TABLE]) - set(profile.IDENTITY_COLUMNS)


def test_value_ranges_per_station_and_numeric_column(results_dir):
    ranges = _read(results_dir / "profile_ranges.csv")
    by_key = {(row["table"], row["station"], row["column"]): row for row in ranges}

    assert tuple(ranges[0]) == profile.RANGE_HEADER
    tmax = by_key[(DAILY_TABLE, NEW_YORK, "tmax_f")]
    assert float(tmax["max"]) == pytest.approx(32.8 * 1.8 + 32)
    assert float(tmax["min"]) == pytest.approx(-7.7 * 1.8 + 32)
    assert float(tmax["min"]) < float(tmax["mean"]) < float(tmax["max"])
    assert float(tmax["stddev"]) > 0
    assert tmax["n_values"] == "18"
    empty = by_key[(DAILY_TABLE, LA_DOWNTOWN, "snow_in")]
    assert (empty["n_values"], empty["min"], empty["max"], empty["mean"]) == ("0", "", "", "")
    columns = {row["column"] for row in ranges if row["table"] == HOURLY_TABLE}
    assert {"temp_f", "rh_pct", "sky_cover_okta", "precip_in"} <= columns
    assert not {"sky_conditions", "is_special", "obs_ts", "station", "yr"} & columns
