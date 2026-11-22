"""Columns every cleaned table shares: station, city, time keys and the primary-station flag."""

from __future__ import annotations

from collections.abc import Sequence

from pyspark.sql import Column, DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import IntegerType, StringType, StructField, StructType

from lcdweather.ingest import parsing
from lcdweather.stations import Station

WINTER_MONTHS = (12, 1, 2)
SPRING_MONTHS = (3, 4, 5)
SUMMER_MONTHS = (6, 7, 8)
AUTUMN_MONTHS = (9, 10, 11)

# Carried from the raw rows into every table builder. The raw columns are left behind
# there: Spark matches names without regard to case, so raw ``Sunrise`` next to a cleaned
# ``sunrise`` would be ambiguous.
KEY_COLUMNS = (
    "station",
    "city",
    "city_code",
    "is_primary_station",
    "report_type",
    "obs_ts",
    "obs_date",
    "yr",
    "month",
    "season",
)

_STATION_SCHEMA = StructType(
    [
        StructField("station", StringType(), False),
        StructField("city", StringType(), False),
        StructField("city_code", StringType(), False),
        StructField("start_year", IntegerType(), False),
        StructField("end_year", IntegerType(), False),
    ]
)


def season(month: Column) -> Column:
    """Meteorological season of a month number: DJF, MAM, JJA or SON."""
    return (
        F.when(month.isin(*WINTER_MONTHS), "DJF")
        .when(month.isin(*SPRING_MONTHS), "MAM")
        .when(month.isin(*SUMMER_MONTHS), "JJA")
        .when(month.isin(*AUTUMN_MONTHS), "SON")
    )


def stations_frame(spark: SparkSession, stations: Sequence[Station]) -> DataFrame:
    """The station list as a small DataFrame keyed by ``station``."""
    rows = [
        (item.station_id, item.city, item.city_code, item.start_year, item.end_year)
        for item in stations
    ]
    return spark.createDataFrame(rows, _STATION_SCHEMA)


def with_report_keys(raw: DataFrame, years: Sequence[int]) -> DataFrame:
    """Add station, report type and time keys; keep only rows dated in ``years``.

    ``DATE`` is local standard time. Rows whose ``DATE`` cannot be read are dropped: they
    cannot be placed in a year partition.
    """
    keyed = (
        raw.withColumn("station", F.trim(F.col("STATION")))
        .withColumn("report_type", F.trim(F.col("REPORT_TYPE")))
        .withColumn("obs_ts", parsing.timestamp(F.col("DATE")))
        .where(F.col("obs_ts").isNotNull())
        .withColumn("obs_date", F.to_date(F.col("obs_ts")))
        .withColumn("yr", F.year(F.col("obs_ts")))
        .withColumn("month", F.month(F.col("obs_ts")))
    )
    return keyed.where(F.col("yr").isin(*years)).withColumn("season", season(F.col("month")))


def with_station_identity(reports: DataFrame, stations: DataFrame) -> DataFrame:
    """Add ``city``, ``city_code`` and ``is_primary_station``; drop stations not in the list.

    A station is primary in the years it stands for its city, so each city has exactly one
    primary station per year even where two stations were loaded for it.
    """
    is_primary = F.col("yr").between(F.col("start_year"), F.col("end_year"))
    return (
        reports.join(F.broadcast(stations), on="station", how="inner")
        .withColumn("is_primary_station", is_primary)
        .drop("start_year", "end_year")
    )
