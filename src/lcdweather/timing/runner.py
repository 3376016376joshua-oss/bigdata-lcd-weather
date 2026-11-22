"""Build and time the spark-submit commands of the scaling experiment."""

from __future__ import annotations

import shlex
import subprocess
import time
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Callable

from lcdweather.timing.plan import YearWindow

DEFAULT_SPARK_SUBMIT = "spark-submit"
DEFAULT_TEMPLATES = {
    "ingest": "{spark_submit} jobs/phase2_ingest.py --years {start}-{end}",
    "analysis": "{spark_submit} jobs/phase4_analysis.py --years {start}-{end}",
}


@dataclass(frozen=True)
class TimedRun:
    wall_seconds: float
    exit_code: int


def build_command(template: str, window: YearWindow, spark_submit: str) -> list[str]:
    """Fill a command template; placeholders: {spark_submit} {start} {end} {n_years}."""
    filled = template.format(
        spark_submit=spark_submit,
        start=window.start,
        end=window.end,
        n_years=window.n_years,
    )
    command = shlex.split(filled)
    if not command:
        raise ValueError("Command template produced an empty command")
    return command


def _exit_code(command: Sequence[str]) -> int:
    return subprocess.run(list(command), check=False).returncode


def run_timed(
    command: Sequence[str],
    execute: Callable[[Sequence[str]], int] = _exit_code,
    clock: Callable[[], float] = time.perf_counter,
) -> TimedRun:
    """Wall-clock seconds and exit code of one command."""
    started = clock()
    exit_code = execute(command)
    return TimedRun(wall_seconds=clock() - started, exit_code=exit_code)
