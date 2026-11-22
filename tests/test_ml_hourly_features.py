from datetime import date

import pytest

pytest.importorskip("pyspark")

from pyspark.sql import functions as F  # noqa: E402

from lcdweather.ml.hourly_features import summarize_hourly  # noqa: E402

HOURLY_SCHEMA = (
    "city_code string, obs_ts string, report_type string, temp_f double, dewpt_f double, "
    "rh_pct double, wind_speed_mph double, wind_gust_mph double, "
    "station_pressure_hpa double, sky_cover_okta int, precip_in double, is_special boolean"
)


def _routine(hour, temp, pressure, sky=2, humidity=50.0, gust=None, precip=0.0):
    stamp = f"2020-05-01 {hour:02d}:51:00"
    dewpoint = None if temp is None else temp - 10.0
    return (
        "KAAA",
        stamp,
        "FM-15",
        temp,
        dewpoint,
        humidity,
        5.0,
        gust,
        pressure,
        sky,
        precip,
        False,
    )


def _special(hour, temp):
    stamp = f"2020-05-01 {hour:02d}:20:00"
    return ("KAAA", stamp, "FM-16", temp, None, None, 40.0, None, 900.0, 8, None, True)


def _summary(spark, rows):
    hourly = (
        spark.createDataFrame(rows, HOURLY_SCHEMA)
        .withColumn("obs_ts", F.to_timestamp("obs_ts"))
        .withColumn("obs_date", F.to_date("obs_ts"))
    )
    return summarize_hourly(hourly).first()


def test_pressure_changes_look_back_3_12_and_24_hours(spark):
    rows = [
        _routine(0, 50.0, 1020.0),
        _routine(11, 60.0, 1016.0),
        _routine(12, 61.0, 1015.0),
        _routine(20, 55.0, 1011.0),
        _routine(22, 53.0, 1009.5),
        _routine(23, 52.0, 1009.0),
    ]

    summary = _summary(spark, rows)

    assert summary["obs_date"] == date(2020, 5, 1)
    assert summary["h24_pressure_last"] == 1009.0
    assert summary["h24_pressure_change_3h"] == pytest.approx(-2.0)
    assert summary["h24_pressure_change_12h"] == pytest.approx(-7.0)
    assert summary["h24_pressure_change_24h"] == pytest.approx(-11.0)


def test_last_reading_skips_missing_values(spark):
    rows = [
        _routine(21, 55.0, 1010.0),
        _routine(22, 54.0, None),
        _routine(23, None, None),
    ]

    summary = _summary(spark, rows)

    assert summary["h24_temp_last"] == 54.0
    assert summary["h24_pressure_last"] == 1010.0
    assert summary["h24_pressure_change_3h"] is None


def test_special_reports_are_counted_but_excluded_from_aggregates(spark):
    rows = [
        _routine(10, 60.0, 1012.0, sky=4, humidity=40.0, precip=0.1),
        _routine(11, 70.0, 1010.0, sky=6, humidity=60.0, gust=25.0, precip=0.2),
        _special(11, 150.0),
        _special(12, 150.0),
    ]

    summary = _summary(spark, rows)

    assert summary["h24_special_count"] == 2.0
    assert summary["h24_temp_max"] == 70.0
    assert summary["h24_temp_mean"] == pytest.approx(65.0)
    assert summary["h24_wind_max"] == 5.0
    assert summary["h24_pressure_mean"] == pytest.approx(1011.0)
    assert summary["h24_sky_mean"] == pytest.approx(5.0)
    assert summary["h24_sky_max"] == 6.0
    assert summary["h24_rh_min"] == 40.0
    assert summary["h24_dewpt_dep_mean"] == pytest.approx(10.0)
    assert summary["h24_precip_sum"] == pytest.approx(0.3)
    assert summary["h24_gust_max"] == 25.0


def test_days_without_gust_reports_have_zero_gust(spark):
    summary = _summary(spark, [_routine(10, 60.0, 1012.0)])

    assert summary["h24_gust_max"] == 0.0
