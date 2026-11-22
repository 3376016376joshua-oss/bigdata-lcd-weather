"""CSV output of the scaling experiment."""

from __future__ import annotations

import csv
import os
from collections.abc import Sequence

RUN_COLUMNS = (
    "job",
    "n_years",
    "start_year",
    "end_year",
    "repeat",
    "input_files",
    "input_bytes",
    "input_rows",
    "wall_seconds",
    "exit_code",
    "command",
)
SUMMARY_COLUMNS = (
    "job",
    "n_years",
    "runs",
    "input_gb",
    "median_wall_seconds",
    "seconds_per_gb",
    "input_ratio",
    "time_ratio",
    "loglog_slope",
)


def write_csv(path: str, columns: Sequence[str], rows: Sequence[dict]) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), restval="")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: "" if row.get(key) is None else row[key] for key in columns})
