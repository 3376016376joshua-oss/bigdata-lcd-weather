"""``lcd_daily``: the daily summary (SOD) rows with anomaly, extreme and dry-day flags."""

from __future__ import annotations

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from lcdweather import units
from lcdweather.ingest import parsing
from lcdweather.ingest.contract import (
    DAILY_COLUMNS,
    EXTREME_DEPARTURE_F,
    MEASURABLE_PRECIPITATION_IN,
    REPORT_DAILY_SUMMARY,
)
from lcdweather.ingest.reports import KEY_COLUMNS


def _measured(reports: DataFrame) -> DataFrame:
    summaries = reports.where(F.col("report_type") == REPORT_DAILY_SUMMARY)
    departure_c = parsing.number(F.col("DailyDepartureFromNormalAverageTemperature"))
    return summaries.select(
        *KEY_COLUMNS,
        units.c_to_f(parsing.number(F.col("DailyMaximumDryBulbTemperature"))).alias("tmax_f"),
        units.c_to_f(parsing.number(F.col("DailyMinimumDryBulbTemperature"))).alias("tmin_f"),
        units.c_to_f(parsing.number(F.col("DailyAverageDryBulbTemperature"))).alias("tavg_f"),
        units.delta_c_to_f(departure_c).alias("dep_f"),
        units.mm_to_in(parsing.amount(F.col("DailyPrecipitation"))).alias("prcp_in"),
        parsing.is_trace(F.col("DailyPrecipitation")).alias("prcp_trace"),
        units.mm_to_in(parsing.amount(F.col("DailySnowfall"))).alias("snow_in"),
        units.mm_to_in(parsing.amount(F.col("DailySnowDepth"))).alias("snow_depth_in"),
        units.delta_c_to_f(parsing.number(F.col("DailyHeatingDegreeDays"))).alias("hdd"),
        units.delta_c_to_f(parsing.number(F.col("DailyCoolingDegreeDays"))).alias("cdd"),
        units.ms_to_mph(parsing.number(F.col("DailyPeakWindSpeed"))).alias("peak_wind_mph"),
        units.ms_to_mph(parsing.number(F.col("DailySustainedWindSpeed"))).alias(
            "sustained_wind_mph"
        ),
        parsing.clock_time(F.col("Sunrise")).alias("sunrise"),
        parsing.clock_time(F.col("Sunset")).alias("sunset"),
        F.dayofyear(F.col("obs_date")).alias("doy"),
    )


def build_daily(reports: DataFrame) -> DataFrame:
    """Typed daily summaries in degF, inches and mph, without exact duplicates.

    A flag is null when the value it is derived from is missing, so a day with no reported
    precipitation is neither dry nor wet.
    """
    flagged = (
        _measured(reports)
        .withColumn("temp_range_f", F.col("tmax_f") - F.col("tmin_f"))
        .withColumn("is_warm_extreme", F.col("dep_f") >= EXTREME_DEPARTURE_F)
        .withColumn("is_cold_extreme", F.col("dep_f") <= -EXTREME_DEPARTURE_F)
        .withColumn("is_dry_day", F.col("prcp_in") < MEASURABLE_PRECIPITATION_IN)
        .withColumn("is_wet_day", F.col("prcp_in") >= MEASURABLE_PRECIPITATION_IN)
    )
    return flagged.select(*DAILY_COLUMNS).dropDuplicates()
