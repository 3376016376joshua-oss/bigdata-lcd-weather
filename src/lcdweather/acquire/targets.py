"""Which station-year files Phase 1 downloads, and from where."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from lcdweather.config import Settings, lcd_filename
from lcdweather.stations import Station


@dataclass(frozen=True)
class DownloadTarget:
    station_id: str
    year: int
    url: str
    relative_path: str


def build_url(base_url: str, station_id: str, year: int) -> str:
    """NOAA publishes one file per station and year under a folder per year."""
    return f"{base_url}/{year}/{lcd_filename(station_id, year)}"


def raw_relative_path(station_id: str, year: int) -> str:
    """Local layout, the same as the HDFS raw zone: ``<station_id>/LCD_<station_id>_<year>.csv``."""
    return f"{station_id}/{lcd_filename(station_id, year)}"


def download_years(station: Station, settings: Settings) -> range:
    """Years to download for a station.

    A station is kept through the last project year even after another station takes over
    its city, so the raw zone holds the incomplete Los Angeles Downtown/USC files of
    2024-2025 that justify the switch to the airport station.
    """
    return range(max(station.start_year, settings.first_year), settings.last_year + 1)


def plan_targets(
    stations: Sequence[Station],
    settings: Settings,
    years: Iterable[int] | None = None,
    station_ids: Iterable[str] | None = None,
) -> list[DownloadTarget]:
    """Every file to download, optionally limited to some years and stations."""
    wanted_years = None if years is None else set(years)
    wanted_stations = None if station_ids is None else set(station_ids)
    if wanted_stations is not None:
        unknown = wanted_stations - {station.station_id for station in stations}
        if unknown:
            raise ValueError(f"unknown station ids: {', '.join(sorted(unknown))}")
    targets = []
    for station in stations:
        if wanted_stations is not None and station.station_id not in wanted_stations:
            continue
        for year in download_years(station, settings):
            if wanted_years is not None and year not in wanted_years:
                continue
            targets.append(
                DownloadTarget(
                    station_id=station.station_id,
                    year=year,
                    url=build_url(settings.base_url, station.station_id, year),
                    relative_path=raw_relative_path(station.station_id, year),
                )
            )
    return targets
