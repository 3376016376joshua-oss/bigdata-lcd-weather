"""Command line options shared by the download and check scripts."""

from __future__ import annotations

import argparse
from pathlib import Path

from lcdweather.acquire.targets import DownloadTarget, plan_targets
from lcdweather.config import Settings
from lcdweather.stations import load_stations

YEAR_RANGE_SEPARATOR = "-"


def parse_years(text: str) -> list[int]:
    """``2014``, ``2010-2012`` or a comma separated mix of both."""
    years: list[int] = []
    for part in text.split(","):
        first, separator, last = part.strip().partition(YEAR_RANGE_SEPARATOR)
        try:
            start = int(first)
            end = int(last) if separator else start
        except ValueError as error:
            raise argparse.ArgumentTypeError(f"bad year or year range: {part!r}") from error
        if start > end:
            raise argparse.ArgumentTypeError(f"year range runs backwards: {part!r}")
        years.extend(range(start, end + 1))
    return years


def parse_station_ids(text: str) -> list[str]:
    return [part.strip() for part in text.split(",") if part.strip()]


def add_selection_arguments(parser: argparse.ArgumentParser, settings: Settings) -> None:
    parser.add_argument(
        "--years",
        type=parse_years,
        help=f"years to include, e.g. 2014 or 2010-2012,2024 "
        f"(default {settings.first_year}-{settings.last_year})",
    )
    parser.add_argument(
        "--stations",
        type=parse_station_ids,
        help="comma separated station ids to include (default: all in the station list)",
    )
    parser.add_argument(
        "--stations-csv",
        type=Path,
        help="station list (default config/stations.csv)",
    )


def selected_targets(arguments: argparse.Namespace, settings: Settings) -> list[DownloadTarget]:
    """The station-year files the options select."""
    stations = load_stations(arguments.stations_csv)
    return plan_targets(stations, settings, years=arguments.years, station_ids=arguments.stations)
