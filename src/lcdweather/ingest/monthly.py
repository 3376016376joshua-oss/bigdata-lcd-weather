"""``lcd_monthly``: the monthly summary (SOM) rows."""

from __future__ import annotations

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from lcdweather import units
from lcdweather.ingest import parsing
from lcdweather.ingest.contract import MONTHLY_COLUMNS, REPORT_MONTHLY_SUMMARY
from lcdweather.ingest.reports import KEY_COLUMNS

# The two freezing-day columns are named the other way round from what they hold: checked
# against the daily rows of the same files, MonthlyDaysWithGT32Temp counts days whose
# minimum was at or below 32 degF and MonthlyDaysWithLT32Temp days whose maximum was.
RAW_DAYS_MIN_LE_32 = "MonthlyDaysWithGT32Temp"
RAW_DAYS_MAX_GE_90 = "MonthlyDaysWithGT90Temp"


def _measured(reports: DataFrame) -> DataFrame:
    summaries = reports.where(F.col("report_type") == REPORT_MONTHLY_SUMMARY)
    departure_c = parsing.number(F.col("MonthlyDepartureFromNormalAverageTemperature"))
    departure_mm = parsing.number(F.col("MonthlyDepartureFromNormalPrecipitation"))
    return summaries.select(
        *KEY_COLUMNS,
        units.c_to_f(parsing.number(F.col("MonthlyMaximumTemperature"))).alias("mean_tmax_f"),
        units.c_to_f(parsing.number(F.col("MonthlyMinimumTemperature"))).alias("mean_tmin_f"),
        units.c_to_f(parsing.number(F.col("MonthlyMeanTemperature"))).alias("mean_tavg_f"),
        units.delta_c_to_f(departure_c).alias("dep_tavg_f"),
        units.mm_to_in(parsing.amount(F.col("MonthlyTotalLiquidPrecipitation"))).alias(
            "total_prcp_in"
        ),
        units.mm_to_in(departure_mm).alias("dep_prcp_in"),
        units.mm_to_in(parsing.amount(F.col("MonthlyTotalSnowfall"))).alias("total_snow_in"),
        parsing.whole_number(F.col(RAW_DAYS_MAX_GE_90)).alias("days_max_ge_90"),
        parsing.whole_number(F.col(RAW_DAYS_MIN_LE_32)).alias("days_min_le_32"),
        units.delta_c_to_f(parsing.number(F.col("MonthlyHeatingDegreeDays"))).alias("hdd"),
        units.delta_c_to_f(parsing.number(F.col("MonthlyCoolingDegreeDays"))).alias("cdd"),
    )


def build_monthly(reports: DataFrame) -> DataFrame:
    """Typed monthly summaries in degF and inches, without exact duplicates.

    LCD v2 gives the monthly mean and its departure from the 1991-2020 normal but not the
    normal itself, so ``normal_tavg_f`` is the mean minus the departure.
    """
    with_normal = _measured(reports).withColumn(
        "normal_tavg_f", F.col("mean_tavg_f") - F.col("dep_tavg_f")
    )
    return with_normal.select(*MONTHLY_COLUMNS).dropDuplicates()
