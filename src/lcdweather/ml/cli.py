"""Shared command line and start-up for the Phase 5 spark-submit jobs."""

from __future__ import annotations

import argparse
import logging
from typing import Callable

from lcdweather.config import load_settings
from lcdweather.ingest.contract import DAILY_TABLE, HOURLY_TABLE
from lcdweather.ml.export import ResultTable, export_results
from lcdweather.ml.session import build_session
from lcdweather.ml.sources import WeatherTables, load_hive_tables, load_synthetic_tables

GRID_CHOICES = ("full", "quick")


def build_parser(description: str, with_grid: bool = True) -> argparse.ArgumentParser:
    settings = load_settings()
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--database", default=settings.hive_db, help="Hive database")
    parser.add_argument("--hourly-table", default=HOURLY_TABLE)
    parser.add_argument("--daily-table", default=DAILY_TABLE)
    parser.add_argument(
        "--results-dir",
        default=settings.results_dir,
        help="local folder, or an hdfs:// folder when running on the cluster",
    )
    parser.add_argument("--master", default=None, help="Spark master (else spark-submit's)")
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="smoke-run on small generated tables instead of the Hive tables",
    )
    if with_grid:
        parser.add_argument(
            "--grid",
            choices=GRID_CHOICES,
            default="full",
            help="hyper-parameter grid size; 'quick' is a one-point smoke grid",
        )
    return parser


def run_job(
    app_name: str,
    args: argparse.Namespace,
    compute: Callable[[WeatherTables], dict[str, ResultTable]],
    year_round_synthetic: bool = False,
) -> None:
    """Open the session, load the tables, compute and export the result tables."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    spark = build_session(app_name, master=args.master, hive=not args.synthetic)
    if args.synthetic:
        tables = load_synthetic_tables(spark, year_round=year_round_synthetic)
    else:
        tables = load_hive_tables(spark, args.database, args.hourly_table, args.daily_table)
    export_results(spark, compute(tables), args.results_dir)
