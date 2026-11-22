"""Daily-table features: de-duplication, exact-day lags/leads and calendar encoding."""

from __future__ import annotations

import math

from pyspark.sql import Column, DataFrame, Window
from pyspark.sql import functions as F

from lcdweather.ml.splits import TARGET_DATE_COL

CITY_KEY = "city_code"
DATE_COL = "obs_date"
DAY_NUMBER_COL = "day_num"
DAILY_VALUE_COLUMNS = ("tmax_f", "tmin_f", "tavg_f", "dep_f", "prcp_in")
EPOCH_DATE = "1970-01-01"
DAYS_PER_YEAR = 365.25
FORECAST_HORIZON_DAYS = 1


def dedupe_daily(daily: DataFrame) -> DataFrame:
    """One row per city-day (a guard; the tables hold one primary station per city-day)."""
    values = [F.avg(F.col(name).cast("double")).alias(name) for name in DAILY_VALUE_COLUMNS]
    return daily.groupBy(CITY_KEY, DATE_COL).agg(F.min("city").alias("city"), *values)


def with_day_number(days: DataFrame) -> DataFrame:
    epoch = F.lit(EPOCH_DATE).cast("date")
    return days.withColumn(DAY_NUMBER_COL, F.datediff(F.col(DATE_COL), epoch))


def value_at_day_offset(column: str, offset_days: int) -> Column:
    """Value of `column` exactly `offset_days` calendar days away, else null.

    A range window on the day number (not a row-based lag) keeps a missing
    date from silently shifting a different day's value into the feature.
    """
    window = (
        Window.partitionBy(CITY_KEY).orderBy(DAY_NUMBER_COL).rangeBetween(offset_days, offset_days)
    )
    return F.max(F.col(column)).over(window)


def with_target_calendar(days: DataFrame) -> DataFrame:
    """Calendar features of the predicted day, which is known in advance."""
    target = F.date_add(F.col(DATE_COL), FORECAST_HORIZON_DAYS)
    angle = F.dayofyear(target) * F.lit(2.0 * math.pi / DAYS_PER_YEAR)
    return (
        days.withColumn(TARGET_DATE_COL, target)
        .withColumn("doy_sin", F.sin(angle))
        .withColumn("doy_cos", F.cos(angle))
        .withColumn("month", F.month(target))
    )


def prepare_daily(daily: DataFrame) -> DataFrame:
    """De-duplicated city-days with day number and target-day calendar features."""
    return with_target_calendar(with_day_number(dedupe_daily(daily)))
