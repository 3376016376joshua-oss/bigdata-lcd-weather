"""Write the Phase 1 check results as the three small CSV manifests."""

from __future__ import annotations

import csv
import os
from collections.abc import Callable, Iterable, Sequence
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


ReportKey = tuple[str, int]


def _read_rows_by_key(path: Path, columns: Sequence[str]) -> dict[ReportKey, list[list[str]]]:
    """Existing report rows grouped by (station, year); empty when the report does not exist."""
    if not path.is_file():
        return {}
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        if tuple(next(reader, ())) != tuple(columns):
            raise ValueError(f"{path}: expected columns {','.join(columns)}")
        grouped: dict[ReportKey, list[list[str]]] = {}
        for row in reader:
            grouped.setdefault((row[0], int(row[1])), []).append(row)
    return grouped


def _merge_csv(
    path: Path,
    columns: Sequence[str],
    checks: Sequence[FileCheck],
    rows_for: Callable[[FileCheck], Iterable[Sequence[object]]],
) -> None:
    """Replace the rows of the checked (station, year) keys and keep every other row."""
    grouped: dict[ReportKey, list[Sequence[object]]] = dict(_read_rows_by_key(path, columns))
    for check in checks:
        grouped[(check.station, check.year)] = list(rows_for(check))
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(columns)
        for key in sorted(grouped):
            writer.writerows(grouped[key])
    os.replace(temporary, path)


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


def _report_type_count_rows(check: FileCheck) -> list[list[object]]:
    return [
        [check.station, check.year, report_type, rows]
        for report_type, rows in sorted(check.report_type_counts.items())
    ]


def _missing_day_rows(check: FileCheck) -> list[list[object]]:
    return [
        [
            check.station,
            check.year,
            missing.day.isoformat(),
            _flag(missing.missing_hourly),
            _flag(missing.missing_daily_summary),
        ]
        for missing in check.missing_days
    ]


def write_reports(checks: Iterable[FileCheck], manifests_dir: Path) -> None:
    """Update ``file_checks.csv``, ``report_type_counts.csv`` and ``missing_days.csv``.

    Rows of the checked (station, year) files are replaced; rows of other files are kept, so
    checking a subset does not drop the results of earlier runs.
    """
    checked = list(checks)
    _merge_csv(
        manifests_dir / FILE_CHECKS_NAME,
        FILE_CHECK_COLUMNS,
        checked,
        lambda check: [_file_check_row(check)],
    )
    _merge_csv(
        manifests_dir / REPORT_TYPE_COUNTS_NAME,
        REPORT_TYPE_COUNT_COLUMNS,
        checked,
        _report_type_count_rows,
    )
    _merge_csv(manifests_dir / MISSING_DAYS_NAME, MISSING_DAY_COLUMNS, checked, _missing_day_rows)
