"""Phase 3 validation: ``lcd_daily`` against the FiveThirtyEight U.S. Weather History files.

FiveThirtyEight published one CSV per city for 2014-07-01 to 2015-06-30, in whole degF
and inches. The comparison is of the measured values only: its normals come from records
since 1880, the LCD ones from 1991-2020, so the anomalies are expected to differ.
"""

from __future__ import annotations

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

VALIDATION_START = "2014-07-01"
VALIDATION_END = "2015-06-30"
FIVETHIRTYEIGHT_DATE_FORMAT = "yyyy-M-d"
CITY_CODE_FROM_FILE_PATTERN = r"([^/]+)\.csv$"

# metric name -> (lcd_daily column, FiveThirtyEight column)
METRICS = {
    "tmax": ("tmax_f", "actual_max_temp"),
    "tmin": ("tmin_f", "actual_min_temp"),
    "tavg": ("tavg_f", "actual_mean_temp"),
    "prcp": ("prcp_in", "actual_precipitation"),
}
SUMMARY_STATISTICS = ("n", "corr", "mae", "bias")

DAILY_EXPORT_COLUMNS = (
    "city_code",
    "city",
    "station",
    "obs_date",
    *(f"{metric}_{suffix}" for metric in METRICS for suffix in ("lcd", "538", "diff")),
)
SUMMARY_COLUMNS = (
    "city_code",
    "city",
    "n_days",
    *(f"{metric}_{statistic}" for metric in METRICS for statistic in SUMMARY_STATISTICS),
)


def read_fivethirtyeight(spark: SparkSession, folder: str) -> DataFrame:
    """Every ``<CODE>.csv`` in ``folder`` as city_code, obs_date and the four measures."""
    files = spark.read.option("header", True).csv(f"{folder.rstrip('/')}/*.csv")
    city_code = F.regexp_extract(F.input_file_name(), CITY_CODE_FROM_FILE_PATTERN, 1)
    measures = [
        F.col(source).cast("double").alias(f"{metric}_538")
        for metric, (_, source) in METRICS.items()
    ]
    return files.select(
        city_code.alias("city_code"),
        F.to_date(F.col("date"), FIVETHIRTYEIGHT_DATE_FORMAT).alias("obs_date"),
        *measures,
    )


def join_daily(lcd_daily: DataFrame, fivethirtyeight: DataFrame) -> DataFrame:
    """One row per city and validation day found in both sources, with the differences.

    Only each city's primary station is compared, so Los Angeles is Downtown/USC, the
    station FiveThirtyEight used.
    """
    first_day, last_day = (F.lit(day).cast("date") for day in (VALIDATION_START, VALIDATION_END))
    in_period = F.col("obs_date").between(first_day, last_day)
    lcd = lcd_daily.where(F.col("is_primary_station") & in_period).select(
        "city_code",
        "city",
        "station",
        "obs_date",
        *(F.col(column).alias(f"{metric}_lcd") for metric, (column, _) in METRICS.items()),
    )
    joined = lcd.join(fivethirtyeight, on=["city_code", "obs_date"], how="inner")
    for metric in METRICS:
        joined = joined.withColumn(
            f"{metric}_diff", F.col(f"{metric}_lcd") - F.col(f"{metric}_538")
        )
    return joined.select(*DAILY_EXPORT_COLUMNS).orderBy("city_code", "obs_date")


def summarize(joined: DataFrame) -> DataFrame:
    """Per city: days compared and, per measure, pairs, correlation, mean absolute
    difference and mean difference (LCD minus FiveThirtyEight)."""
    statistics = [F.count(F.lit(1)).alias("n_days")]
    for metric in METRICS:
        lcd, other, diff = (F.col(f"{metric}_{suffix}") for suffix in ("lcd", "538", "diff"))
        statistics += [
            F.count(diff).alias(f"{metric}_n"),
            F.corr(lcd, other).alias(f"{metric}_corr"),
            F.avg(F.abs(diff)).alias(f"{metric}_mae"),
            F.avg(diff).alias(f"{metric}_bias"),
        ]
    summary = joined.groupBy("city_code", "city").agg(*statistics)
    return summary.select(*SUMMARY_COLUMNS).orderBy("city_code")
