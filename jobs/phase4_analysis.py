"""Phase 4 job: answer questions 1-6 with Spark SQL and export the result tables.

Submit with spark-submit (see scripts/run_phase4.sh). Each ``hive/queries/q<N>_*.sql``
file becomes ``<results-dir>/q<N>_<name>.csv`` locally or ``<results-dir>/q<N>_<name>/``
on HDFS.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from functools import partial

from pyspark.sql import SparkSession

from lcdweather.analysis.catalog import ANALYSIS_QUESTIONS, discover_queries, select_queries
from lcdweather.analysis.export import write_result
from lcdweather.analysis.runner import run_analysis
from lcdweather.config import load_settings

APP_NAME = "lcd-phase4-analysis"
DEFAULT_QUERIES_DIR = "hive/queries"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    settings = load_settings()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument(
        "--db", default=settings.hive_db, help="Hive database of the cleaned tables"
    )
    parser.add_argument(
        "--queries-dir", default=DEFAULT_QUERIES_DIR, help="directory of the q<N>_*.sql files"
    )
    parser.add_argument(
        "--results-dir",
        default=settings.results_zone,
        help="local directory or HDFS URI for the result CSVs",
    )
    parser.add_argument(
        "--questions",
        type=int,
        nargs="+",
        choices=ANALYSIS_QUESTIONS,
        help="questions to run (default: all of 1-6)",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    queries = select_queries(discover_queries(args.queries_dir), args.questions)
    spark = SparkSession.builder.appName(APP_NAME).enableHiveSupport().getOrCreate()
    try:
        written = run_analysis(
            spark, queries, args.db, partial(write_result, results_dir=args.results_dir)
        )
    finally:
        spark.stop()
    for name, target in written.items():
        print(f"{name} -> {target}")


if __name__ == "__main__":
    main()
