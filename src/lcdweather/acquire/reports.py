"""Write the Phase 1 check results as the three small CSV manifests."""

from __future__ import annotations

import csv
from collections.abc import Iterable, Sequence
from pathlib import Path

from lcdweather.acquire.checks import FileCheck

FILE_CHECKS_NAME = "file_checks.csv"
REPORT_TYPE_COUNTS_NAME = "report_type_counts.csv"
MISSING_DAYS_NAME = "missing_days.csv"

FILE_CHECK_COLUMNS = (
    "station",
    "year",
    "file",
    "bytes",
    "columns",
    "header_ok",
    "rows",
    "malformed_rows",
    "station_mismatch_rows",
    "first_obs",
    "last_obs",
    "days_in_year",
    "days_with_hourly",
    "days_with_daily_summary",
    "days_missing_hourly",
    "days_missing_daily_summary",
)
REPORT_TYPE_COUNT_COLUMNS = ("station", "year", "report_type", "rows")
MISSING_DAY_COLUMNS = ("station", "year", "date", "missing_hourly", "missing_daily_summary")


def _flag(value: bool) -> str:
    return "true" if value else "false"


def _write_csv(path: Path, columns: Sequence[str], rows: Iterable[Sequence[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(columns)
        writer.writerows(rows)


def _file_check_row(check: FileCheck) -> list[object]:
    return [
        check.station,
        check.year,
        check.file,
        check.bytes,
        check.columns,
        _flag(check.header_ok),
        check.rows,
        check.malformed_rows,
        check.station_mismatch_rows,
        check.first_obs,
        check.last_obs,
        check.days_in_year,
        check.days_with_hourly,
        check.days_with_daily_summary,
        check.days_in_year - check.days_with_hourly,
        check.days_in_year - check.days_with_daily_summary,
    ]


def write_reports(checks: Iterable[FileCheck], manifests_dir: Path) -> None:
    """Write ``file_checks.csv``, ``report_type_counts.csv`` and ``missing_days.csv``."""
    ordered = sorted(checks, key=lambda check: (check.station, check.year))
    _write_csv(
        manifests_dir / FILE_CHECKS_NAME,
        FILE_CHECK_COLUMNS,
        (_file_check_row(check) for check in ordered),
    )
    _write_csv(
        manifests_dir / REPORT_TYPE_COUNTS_NAME,
        REPORT_TYPE_COUNT_COLUMNS,
        (
            [check.station, check.year, report_type, rows]
            for check in ordered
            for report_type, rows in sorted(check.report_type_counts.items())
        ),
    )
    _write_csv(
        manifests_dir / MISSING_DAYS_NAME,
        MISSING_DAY_COLUMNS,
        (
            [
                check.station,
                check.year,
                missing.day.isoformat(),
                _flag(missing.missing_hourly),
                _flag(missing.missing_daily_summary),
            ]
            for check in ordered
            for missing in check.missing_days
        ),
    )
