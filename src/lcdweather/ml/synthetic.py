"""Synthetic `lcd_hourly` / `lcd_daily` DataFrames for tests and smoke runs."""

from __future__ import annotations

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from lcdweather.ml.synthetic_weather import SyntheticCity, SyntheticSpec, generate_rows

HOURLY_SCHEMA = (
    "city_code string, city string, obs_ts string, obs_date string, report_type string, "
    "temp_f double, dewpt_f double, rh_pct double, wind_speed_mph double, "
    "wind_gust_mph double, station_pressure_hpa double, sky_cover_okta int, "
    "precip_in double, is_special boolean"
)
DAILY_SCHEMA = (
    "city_code string, city string, obs_date string, tmax_f double, tmin_f double, "
    "tavg_f double, dep_f double, prcp_in double"
)

DEMO_CITIES = (
    SyntheticCity("KSEA", "Seattle", 52.0, 13.0, 0.45),
    SyntheticCity("KPHX", "Phoenix", 75.0, 20.0, 0.08),
    SyntheticCity("KMDW", "Chicago", 51.0, 25.0, 0.30),
    SyntheticCity("KJAX", "Jacksonville", 69.0, 14.0, 0.33),
    SyntheticCity("KNYC", "New York", 55.0, 22.0, 0.32),
)
DEMO_YEARS = tuple(range(2020, 2026))
THREE_HOURLY = tuple(range(0, 24, 3))
# Consecutive days keep lag features populated; year-round days fill all months.
CONSECUTIVE_DAYS_SPEC = SyntheticSpec(
    DEMO_CITIES[:3], DEMO_YEARS, tuple(range(1, 46)), THREE_HOURLY
)
YEAR_ROUND_SPEC = SyntheticSpec(DEMO_CITIES, DEMO_YEARS[-2:], tuple(range(1, 366, 9)), THREE_HOURLY)


def synthetic_tables(spark: SparkSession, spec: SyntheticSpec) -> tuple[DataFrame, DataFrame]:
    """(hourly, daily) DataFrames with the cleaned-table columns Phase 5 reads."""
    hourly_rows, daily_rows = generate_rows(spec)
    # Timestamps are parsed by Spark so hours stay stable in any session time zone.
    hourly = (
        spark.createDataFrame(hourly_rows, HOURLY_SCHEMA)
        .withColumn("obs_ts", F.to_timestamp("obs_ts"))
        .withColumn("obs_date", F.to_date("obs_date"))
    )
    daily = spark.createDataFrame(daily_rows, DAILY_SCHEMA).withColumn(
        "obs_date", F.to_date("obs_date")
    )
    return hourly, daily
