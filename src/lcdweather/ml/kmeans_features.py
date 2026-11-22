"""Per-city climate profile used for k-means: seasonal and daily cycle shape."""

from __future__ import annotations

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from lcdweather.ml.daily_features import CITY_KEY, DATE_COL, dedupe_daily
from lcdweather.ml.settings import ROUTINE_REPORT_TYPE

MONTHS = tuple(range(1, 13))
TEMPERATURE_COLUMNS = tuple(f"temp_m{month:02d}" for month in MONTHS)
PRECIPITATION_COLUMNS = tuple(f"prcp_m{month:02d}" for month in MONTHS)
SHAPE_COLUMNS = ("diurnal_range_f", "hourly_amplitude_f", "mean_rh_pct")
PROFILE_COLUMNS = TEMPERATURE_COLUMNS + PRECIPITATION_COLUMNS + SHAPE_COLUMNS


def _pivot_months(frame: DataFrame, value: str, names: tuple) -> DataFrame:
    pivoted = frame.groupBy(CITY_KEY).pivot("month", list(MONTHS)).agg(F.avg(value))
    renamed = [F.col(str(month)).alias(name) for month, name in zip(MONTHS, names)]
    return pivoted.select(CITY_KEY, *renamed)


def monthly_temperature(days: DataFrame) -> DataFrame:
    """Mean daily temperature of each calendar month across all years."""
    return _pivot_months(days, "tavg_f", TEMPERATURE_COLUMNS)


def monthly_precipitation(days: DataFrame) -> DataFrame:
    """Mean monthly precipitation total of each calendar month across all years."""
    totals = days.groupBy(CITY_KEY, F.year(DATE_COL).alias("year"), "month").agg(
        F.sum("prcp_in").alias("total_prcp_in")
    )
    return _pivot_months(totals, "total_prcp_in", PRECIPITATION_COLUMNS)


def daily_shape(days: DataFrame) -> DataFrame:
    daily_range = F.col("tmax_f") - F.col("tmin_f")
    return days.groupBy(CITY_KEY).agg(
        F.min("city").alias("city"), F.avg(daily_range).alias("diurnal_range_f")
    )


def hourly_shape(hourly: DataFrame) -> DataFrame:
    """Amplitude of the mean hour-of-day temperature curve, and mean humidity."""
    routine = hourly.where(F.col("report_type") == ROUTINE_REPORT_TYPE)
    by_hour = routine.groupBy(CITY_KEY, F.hour("obs_ts").alias("hour")).agg(
        F.avg("temp_f").alias("mean_temp_f")
    )
    amplitude = by_hour.groupBy(CITY_KEY).agg(
        (F.max("mean_temp_f") - F.min("mean_temp_f")).alias("hourly_amplitude_f")
    )
    humidity = routine.groupBy(CITY_KEY).agg(F.avg("rh_pct").alias("mean_rh_pct"))
    return amplitude.join(humidity, CITY_KEY, "outer")


def build_city_profiles(daily: DataFrame, hourly: DataFrame) -> DataFrame:
    """One row per city with every clustering feature."""
    days = dedupe_daily(daily).withColumn("month", F.month(DATE_COL))
    parts: list[DataFrame] = [
        monthly_temperature(days),
        monthly_precipitation(days),
        hourly_shape(hourly),
    ]
    profiles = daily_shape(days)
    for part in parts:
        profiles = profiles.join(part, CITY_KEY, "left")
    features = [F.col(name).cast("double").alias(name) for name in PROFILE_COLUMNS]
    return profiles.select(CITY_KEY, "city", *features)
