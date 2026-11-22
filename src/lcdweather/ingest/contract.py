"""Names of the cleaned tables and their columns, in storage order.

The other phases read only these columns. ``hive/ddl/*.sql`` declares the same columns and
``tests/test_ingest_contract.py`` keeps the two in step.
"""

from __future__ import annotations

HOURLY_TABLE = "lcd_hourly"
DAILY_TABLE = "lcd_daily"
MONTHLY_TABLE = "lcd_monthly"

REPORT_ROUTINE = "FM-15"
REPORT_SPECIAL = "FM-16"
REPORT_SYNOPTIC = "FM-12"
# Two rare kinds of hourly report (about 5,500 rows of 2 million, mostly Jacksonville): a
# synoptic report merged with a METAR, and a report from an automatic station. They are
# kept so those hours are not lost; ``report_type`` tells them apart.
REPORT_SYNOPTIC_METAR = "SY-MT"
REPORT_AUTOMATIC = "AUTO"
REPORT_DAILY_SUMMARY = "SOD"
REPORT_MONTHLY_SUMMARY = "SOM"
HOURLY_REPORT_TYPES = (
    REPORT_ROUTINE,
    REPORT_SPECIAL,
    REPORT_SYNOPTIC,
    REPORT_SYNOPTIC_METAR,
    REPORT_AUTOMATIC,
)

PARTITION_COLUMNS = ("station", "yr")
# True for the station meant for each city and year (Los Angeles has two in 2024-2025).
PRIMARY_STATION_COLUMN = "is_primary_station"

# Daily mean this many degF or more above (below) normal makes a warm (cold) extreme day.
EXTREME_DEPARTURE_F = 10.0
# Smallest measurable daily precipitation; a trace is stored as 0.0 and so counts as dry.
MEASURABLE_PRECIPITATION_IN = 0.01

HOURLY_COLUMNS = (
    "city_code",
    "city",
    "obs_ts",
    "obs_date",
    "report_type",
    "temp_f",
    "dewpt_f",
    "wetbulb_f",
    "rh_pct",
    "wind_speed_mph",
    "wind_gust_mph",
    "wind_dir_deg",
    "station_pressure_hpa",
    "sea_level_pressure_hpa",
    "pressure_change_hpa",
    "visibility_mi",
    "sky_conditions",
    "sky_cover_okta",
    "precip_in",
    "hour",
    "month",
    "season",
    "is_special",
    PRIMARY_STATION_COLUMN,
    *PARTITION_COLUMNS,
)

DAILY_COLUMNS = (
    "city_code",
    "city",
    "obs_date",
    "tmax_f",
    "tmin_f",
    "tavg_f",
    "dep_f",
    "prcp_in",
    "prcp_trace",
    "snow_in",
    "snow_depth_in",
    "hdd",
    "cdd",
    "peak_wind_mph",
    "sustained_wind_mph",
    "sunrise",
    "sunset",
    "month",
    "season",
    "doy",
    "temp_range_f",
    "is_warm_extreme",
    "is_cold_extreme",
    "is_dry_day",
    "is_wet_day",
    PRIMARY_STATION_COLUMN,
    *PARTITION_COLUMNS,
)

MONTHLY_COLUMNS = (
    "city_code",
    "city",
    "month",
    "mean_tmax_f",
    "mean_tmin_f",
    "mean_tavg_f",
    "dep_tavg_f",
    "total_prcp_in",
    "dep_prcp_in",
    "total_snow_in",
    "days_max_ge_90",
    "days_min_le_32",
    "hdd",
    "cdd",
    "normal_tavg_f",
    PRIMARY_STATION_COLUMN,
    *PARTITION_COLUMNS,
)

TABLE_COLUMNS = {
    HOURLY_TABLE: HOURLY_COLUMNS,
    DAILY_TABLE: DAILY_COLUMNS,
    MONTHLY_TABLE: MONTHLY_COLUMNS,
}
