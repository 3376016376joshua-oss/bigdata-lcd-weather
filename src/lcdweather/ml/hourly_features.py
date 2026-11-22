"""Per city-day aggregates of the hourly readings (a backward-looking 24 h window)."""

from __future__ import annotations

from pyspark.sql import Column, DataFrame
from pyspark.sql import functions as F

from lcdweather.ml.daily_features import CITY_KEY, DATE_COL
from lcdweather.ml.settings import ROUTINE_REPORT_TYPE

TIMESTAMP_COL = "obs_ts"
# The last routine report of a day is near 23:00, so readings at or before
# these hours are at least 3 h / 12 h older than it.
LAST_HOUR_3H_BEFORE_DAY_END = 20
LAST_HOUR_12H_BEFORE_DAY_END = 11


def _routine(column: str) -> Column:
    """Routine hourly reports only, so storm-time specials do not skew the means."""
    is_routine = F.col("report_type") == ROUTINE_REPORT_TYPE
    return F.when(is_routine, F.col(column).cast("double"))


def _reading(value: Column, condition: Column | None = None, latest: bool = True) -> Column:
    """Latest (or earliest) non-null value of the day, optionally restricted."""
    keep = value.isNotNull() if condition is None else value.isNotNull() & condition
    tagged = F.when(keep, F.struct(F.col(TIMESTAMP_COL).alias("ts"), value.alias("value")))
    picked = F.max(tagged) if latest else F.min(tagged)
    return picked.getField("value")


def _temperature_aggregates() -> list[Column]:
    temp = _routine("temp_f")
    return [
        F.avg(temp).alias("h24_temp_mean"),
        F.min(temp).alias("h24_temp_min"),
        F.max(temp).alias("h24_temp_max"),
        _reading(temp).alias("h24_temp_last"),
    ]


def _moisture_aggregates() -> list[Column]:
    dewpoint = _routine("dewpt_f")
    humidity = _routine("rh_pct")
    depression = _routine("temp_f") - dewpoint
    return [
        F.avg(dewpoint).alias("h24_dewpt_mean"),
        _reading(dewpoint).alias("h24_dewpt_last"),
        F.avg(humidity).alias("h24_rh_mean"),
        F.min(humidity).alias("h24_rh_min"),
        F.max(humidity).alias("h24_rh_max"),
        _reading(humidity).alias("h24_rh_last"),
        F.avg(depression).alias("h24_dewpt_dep_mean"),
        F.min(depression).alias("h24_dewpt_dep_min"),
        _reading(depression).alias("h24_dewpt_dep_last"),
        F.sum(_routine("precip_in")).alias("h24_precip_sum"),
    ]


def _wind_aggregates() -> list[Column]:
    wind = _routine("wind_speed_mph")
    gust = F.col("wind_gust_mph").cast("double")
    return [
        F.avg(wind).alias("h24_wind_mean"),
        F.max(wind).alias("h24_wind_max"),
        _reading(wind).alias("h24_wind_last"),
        # Gusts are only reported when they occur, so no report means calm.
        F.coalesce(F.max(gust), F.lit(0.0)).alias("h24_gust_max"),
    ]


def _pressure_aggregates() -> list[Column]:
    pressure = _routine("station_pressure_hpa")
    hour = F.hour(F.col(TIMESTAMP_COL))
    last = _reading(pressure)
    three_hours_ago = _reading(pressure, hour <= LAST_HOUR_3H_BEFORE_DAY_END)
    twelve_hours_ago = _reading(pressure, hour <= LAST_HOUR_12H_BEFORE_DAY_END)
    first = _reading(pressure, latest=False)
    return [
        F.avg(pressure).alias("h24_pressure_mean"),
        last.alias("h24_pressure_last"),
        (last - three_hours_ago).alias("h24_pressure_change_3h"),
        (last - twelve_hours_ago).alias("h24_pressure_change_12h"),
        (last - first).alias("h24_pressure_change_24h"),
    ]


def _sky_aggregates() -> list[Column]:
    sky = _routine("sky_cover_okta")
    specials = F.sum(F.col("is_special").cast("int")).cast("double")
    return [
        F.avg(sky).alias("h24_sky_mean"),
        F.max(sky).alias("h24_sky_max"),
        _reading(sky).alias("h24_sky_last"),
        specials.alias("h24_special_count"),
    ]


def summarize_hourly(hourly: DataFrame) -> DataFrame:
    """One row per city-day summarising that day's hourly readings."""
    aggregates = (
        _temperature_aggregates()
        + _moisture_aggregates()
        + _wind_aggregates()
        + _pressure_aggregates()
        + _sky_aggregates()
    )
    return hourly.groupBy(CITY_KEY, DATE_COL).agg(*aggregates)
