"""Run the Phase 4 queries with Spark SQL and export their results."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING

from lcdweather.analysis.catalog import AnalysisQuery
from lcdweather.analysis.sql import render_query

if TYPE_CHECKING:
    from pyspark.sql import DataFrame, SparkSession

ResultWriter = Callable[["DataFrame", str], str]


def run_query(spark: SparkSession, query: AnalysisQuery, database: str) -> DataFrame:
    """Run one query file against the cleaned tables of ``database``."""
    try:
        statement = render_query(query.read_sql(), database)
    except ValueError as error:
        raise ValueError(f"{query.path}: {error}") from error
    return spark.sql(statement)


def run_analysis(
    spark: SparkSession,
    queries: Iterable[AnalysisQuery],
    database: str,
    write_result: ResultWriter,
) -> dict[str, str]:
    """Run every query and hand its result to ``write_result(frame, name)``.

    Returns where each result was written, keyed by result name.
    """
    written = {}
    for query in queries:
        written[query.name] = write_result(run_query(spark, query, database), query.name)
    return written
