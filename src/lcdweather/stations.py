"""The station list in ``config/stations.csv``.

``start_year`` and ``end_year`` are the years a station stands for its city in the
analysis. Los Angeles has two rows: Downtown/USC (USW00093134) through 2023 and the
international airport (USW00023174) for 2024-2025, when the USC files are incomplete.
"""

from __future__ import annotations

import csv
import os
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

ENV_STATIONS_CSV = "LCD_STATIONS_CSV"
STATIONS_CSV_RELATIVE_PATH = Path("config") / "stations.csv"
STATION_COLUMNS = (
    "station_id",
    "city",
    "city_code",
    "state",
    "lat",
    "lon",
    "start_year",
    "end_year",
)


@dataclass(frozen=True)
class Station:
    station_id: str
    city: str
    city_code: str
    state: str
    lat: float
    lon: float
    start_year: int
    end_year: int

    def covers(self, year: int) -> bool:
        """Whether this station is its city's source in ``year``."""
        return self.start_year <= year <= self.end_year


def default_stations_path() -> Path:
    """``LCD_STATIONS_CSV`` when set, else the file in the working directory or the checkout."""
    override = os.environ.get(ENV_STATIONS_CSV)
    if override:
        return Path(override)
    in_working_directory = Path.cwd() / STATIONS_CSV_RELATIVE_PATH
    if in_working_directory.is_file():
        return in_working_directory
    return Path(__file__).resolve().parents[2] / STATIONS_CSV_RELATIVE_PATH


def _station_from_row(row: dict[str, str], line_number: int, path: Path) -> Station:
    try:
        station = Station(
            station_id=row["station_id"].strip(),
            city=row["city"].strip(),
            city_code=row["city_code"].strip(),
            state=row["state"].strip(),
            lat=float(row["lat"]),
            lon=float(row["lon"]),
            start_year=int(row["start_year"]),
            end_year=int(row["end_year"]),
        )
    except (TypeError, ValueError) as error:
        raise ValueError(f"{path}:{line_number}: bad station row {row!r}") from error
    if not station.station_id or not station.city_code:
        raise ValueError(f"{path}:{line_number}: station_id and city_code are required")
    if station.start_year > station.end_year:
        raise ValueError(f"{path}:{line_number}: start_year is after end_year")
    return station


def load_stations(path: str | os.PathLike[str] | None = None) -> list[Station]:
    """Read and validate the station list, in file order."""
    csv_path = Path(path) if path is not None else default_stations_path()
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != STATION_COLUMNS:
            raise ValueError(
                f"{csv_path}: expected columns {','.join(STATION_COLUMNS)}, "
                f"got {','.join(reader.fieldnames or ())}"
            )
        stations = [
            _station_from_row(row, line_number, csv_path)
            for line_number, row in enumerate(reader, start=2)
        ]
    if not stations:
        raise ValueError(f"{csv_path}: no stations listed")
    station_ids = [station.station_id for station in stations]
    if len(set(station_ids)) != len(station_ids):
        raise ValueError(f"{csv_path}: a station_id is listed more than once")
    return stations


def city_codes(stations: Iterable[Station]) -> list[str]:
    """Distinct city codes, sorted."""
    return sorted({station.city_code for station in stations})


def station_for(stations: Iterable[Station], city_code: str, year: int) -> Station:
    """The one station that stands for ``city_code`` in ``year``."""
    matches = [
        station for station in stations if station.city_code == city_code and station.covers(year)
    ]
    if len(matches) != 1:
        raise LookupError(f"expected one station for {city_code} in {year}, found {len(matches)}")
    return matches[0]
