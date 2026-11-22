"""Size of the raw LCD input (files, bytes, rows) behind a year window."""

from __future__ import annotations

import glob
import os
import subprocess
from dataclasses import dataclass

from lcdweather.timing.plan import YearWindow

REMOTE_SCHEMES = ("hdfs://", "gs://", "viewfs://")
RAW_FILE_PATTERN = "LCD_*_{year}.csv"
READ_CHUNK_BYTES = 1 << 20
HEADER_ROWS_PER_FILE = 1


@dataclass(frozen=True)
class InputStats:
    files: int
    bytes: int
    rows: int | None


def raw_globs(raw_root: str, window: YearWindow) -> list[str]:
    """One glob per year over `<raw_root>/<station_id>/LCD_<station_id>_<year>.csv`."""
    root = raw_root.rstrip("/")
    return [f"{root}/*/{RAW_FILE_PATTERN.format(year=year)}" for year in window.years]


def _count_lines(stream) -> int:
    lines = 0
    while True:
        chunk = stream.read(READ_CHUNK_BYTES)
        if not chunk:
            return lines
        lines += chunk.count(b"\n")


def _local_stats(patterns: list[str], count_rows: bool) -> InputStats:
    paths = sorted(path for pattern in patterns for path in glob.glob(pattern))
    total_bytes = sum(os.path.getsize(path) for path in paths)
    rows = None
    if count_rows:
        lines = 0
        for path in paths:
            with open(path, "rb") as handle:
                lines += _count_lines(handle)
        rows = lines - HEADER_ROWS_PER_FILE * len(paths)
    return InputStats(files=len(paths), bytes=total_bytes, rows=rows)


def parse_du_output(output: str) -> list[int]:
    """File sizes from `hdfs dfs -du` lines (`<bytes> [<disk bytes>] <path>`)."""
    sizes = []
    for line in output.splitlines():
        fields = line.split()
        if fields:
            sizes.append(int(fields[0]))
    return sizes


def _hdfs_stats(patterns: list[str], count_rows: bool, hdfs_command: str) -> InputStats:
    listing = subprocess.run(
        [hdfs_command, "dfs", "-du", *patterns],
        capture_output=True,
        text=True,
        check=False,
    )
    if listing.returncode != 0:
        raise RuntimeError(f"hdfs dfs -du failed for {patterns}: {listing.stderr.strip()}")
    sizes = parse_du_output(listing.stdout)
    rows = None
    if count_rows:
        with subprocess.Popen(
            [hdfs_command, "dfs", "-cat", *patterns], stdout=subprocess.PIPE
        ) as cat:
            lines = _count_lines(cat.stdout)
        if cat.returncode != 0:
            raise RuntimeError(f"hdfs dfs -cat failed for {patterns}")
        rows = lines - HEADER_ROWS_PER_FILE * len(sizes)
    return InputStats(files=len(sizes), bytes=sum(sizes), rows=rows)


def measure_inputs(
    raw_root: str,
    window: YearWindow,
    count_rows: bool = True,
    hdfs_command: str = "hdfs",
) -> InputStats:
    """Files, bytes and data rows of the raw CSVs for the window's years."""
    patterns = raw_globs(raw_root, window)
    if raw_root.startswith(REMOTE_SCHEMES):
        return _hdfs_stats(patterns, count_rows, hdfs_command)
    return _local_stats(patterns, count_rows)
