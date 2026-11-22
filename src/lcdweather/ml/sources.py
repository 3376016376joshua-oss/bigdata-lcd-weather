"""Where the Phase 5 jobs read their cleaned hourly and daily tables from."""

from __future__ import annotations

from dataclasses import dataclass

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from lcdweather.ingest.contract import PRIMARY_STATION_COLUMN
from lcdweather.ml.synthetic import (
    CONSECUTIVE_DAYS_SPEC,
    YEAR_ROUND_SPEC,
    synthetic_tables,
)


@dataclass(frozen=True)
class WeatherTables:
    hourly: DataFrame
    daily: DataFrame


def primary_station_tables(hourly: DataFrame, daily: DataFrame) -> WeatherTables:
    """Rows of each city's primary station only.

    Los Angeles has two stations under one city code in 2024-2025; Phase 2 flags
    the one meant for each year, so features never blend two stations.
    """
    primary = F.col(PRIMARY_STATION_COLUMN)
    return WeatherTables(hourly=hourly.where(primary), daily=daily.where(primary))


def load_hive_tables(
    spark: SparkSession, database: str, hourly_table: str, daily_table: str
) -> WeatherTables:
    return primary_station_tables(
        spark.table(f"{database}.{hourly_table}"), spark.table(f"{database}.{daily_table}")
    )


def load_synthetic_tables(spark: SparkSession, year_round: bool = False) -> WeatherTables:
    """Small generated tables for smoke runs without Hive."""
    spec = YEAR_ROUND_SPEC if year_round else CONSECUTIVE_DAYS_SPEC
    return primary_station_tables(*synthetic_tables(spark, spec))
