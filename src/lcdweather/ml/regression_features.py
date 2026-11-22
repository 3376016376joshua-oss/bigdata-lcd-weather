"""Question 7 dataset: one row per city-day predicting the next day's maximum."""

from __future__ import annotations

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from lcdweather.ml.daily_features import (
    CITY_KEY,
    DATE_COL,
    FORECAST_HORIZON_DAYS,
    prepare_daily,
    value_at_day_offset,
)
from lcdweather.ml.feature_names import FeatureSet
from lcdweather.ml.hourly_features import summarize_hourly
from lcdweather.ml.settings import LABEL_COL
from lcdweather.ml.splits import TARGET_DATE_COL

PERSISTENCE_COL = "pred_persistence"
LAGGED_COLUMNS = ("tmax_f", "tmin_f", "tavg_f")
LAG_DAYS = (1, 2, 3)
TODAY_FEATURES = ("dep_f", "tmax_f", "tmin_f", "tavg_f")
CALENDAR_FEATURES = ("doy_sin", "doy_cos")
HOURLY_FEATURES = (
    "h24_temp_mean",
    "h24_temp_min",
    "h24_temp_max",
    "h24_temp_last",
    "h24_dewpt_mean",
    "h24_dewpt_last",
    "h24_rh_mean",
    "h24_rh_last",
    "h24_wind_mean",
    "h24_wind_max",
    "h24_wind_last",
    "h24_pressure_mean",
    "h24_pressure_last",
    "h24_pressure_change_3h",
    "h24_pressure_change_12h",
    "h24_pressure_change_24h",
)
LAG_FEATURES = tuple(f"{name}_lag{days}" for days in LAG_DAYS for name in LAGGED_COLUMNS)
KEY_COLUMNS = (CITY_KEY, "city", DATE_COL, TARGET_DATE_COL)

REGRESSION_FEATURES = FeatureSet(
    numeric=CALENDAR_FEATURES + TODAY_FEATURES + LAG_FEATURES + HOURLY_FEATURES,
    categorical=(CITY_KEY, "month"),
)


def build_regression_dataset(daily: DataFrame, hourly: DataFrame) -> DataFrame:
    """Join today's daily values, exact-day lags and today's hourly summary.

    Every feature is known by the end of day t; the label is day t+1's maximum.
    """
    days = prepare_daily(daily)
    days = days.withColumn(LABEL_COL, value_at_day_offset("tmax_f", FORECAST_HORIZON_DAYS))
    for days_back in LAG_DAYS:
        for name in LAGGED_COLUMNS:
            lagged = value_at_day_offset(name, -days_back)
            days = days.withColumn(f"{name}_lag{days_back}", lagged)
    joined = days.join(summarize_hourly(hourly), [CITY_KEY, DATE_COL], "left")
    numeric = [F.col(name).cast("double").alias(name) for name in REGRESSION_FEATURES.numeric]
    return joined.where(F.col(LABEL_COL).isNotNull() & F.col("tmax_f").isNotNull()).select(
        *KEY_COLUMNS,
        "month",
        F.col(LABEL_COL).cast("double").alias(LABEL_COL),
        F.col("tmax_f").cast("double").alias(PERSISTENCE_COL),
        *numeric,
    )
