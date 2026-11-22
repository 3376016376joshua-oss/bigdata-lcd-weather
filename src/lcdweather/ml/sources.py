"""Where the Phase 5 jobs read their cleaned hourly and daily tables from."""

from __future__ import annotations

from dataclasses import dataclass

from pyspark.sql import DataFrame, SparkSession

from lcdweather.ml.synthetic import (
    CONSECUTIVE_DAYS_SPEC,
    YEAR_ROUND_SPEC,
    synthetic_tables,
)


@dataclass(frozen=True)
class WeatherTables:
    hourly: DataFrame
    daily: DataFrame


def load_hive_tables(
    spark: SparkSession, database: str, hourly_table: str, daily_table: str
) -> WeatherTables:
    return WeatherTables(
        hourly=spark.table(f"{database}.{hourly_table}"),
        daily=spark.table(f"{database}.{daily_table}"),
    )


def load_synthetic_tables(spark: SparkSession, year_round: bool = False) -> WeatherTables:
    """Small generated tables for smoke runs without Hive."""
    spec = YEAR_ROUND_SPEC if year_round else CONSECUTIVE_DAYS_SPEC
    hourly, daily = synthetic_tables(spark, spec)
    return WeatherTables(hourly=hourly, daily=daily)
