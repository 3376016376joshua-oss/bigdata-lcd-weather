"""Phase 2 end to end on the raw fixture, in local Spark."""

from __future__ import annotations

import pytest

pytest.importorskip("pyspark")

from pyspark.sql import functions as F  # noqa: E402

from ingest_support import (  # noqa: E402
    LA_AIRPORT,
    LA_DOWNTOWN,
    NEW_YORK,
    SEATTLE,
    UNLISTED_STATION,
    expected_row_count,
    ingest_fixture,
)
from lcdweather.ingest.contract import (  # noqa: E402
    DAILY_COLUMNS,
    DAILY_TABLE,
    HOURLY_COLUMNS,
    HOURLY_REPORT_TYPES,
    HOURLY_TABLE,
    MONTHLY_COLUMNS,
    MONTHLY_TABLE,
)

DATABASE = "lcd_test_pipeline"
TIMESTAMP_FORMAT = "yyyy-MM-dd HH:mm"


@pytest.fixture(scope="module")
def clean_dir(spark, tmp_path_factory):
    output = tmp_path_factory.mktemp("clean")
    ingest_fixture(spark, output, DATABASE)
    return output


@pytest.fixture(scope="module")
def hourly(spark, clean_dir):
    return spark.table(f"{DATABASE}.{HOURLY_TABLE}")


@pytest.fixture(scope="module")
def daily(spark, clean_dir):
    return spark.table(f"{DATABASE}.{DAILY_TABLE}")


@pytest.fixture(scope="module")
def monthly(spark, clean_dir):
    return spark.table(f"{DATABASE}.{MONTHLY_TABLE}")


def _hourly_report(hourly, station, written_time):
    at_time = F.date_format(F.col("obs_ts"), TIMESTAMP_FORMAT) == written_time
    rows = hourly.where((F.col("station") == station) & at_time).collect()
    assert len(rows) == 1, f"{len(rows)} reports for {station} at {written_time}"
    return rows[0]


def _day(daily, station, date):
    rows = daily.where((F.col("station") == station) & (F.col("obs_date") == date)).collect()
    assert len(rows) == 1, f"{len(rows)} rows for {station} on {date}"
    return rows[0]


def _month(monthly, station, year, month):
    in_month = (F.col("yr") == year) & (F.col("month") == month)
    rows = monthly.where((F.col("station") == station) & in_month).collect()
    assert len(rows) == 1, f"{len(rows)} rows for {station} in {year}-{month}"
    return rows[0]


def test_tables_have_exactly_the_contract_columns(hourly, daily, monthly):
    assert tuple(hourly.columns) == HOURLY_COLUMNS
    assert tuple(daily.columns) == DAILY_COLUMNS
    assert tuple(monthly.columns) == MONTHLY_COLUMNS


def test_column_types(hourly, daily, monthly):
    hourly_types, daily_types, monthly_types = (
        dict(table.dtypes) for table in (hourly, daily, monthly)
    )

    assert hourly_types["obs_ts"] == "timestamp"
    assert hourly_types["obs_date"] == daily_types["obs_date"] == "date"
    assert (
        hourly_types["temp_f"] == daily_types["tmax_f"] == monthly_types["mean_tavg_f"] == "double"
    )
    assert hourly_types["wind_dir_deg"] == hourly_types["sky_cover_okta"] == "int"
    assert hourly_types["is_special"] == daily_types["is_dry_day"] == "boolean"
    assert daily_types["prcp_trace"] == daily_types["is_primary_station"] == "boolean"
    assert monthly_types["days_max_ge_90"] == monthly_types["month"] == "int"
    assert hourly_types["station"] == "string"
    assert hourly_types["yr"] == daily_types["yr"] == monthly_types["yr"] == "int"


def test_rows_are_split_by_report_type_and_deduplicated(hourly, daily, monthly):
    assert hourly.count() == expected_row_count(HOURLY_REPORT_TYPES)
    assert daily.count() == expected_row_count({"SOD"})
    assert monthly.count() == expected_row_count({"SOM"})


def test_hourly_keeps_every_kind_of_hourly_report_and_nothing_else(hourly):
    by_type = {
        row["report_type"]: row["count"] for row in hourly.groupBy("report_type").count().collect()
    }

    assert by_type["SY-MT"] == 2
    assert set(by_type) == {"FM-15", "FM-16", "FM-12", "SY-MT"}
    assert hourly.where(F.col("is_special") != (F.col("report_type") == "FM-16")).count() == 0


def test_files_are_orc_partitioned_by_station_and_year(clean_dir):
    partition = clean_dir / DAILY_TABLE / f"station={NEW_YORK}" / "yr=2014"

    assert [path.suffix for path in partition.glob("part-*")] == [".orc"]
    assert (clean_dir / HOURLY_TABLE / f"station={SEATTLE}" / "yr=2010").is_dir()
    assert (clean_dir / MONTHLY_TABLE / f"station={LA_AIRPORT}" / "yr=2024").is_dir()


def test_stations_outside_the_list_and_unreadable_dates_are_dropped(hourly, daily):
    assert daily.where(F.col("station") == UNLISTED_STATION).count() == 0
    assert hourly.where(F.col("obs_ts").isNull() | F.col("yr").isNull()).count() == 0


def test_hourly_values_are_converted_to_us_units(hourly):
    report = _hourly_report(hourly, NEW_YORK, "2014-01-03 00:37")

    assert (report["city_code"], report["city"], report["yr"]) == ("KNYC", "New York", 2014)
    assert report["report_type"] == "FM-16" and report["is_special"] is True
    assert report["temp_f"] == pytest.approx(-8.3 * 1.8 + 32)
    assert report["dewpt_f"] == pytest.approx(-11.1 * 1.8 + 32)
    assert report["wetbulb_f"] == pytest.approx(-9.1 * 1.8 + 32)
    assert report["rh_pct"] == 80.0
    assert report["wind_speed_mph"] == pytest.approx(5.7 * 2.236936, rel=1e-6)
    assert report["wind_gust_mph"] == pytest.approx(11.8 * 2.236936, rel=1e-6)
    assert report["wind_dir_deg"] == 50
    assert report["station_pressure_hpa"] == 999.4
    assert report["sea_level_pressure_hpa"] is None
    assert report["visibility_mi"] == pytest.approx(0.5, abs=1e-3)
    assert report["sky_conditions"] == "VV:09 2.74"
    assert report["sky_cover_okta"] == 9
    assert report["precip_in"] == pytest.approx(1.0 / 25.4)
    assert (report["hour"], report["month"], report["season"]) == (0, 1, "DJF")
    assert str(report["obs_date"]) == "2014-01-03"


def test_hourly_flags_and_markers_are_parsed_defensively(hourly):
    trace = _hourly_report(hourly, NEW_YORK, "2014-01-02 04:15")
    variable = _hourly_report(hourly, NEW_YORK, "2014-01-06 00:51")
    flagged = _hourly_report(hourly, NEW_YORK, "2014-12-31 22:51")

    assert trace["precip_in"] == 0.0
    assert _hourly_report(hourly, NEW_YORK, "2014-01-02 04:51")["wind_dir_deg"] is None
    assert variable["visibility_mi"] == pytest.approx(2.5, abs=1e-3)
    assert variable["pressure_change_hpa"] == -6.8
    assert flagged["visibility_mi"] == pytest.approx(0.5, abs=1e-3)
    assert flagged["precip_in"] is None
    assert flagged["station_pressure_hpa"] is None
    assert flagged["wind_gust_mph"] is None
    assert (flagged["sky_conditions"], flagged["sky_cover_okta"]) == ("4.5", None)
    assert _hourly_report(hourly, LA_AIRPORT, "2024-01-02 10:53")["wind_dir_deg"] == 90
    assert _hourly_report(hourly, LA_DOWNTOWN, "2024-01-02 12:47")["wind_dir_deg"] == 0


def test_daily_values_and_derived_columns(daily):
    day = _day(daily, NEW_YORK, "2014-07-02")

    assert (day["city_code"], day["month"], day["season"], day["doy"]) == ("KNYC", 7, "JJA", 183)
    assert day["tmax_f"] == pytest.approx(32.8 * 1.8 + 32)
    assert day["tmin_f"] == pytest.approx(22.2 * 1.8 + 32)
    assert day["tavg_f"] == pytest.approx(27.5 * 1.8 + 32)
    assert day["temp_range_f"] == pytest.approx((32.8 - 22.2) * 1.8)
    assert day["dep_f"] == pytest.approx(2.83 * 1.8)
    assert day["prcp_in"] == pytest.approx(24.4 / 25.4)
    assert day["cdd"] == pytest.approx(9.2 * 1.8)
    assert day["hdd"] == 0.0
    assert day["peak_wind_mph"] == pytest.approx(11.6 * 2.236936, rel=1e-6)
    assert day["sustained_wind_mph"] == pytest.approx(6.7 * 2.236936, rel=1e-6)
    assert (day["sunrise"], day["sunset"]) == ("0428", "1931")
    assert (day["prcp_trace"], day["is_dry_day"], day["is_wet_day"]) == (False, False, True)
    assert (day["is_warm_extreme"], day["is_cold_extreme"]) == (False, False)


def test_daily_extremes_snow_and_trace(daily):
    cold = _day(daily, NEW_YORK, "2014-01-03")
    trace_snow = _day(daily, NEW_YORK, "2014-01-05")
    trace_rain = _day(daily, LA_DOWNTOWN, "2015-06-28")

    assert cold["dep_f"] == pytest.approx(-11.76 * 1.8)
    assert (cold["is_warm_extreme"], cold["is_cold_extreme"]) == (False, True)
    assert cold["snow_in"] == pytest.approx(84.0 / 25.4)
    assert cold["snow_depth_in"] == pytest.approx(150.0 / 25.4)
    assert trace_snow["snow_in"] == 0.0
    assert (trace_rain["prcp_in"], trace_rain["prcp_trace"]) == (0.0, True)
    assert (trace_rain["is_dry_day"], trace_rain["is_wet_day"]) == (True, False)
    assert trace_rain["snow_in"] is None


def test_extreme_flags_follow_the_ten_degree_threshold(daily):
    warm = F.col("dep_f") >= 10
    cold = F.col("dep_f") <= -10

    hot = _day(daily, LA_DOWNTOWN, "2015-03-14")
    assert hot["dep_f"] == pytest.approx(9.19 * 1.8)
    assert (hot["is_warm_extreme"], hot["is_cold_extreme"]) == (True, False)
    assert daily.where(F.col("is_warm_extreme")).count() == 1
    assert daily.where(F.col("is_cold_extreme")).count() == 4
    assert daily.where(F.col("is_warm_extreme") != warm).count() == 0
    assert daily.where(F.col("is_cold_extreme") != cold).count() == 0
    assert daily.where(F.col("is_dry_day") == F.col("is_wet_day")).count() == 0


def test_monthly_values(monthly):
    july = _month(monthly, NEW_YORK, 2014, 7)
    november = _month(monthly, NEW_YORK, 2014, 11)

    assert july["mean_tavg_f"] == pytest.approx(24.52 * 1.8 + 32)
    assert july["mean_tmax_f"] == pytest.approx(28.60 * 1.8 + 32)
    assert july["mean_tmin_f"] == pytest.approx(20.45 * 1.8 + 32)
    assert july["dep_tavg_f"] == pytest.approx(-0.76 * 1.8)
    assert july["normal_tavg_f"] == pytest.approx((24.52 + 0.76) * 1.8 + 32)
    assert july["total_prcp_in"] == pytest.approx(142.0 / 25.4)
    assert july["dep_prcp_in"] == pytest.approx(25.2 / 25.4)
    assert july["cdd"] == pytest.approx(191.9 * 1.8)
    assert (july["days_max_ge_90"], july["days_min_le_32"]) == (3, 0)
    assert november["hdd"] == pytest.approx(327.9 * 1.8)
    assert november["total_snow_in"] == pytest.approx(5.0 / 25.4)
    assert (november["days_max_ge_90"], november["days_min_le_32"]) == (0, 7)
    assert _month(monthly, NEW_YORK, 2014, 1)["days_min_le_32"] == 24


def test_los_angeles_keeps_both_stations_and_marks_the_primary_one(daily, hourly, monthly):
    for table in (daily, hourly, monthly):
        flags = {
            (row["station"], row["yr"]): row["is_primary_station"]
            for row in table.where(F.col("city_code") == "KCQT")
            .select("station", "yr", "is_primary_station")
            .distinct()
            .collect()
        }
        assert flags == {
            (LA_DOWNTOWN, 2015): True,
            (LA_DOWNTOWN, 2024): False,
            (LA_AIRPORT, 2024): True,
        }
    assert (
        daily.where(F.col("city_code") != "KCQT").where(~F.col("is_primary_station")).count() == 0
    )


def test_years_flag_limits_the_run_and_prefix_keeps_it_apart(spark, tmp_path, daily):
    full_count = daily.count()

    targets = ingest_fixture(spark, tmp_path, DATABASE, years=(2014,), table_prefix="trial_")

    trial = spark.table(f"{DATABASE}.trial_{DAILY_TABLE}")
    assert [target.name for target in targets] == [
        "trial_lcd_hourly",
        "trial_lcd_daily",
        "trial_lcd_monthly",
    ]
    assert {row["yr"] for row in trial.select("yr").distinct().collect()} == {2014}
    assert trial.count() == expected_row_count({"SOD"}, years=(2014,))
    assert (tmp_path / "trial_lcd_daily" / f"station={NEW_YORK}" / "yr=2014").is_dir()
    assert spark.table(f"{DATABASE}.{DAILY_TABLE}").count() == full_count


def test_rerun_replaces_the_tables(spark, tmp_path):
    database = "lcd_test_rerun"

    ingest_fixture(spark, tmp_path, database)
    ingest_fixture(spark, tmp_path, database)

    assert spark.table(f"{database}.{DAILY_TABLE}").count() == expected_row_count({"SOD"})


def test_files_only_run_writes_orc_without_registering(spark, tmp_path):
    database = "lcd_test_files_only"

    ingest_fixture(spark, tmp_path, database, register_tables=False)

    assert not spark.catalog.databaseExists(database)
    from_files = spark.read.orc(str(tmp_path / MONTHLY_TABLE))
    assert set(from_files.columns) == set(MONTHLY_COLUMNS)
    assert from_files.count() == expected_row_count({"SOM"})


def test_a_file_with_another_header_fails_the_run(spark, tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "LCD_USW00094728_2014.csv").write_text(
        '"STATION","DATE","SOMETHING_ELSE"\n"USW00094728","2014-01-01T00:00:00","1"\n',
        encoding="utf-8",
    )

    with pytest.raises(Exception, match="(?i)header|schema|column"):
        ingest_fixture(spark, tmp_path / "clean", "lcd_test_bad_header", input_path=str(raw))
