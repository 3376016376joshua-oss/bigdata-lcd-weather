"""Check a raw LCD v2 file: header, rows per report type and missing days."""

from __future__ import annotations

import calendar
import csv
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from lcdweather.acquire.header import (
    DATE_COLUMN,
    LCD_V2_COLUMNS,
    REPORT_TYPE_COLUMN,
    STATION_COLUMN,
)

DAILY_SUMMARY_TYPE = "SOD"
MONTHLY_SUMMARY_TYPE = "SOM"
SUMMARY_TYPES = frozenset({DAILY_SUMMARY_TYPE, MONTHLY_SUMMARY_TYPE})
ISO_DATE_LENGTH = len("2014-01-01")


@dataclass(frozen=True)
class MissingDay:
    day: date
    missing_hourly: bool
    missing_daily_summary: bool


@dataclass
class FileCheck:
    station: str
    year: int
    file: str
    bytes: int
    columns: int = 0
    header_ok: bool = False
    rows: int = 0
    malformed_rows: int = 0
    station_mismatch_rows: int = 0
    first_obs: str = ""
    last_obs: str = ""
    days_in_year: int = 0
    days_with_hourly: int = 0
    days_with_daily_summary: int = 0
    report_type_counts: Counter = field(default_factory=Counter)
    missing_days: list[MissingDay] = field(default_factory=list)

    @property
    def is_sound(self) -> bool:
        """The file has the LCD v2 header and every row belongs to it."""
        return self.header_ok and self.malformed_rows == 0 and self.station_mismatch_rows == 0


def days_of_year(year: int) -> list[date]:
    first = date(year, 1, 1)
    day_count = 366 if calendar.isleap(year) else 365
    return [first + timedelta(days=offset) for offset in range(day_count)]


def _day_of(timestamp: str, year: int) -> date | None:
    """Calendar day of an LCD ``DATE`` value, or None when it is not a day of ``year``."""
    try:
        day = date.fromisoformat(timestamp[:ISO_DATE_LENGTH])
    except ValueError:
        return None
    return day if day.year == year else None


def _column_index(header: Sequence[str], name: str) -> int | None:
    return header.index(name) if name in header else None


def check_file(path: Path, station: str, year: int) -> FileCheck:
    """Read the file of one station and year once and collect its counts.

    A day counts as having hourly data when it has any report other than the SOD and SOM
    summaries (FM-15, FM-16, FM-12 and the rare merged types).
    """
    check = FileCheck(station=station, year=year, file=path.name, bytes=path.stat().st_size)
    hourly_days: set[date] = set()
    summary_days: set[date] = set()
    with path.open(newline="", encoding="utf-8", errors="replace") as handle:
        reader = csv.reader(handle)
        header = next(reader, [])
        check.columns = len(header)
        check.header_ok = tuple(header) == LCD_V2_COLUMNS
        station_at = _column_index(header, STATION_COLUMN)
        date_at = _column_index(header, DATE_COLUMN)
        type_at = _column_index(header, REPORT_TYPE_COLUMN)
        for row in reader:
            check.rows += 1
            if len(row) != len(header):
                check.malformed_rows += 1
                continue
            if station_at is not None and row[station_at] != station:
                check.station_mismatch_rows += 1
            report_type = row[type_at] if type_at is not None else ""
            check.report_type_counts[report_type] += 1
            timestamp = row[date_at] if date_at is not None else ""
            if timestamp:
                check.first_obs = min(check.first_obs or timestamp, timestamp)
                check.last_obs = max(check.last_obs, timestamp)
            day = _day_of(timestamp, year)
            if day is None:
                continue
            if report_type == DAILY_SUMMARY_TYPE:
                summary_days.add(day)
            elif report_type not in SUMMARY_TYPES:
                hourly_days.add(day)
    days = days_of_year(year)
    check.days_in_year = len(days)
    check.days_with_hourly = len(hourly_days)
    check.days_with_daily_summary = len(summary_days)
    check.missing_days = [
        MissingDay(day, day not in hourly_days, day not in summary_days)
        for day in days
        if day not in hourly_days or day not in summary_days
    ]
    return check
