#!/usr/bin/env python3
"""Check the downloaded LCD v2 files: header, rows per report type and missing days.

Standard library only. Run from the repository root after ``download_lcd.py``:

    python3 scripts/check_lcd.py
    python3 scripts/check_lcd.py --raw data/raw --manifests manifests

Writes ``file_checks.csv``, ``report_type_counts.csv`` and ``missing_days.csv``. Exits with
status 1 when a selected file is absent, a header differs from the 125-column LCD v2 header,
or a file holds rows that do not belong to it. Missing days are reported, not treated as errors.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lcdweather.acquire.checks import FileCheck, check_file  # noqa: E402
from lcdweather.acquire.cli import add_selection_arguments, selected_targets  # noqa: E402
from lcdweather.acquire.reports import write_reports  # noqa: E402
from lcdweather.config import load_settings  # noqa: E402


def parse_arguments(argv: list[str] | None) -> tuple[argparse.Namespace, list]:
    settings = load_settings()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_selection_arguments(parser, settings)
    parser.add_argument("--raw", type=Path, default=Path(settings.local_raw_dir))
    parser.add_argument("--manifests", type=Path, default=Path(settings.manifests_dir))
    arguments = parser.parse_args(argv)
    try:
        targets = selected_targets(arguments, settings)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    return arguments, targets


def describe_problems(check: FileCheck) -> list[str]:
    problems = []
    if not check.header_ok:
        problems.append(f"{check.file}: header is not the LCD v2 header ({check.columns} columns)")
    if check.malformed_rows:
        problems.append(f"{check.file}: {check.malformed_rows} rows with a wrong column count")
    if check.station_mismatch_rows:
        problems.append(f"{check.file}: {check.station_mismatch_rows} rows of another station")
    return problems


def main(argv: list[str] | None = None) -> int:
    arguments, targets = parse_arguments(argv)
    checks = []
    problems = []
    for target in targets:
        path = arguments.raw / target.relative_path
        if not path.is_file():
            problems.append(f"{target.relative_path}: file is absent")
            continue
        check = check_file(path, target.station_id, target.year)
        checks.append(check)
        problems.extend(describe_problems(check))
    write_reports(checks, arguments.manifests)
    rows = sum(check.rows for check in checks)
    missing_days = sum(len(check.missing_days) for check in checks)
    print(
        f"checked {len(checks)} of {len(targets)} files, {rows} rows, "
        f"{missing_days} station-days with a gap; reports in {arguments.manifests}"
    )
    for problem in problems:
        print(f"PROBLEM {problem}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
