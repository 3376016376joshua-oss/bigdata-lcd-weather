"""Fixtures for the Phase 4 analysis tests.

The synthetic tables are registered as Spark global temporary views, so the query files
run unchanged with ``global_temp`` standing in for the Hive database.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from analysis_synthetic import DAILY_SCHEMA, HOURLY_TEXT_SCHEMA, MONTHLY_SCHEMA

from lcdweather.analysis.catalog import discover_queries
from lcdweather.analysis.runner import run_query

REPO_DIR = Path(__file__).resolve().parents[2]
QUERIES_DIR = REPO_DIR / "hive" / "queries"
VIZ_DIR = REPO_DIR / "viz"
TEST_DATABASE = "global_temp"


class AnalysisHarness:
    """Loads synthetic cleaned tables and runs query files against them."""

    def __init__(self, spark) -> None:
        self.spark = spark
        self.queries = {query.name: query for query in discover_queries(QUERIES_DIR)}

    def load_tables(self, daily=(), hourly=(), monthly=()) -> None:
        """Replace the three cleaned tables with the given rows."""
        create = self.spark.createDataFrame
        create(list(daily), DAILY_SCHEMA).createOrReplaceGlobalTempView("lcd_daily")
        hourly_text = create(list(hourly), HOURLY_TEXT_SCHEMA)
        hourly_typed = hourly_text.withColumn(
            "obs_ts", hourly_text["obs_ts"].cast("timestamp")
        ).withColumn("obs_date", hourly_text["obs_date"].cast("date"))
        hourly_typed.createOrReplaceGlobalTempView("lcd_hourly")
        create(list(monthly), MONTHLY_SCHEMA).createOrReplaceGlobalTempView("lcd_monthly")

    def frame(self, name: str):
        return run_query(self.spark, self.queries[name], TEST_DATABASE)

    def rows(self, name: str) -> list[dict]:
        return [row.asDict() for row in self.frame(name).collect()]

    def by_key(self, name: str, *key_columns: str) -> dict:
        """Result rows keyed by the values of ``key_columns``."""
        keyed = {}
        for row in self.rows(name):
            key = tuple(row[column] for column in key_columns)
            keyed[key[0] if len(key) == 1 else key] = row
        return keyed


@pytest.fixture(scope="session")
def queries_dir() -> Path:
    return QUERIES_DIR


@pytest.fixture(scope="session")
def viz_dir() -> Path:
    return VIZ_DIR


@pytest.fixture()
def analysis(spark) -> AnalysisHarness:
    return AnalysisHarness(spark)
