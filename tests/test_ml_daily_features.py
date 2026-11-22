from datetime import date

import pytest

pytest.importorskip("pyspark")

from lcdweather.ml.daily_features import (  # noqa: E402
    dedupe_daily,
    prepare_daily,
    value_at_day_offset,
    with_day_number,
)

DAILY_SCHEMA = (
    "city_code string, city string, obs_date date, tmax_f double, tmin_f double, "
    "tavg_f double, dep_f double, prcp_in double"
)


def _daily(spark, rows):
    return spark.createDataFrame(rows, DAILY_SCHEMA)


def _day(city, day, tmax):
    return (city, city.title(), day, tmax, tmax - 20.0, tmax - 10.0, 0.0, 0.0)


def test_offsets_use_calendar_days_not_row_positions(spark):
    # 3 January is missing, so 4 January has no "yesterday" and 2 January no "tomorrow".
    rows = [
        _day("KAAA", date(2020, 1, 1), 50.0),
        _day("KAAA", date(2020, 1, 2), 52.0),
        _day("KAAA", date(2020, 1, 4), 58.0),
        _day("KBBB", date(2020, 1, 3), 99.0),
    ]
    days = with_day_number(_daily(spark, rows))

    result = days.select(
        "city_code",
        "obs_date",
        value_at_day_offset("tmax_f", -1).alias("yesterday"),
        value_at_day_offset("tmax_f", 1).alias("tomorrow"),
    ).collect()

    by_key = {(row["city_code"], row["obs_date"]): row for row in result}
    assert by_key[("KAAA", date(2020, 1, 2))]["yesterday"] == 50.0
    assert by_key[("KAAA", date(2020, 1, 2))]["tomorrow"] is None
    assert by_key[("KAAA", date(2020, 1, 4))]["yesterday"] is None
    assert by_key[("KAAA", date(2020, 1, 1))]["tomorrow"] == 52.0
    assert by_key[("KBBB", date(2020, 1, 3))]["yesterday"] is None


def test_duplicate_city_days_from_two_stations_are_averaged(spark):
    rows = [
        _day("KCQT", date(2024, 1, 1), 60.0),
        _day("KCQT", date(2024, 1, 1), 70.0),
        _day("KCQT", date(2024, 1, 2), 61.0),
    ]

    deduped = dedupe_daily(_daily(spark, rows)).orderBy("obs_date").collect()

    assert [row["tmax_f"] for row in deduped] == [65.0, 61.0]


def test_calendar_features_describe_the_predicted_day(spark):
    prepared = prepare_daily(_daily(spark, [_day("KAAA", date(2021, 12, 31), 40.0)])).first()

    assert prepared["target_date"] == date(2022, 1, 1)
    assert prepared["month"] == 1
    assert prepared["doy_cos"] == pytest.approx(1.0, abs=1e-3)
    assert prepared["doy_sin"] == pytest.approx(0.0172, abs=1e-3)
