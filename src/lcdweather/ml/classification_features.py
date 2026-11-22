"""Question 8 dataset: will the next day have measurable precipitation?"""

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
from lcdweather.ml.settings import LABEL_COL, WET_DAY_THRESHOLD_IN
from lcdweather.ml.splits import TARGET_DATE_COL

PERSISTENCE_COL = "p_persistence"
CALENDAR_FEATURES = ("doy_sin", "doy_cos")
HOURLY_FEATURES = (
    "h24_pressure_change_3h",
    "h24_pressure_change_12h",
    "h24_pressure_change_24h",
    "h24_pressure_mean",
    "h24_pressure_last",
    "h24_rh_mean",
    "h24_rh_min",
    "h24_rh_max",
    "h24_rh_last",
    "h24_dewpt_dep_mean",
    "h24_dewpt_dep_min",
    "h24_dewpt_dep_last",
    "h24_wind_mean",
    "h24_wind_max",
    "h24_wind_last",
    "h24_gust_max",
    "h24_sky_mean",
    "h24_sky_max",
    "h24_sky_last",
    "h24_precip_sum",
    "h24_special_count",
)
KEY_COLUMNS = (CITY_KEY, "city", DATE_COL, TARGET_DATE_COL)

CLASSIFICATION_FEATURES = FeatureSet(
    numeric=CALENDAR_FEATURES + HOURLY_FEATURES,
    categorical=(CITY_KEY, "month"),
)


def _is_wet(precipitation):
    """1.0 for measurable precipitation, 0.0 otherwise, null when unknown."""
    wet = (precipitation >= WET_DAY_THRESHOLD_IN).cast("double")
    return F.when(precipitation.isNotNull(), wet)


def build_classification_dataset(daily: DataFrame, hourly: DataFrame) -> DataFrame:
    """Features from day t's hourly readings; label is whether day t+1 is wet."""
    days = prepare_daily(daily)
    next_day_precip = value_at_day_offset("prcp_in", FORECAST_HORIZON_DAYS)
    days = days.withColumn(LABEL_COL, _is_wet(next_day_precip)).withColumn(
        PERSISTENCE_COL, _is_wet(F.col("prcp_in"))
    )
    joined = days.join(summarize_hourly(hourly), [CITY_KEY, DATE_COL], "left")
    numeric = [F.col(name).cast("double").alias(name) for name in CLASSIFICATION_FEATURES.numeric]
    return joined.where(F.col(LABEL_COL).isNotNull() & F.col(PERSISTENCE_COL).isNotNull()).select(
        *KEY_COLUMNS, "month", LABEL_COL, PERSISTENCE_COL, *numeric
    )
