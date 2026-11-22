"""Command line of the Phase 6 run-time scaling driver."""

from __future__ import annotations

import argparse
import logging
import os
from collections.abc import Sequence

from lcdweather.config import load_settings
from lcdweather.timing.driver import Experiment, any_failed, run_experiment
from lcdweather.timing.inputs import measure_inputs
from lcdweather.timing.plan import DEFAULT_SIZES, year_windows
from lcdweather.timing.report import RUN_COLUMNS, SUMMARY_COLUMNS, write_csv
from lcdweather.timing.runner import DEFAULT_SPARK_SUBMIT, DEFAULT_TEMPLATES, run_timed
from lcdweather.timing.summary import summarize

SPARK_SUBMIT_ENV = "SPARK_SUBMIT"
JOB_CHOICES = tuple(DEFAULT_TEMPLATES)
FAILURE_EXIT_CODE = 1


def build_parser() -> argparse.ArgumentParser:
    settings = load_settings()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", type=int, nargs="+", default=list(DEFAULT_SIZES))
    parser.add_argument("--first-year", type=int, default=settings.first_year)
    parser.add_argument("--last-year", type=int, default=settings.last_year)
    parser.add_argument("--jobs", nargs="+", choices=JOB_CHOICES, default=list(JOB_CHOICES))
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--raw-root", default=settings.raw_zone)
    parser.add_argument(
        "--spark-submit",
        default=os.environ.get(SPARK_SUBMIT_ENV, DEFAULT_SPARK_SUBMIT),
        help="spark-submit command with its options, substituted for {spark_submit}",
    )
    parser.add_argument(
        "--ingest-command",
        default=DEFAULT_TEMPLATES["ingest"],
        help="template; placeholders {spark_submit} {start} {end} {n_years}",
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
