"""Run each job on every year window and record wall-clock time and input size."""

from __future__ import annotations

import logging
import shlex
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Callable

from lcdweather.timing.inputs import InputStats
from lcdweather.timing.plan import YearWindow
from lcdweather.timing.runner import JobTargets, TimedRun, build_command

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Experiment:
    windows: Sequence[YearWindow]
    # Job names, run in this order for every window.
    jobs: Sequence[str]
    spark_submit: str
    targets: JobTargets
    repeats: int = 1


def run_experiment(
    experiment: Experiment,
    measure: Callable[[YearWindow], InputStats],
    run: Callable[[Sequence[str]], TimedRun],
) -> list[dict]:
    """One record per (window, job, repeat); failed runs are recorded, not hidden."""
    records = []
    for window in experiment.windows:
        stats = measure(window)
        for job in experiment.jobs:
            command = build_command(job, window, experiment.spark_submit, experiment.targets)
            for repeat in range(1, experiment.repeats + 1):
                logger.info("Timing %s on %s years (run %s)", job, window.n_years, repeat)
                timed = run(command)
                if timed.exit_code != 0:
                    logger.error("%s exited with code %s", job, timed.exit_code)
                records.append(_record(job, window, repeat, stats, timed, command))
    return records


def _record(
    job: str,
    window: YearWindow,
    repeat: int,
    stats: InputStats,
    timed: TimedRun,
    command: Sequence[str],
) -> dict:
    return {
        "job": job,
        "n_years": window.n_years,
        "start_year": window.start,
        "end_year": window.end,
        "repeat": repeat,
        "input_files": stats.files,
        "input_bytes": stats.bytes,
        "input_rows": stats.rows,
        "wall_seconds": round(timed.wall_seconds, 3),
        "exit_code": timed.exit_code,
        "command": shlex.join(command),
    }


def any_failed(records: Sequence[dict]) -> bool:
    return any(record["exit_code"] != 0 for record in records)
