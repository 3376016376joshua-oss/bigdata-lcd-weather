"""``lcd_hourly``: routine (FM-15), special (FM-16) and synoptic (FM-12) reports.

The rare SY-MT and AUTO reports are hourly observations too and are kept with them.
"""

from __future__ import annotations

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from lcdweather import units
from lcdweather.ingest import parsing
from lcdweather.ingest.contract import HOURLY_COLUMNS, HOURLY_REPORT_TYPES, REPORT_SPECIAL
from lcdweather.ingest.reports import KEY_COLUMNS


def build_hourly(reports: DataFrame) -> DataFrame:
    """Typed hourly reports in degF, mph, miles, inches and hPa, without exact duplicates."""
    measured = reports.where(F.col("report_type").isin(*HOURLY_REPORT_TYPES)).select(
        *KEY_COLUMNS,
        units.c_to_f(parsing.number(F.col("HourlyDryBulbTemperature"))).alias("temp_f"),
        units.c_to_f(parsing.number(F.col("HourlyDewPointTemperature"))).alias("dewpt_f"),
        units.c_to_f(parsing.number(F.col("HourlyWetBulbTemperature"))).alias("wetbulb_f"),
        parsing.number(F.col("HourlyRelativeHumidity")).alias("rh_pct"),
        units.ms_to_mph(parsing.number(F.col("HourlyWindSpeed"))).alias("wind_speed_mph"),
        units.ms_to_mph(parsing.number(F.col("HourlyWindGustSpeed"))).alias("wind_gust_mph"),
        parsing.whole_number(F.col("HourlyWindDirection")).alias("wind_dir_deg"),
        parsing.number(F.col("HourlyStationPressure")).alias("station_pressure_hpa"),
        parsing.number(F.col("HourlySeaLevelPressure")).alias("sea_level_pressure_hpa"),
        parsing.number(F.col("HourlyPressureChange")).alias("pressure_change_hpa"),
        units.km_to_mi(parsing.number(F.col("HourlyVisibility"))).alias("visibility_mi"),
        parsing.text_or_null(F.col("HourlySkyConditions")).alias("sky_conditions"),
        parsing.sky_cover_okta(F.col("HourlySkyConditions")).alias("sky_cover_okta"),
        units.mm_to_in(parsing.amount(F.col("HourlyPrecipitation"))).alias("precip_in"),
        F.hour(F.col("obs_ts")).alias("hour"),
        (F.col("report_type") == REPORT_SPECIAL).alias("is_special"),
    )
    return measured.select(*HOURLY_COLUMNS).dropDuplicates()
