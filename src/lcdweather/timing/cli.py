"""Command line of the Phase 6 run-time scaling driver."""

from __future__ import annotations

import argparse
import logging
import os
from collections.abc import Sequence

from lcdweather.config import Settings, load_settings
from lcdweather.timing.driver import Experiment, any_failed, run_experiment
from lcdweather.timing.inputs import measure_inputs
from lcdweather.timing.plan import DEFAULT_SIZES, year_windows
from lcdweather.timing.report import RUN_COLUMNS, SUMMARY_COLUMNS, write_csv
from lcdweather.timing.runner import (
    DEFAULT_SPARK_SUBMIT,
    DEFAULT_TEMPLATES,
    JobTargets,
    run_timed,
)
from lcdweather.timing.summary import summarize

SPARK_SUBMIT_ENV = "SPARK_SUBMIT"
JOB_CHOICES = tuple(DEFAULT_TEMPLATES)
FAILURE_EXIT_CODE = 1
TIMING_ZONE = "timing"
TIMING_DB_SUFFIX = "_timing"
PLACEHOLDERS = "{spark_submit} {start} {end} {n_years} {raw_root} {clean_dir} {db} {results_dir}"


def _add_target_arguments(parser: argparse.ArgumentParser, settings: Settings) -> None:
    """Inputs and per-window scratch outputs, kept apart from the production zones."""
    scratch = f"{settings.hdfs_root}/{TIMING_ZONE}"
    parser.add_argument("--raw-root", default=settings.raw_zone)
    parser.add_argument(
        "--clean-root",
        default=f"{scratch}/clean",
        help="scratch cleaned zone; each window writes to <clean-root>/<n>y",
    )
    parser.add_argument(
        "--db-prefix",
        default=f"{settings.hive_db}{TIMING_DB_SUFFIX}",
        help="each window uses its own Hive database <db-prefix>_t<n>y",
    )
    parser.add_argument(
        "--analysis-results-root",
        default=f"{scratch}/results",
        help="each window's analysis results go to <analysis-results-root>/<n>y",
    )


def build_parser() -> argparse.ArgumentParser:
    settings = load_settings()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", type=int, nargs="+", default=list(DEFAULT_SIZES))
    parser.add_argument("--first-year", type=int, default=settings.first_year)
    parser.add_argument("--last-year", type=int, default=settings.last_year)
    parser.add_argument("--jobs", nargs="+", choices=JOB_CHOICES, default=list(JOB_CHOICES))
    parser.add_argument("--repeats", type=int, default=1)
    _add_target_arguments(parser, settings)
    parser.add_argument(
        "--spark-submit",
        default=os.environ.get(SPARK_SUBMIT_ENV, DEFAULT_SPARK_SUBMIT),
        help="spark-submit command with its options, substituted for {spark_submit}",
    )
    parser.add_argument(
        "--ingest-command",
        default=DEFAULT_TEMPLATES["ingest"],
        help=f"template; placeholders {PLACEHOLDERS}",
    )
    parser.add_argument("--analysis-command", default=DEFAULT_TEMPLATES["analysis"])
    parser.add_argument("--skip-row-count", action="store_true")
    parser.add_argument(
        "--output", default=os.path.join(settings.results_dir, "runtime_scaling.csv")
    )
    parser.add_argument(
        "--summary-output",
        default=os.path.join(settings.results_dir, "runtime_scaling_summary.csv"),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = build_parser().parse_args(argv)
    templates = {"ingest": args.ingest_command, "analysis": args.analysis_command}
    experiment = Experiment(
        windows=year_windows(args.sizes, args.first_year, args.last_year),
        templates={job: templates[job] for job in JOB_CHOICES if job in args.jobs},
        spark_submit=args.spark_submit,
        targets=JobTargets(
            raw_root=args.raw_root,
            clean_root=args.clean_root,
            database_prefix=args.db_prefix,
            results_root=args.analysis_results_root,
        ),
        repeats=args.repeats,
    )
    records = run_experiment(
        experiment,
        measure=lambda window: measure_inputs(
            args.raw_root, window, count_rows=not args.skip_row_count
        ),
        run=run_timed,
    )
    write_csv(args.output, RUN_COLUMNS, records)
    write_csv(args.summary_output, SUMMARY_COLUMNS, summarize(records))
    return FAILURE_EXIT_CODE if any_failed(records) else 0
