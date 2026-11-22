"""Project settings: years, local folders, HDFS zones and the Hive database.

Every value has a default for the NYU Dataproc cluster and can be overridden with an
``LCD_*`` environment variable. ``scripts/env.sh`` sets the same defaults for the Bash
scripts; ``tests/test_config.py`` keeps the two in step.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

ENV_NETID = "LCD_NETID"
ENV_HDFS_ROOT = "LCD_HDFS_ROOT"
ENV_HIVE_DB = "LCD_HIVE_DB"
ENV_FIRST_YEAR = "LCD_FIRST_YEAR"
ENV_LAST_YEAR = "LCD_LAST_YEAR"
ENV_BASE_URL = "LCD_BASE_URL"
ENV_LOCAL_RAW_DIR = "LCD_LOCAL_RAW_DIR"
ENV_FIVETHIRTYEIGHT_DIR = "LCD_FIVETHIRTYEIGHT_DIR"
ENV_MANIFESTS_DIR = "LCD_MANIFESTS_DIR"
ENV_RESULTS_DIR = "LCD_RESULTS_DIR"
ENV_FIGURES_DIR = "LCD_FIGURES_DIR"

DEFAULT_NETID = "wl3564"
DEFAULT_FIRST_YEAR = 2010
DEFAULT_LAST_YEAR = 2025
DEFAULT_BASE_URL = "https://www.ncei.noaa.gov/oa/local-climatological-data/v2/access"
DEFAULT_LOCAL_RAW_DIR = "data/raw"
HDFS_SCHEME = "hdfs://"
DEFAULT_FIVETHIRTYEIGHT_DIR = "data/fivethirtyeight"
DEFAULT_MANIFESTS_DIR = "manifests"
DEFAULT_RESULTS_DIR = "results"
DEFAULT_FIGURES_DIR = "figures"


def lcd_filename(station_id: str, year: int) -> str:
    """Name NOAA gives the LCD v2 file of one station and year."""
    return f"LCD_{station_id}_{year}.csv"


@dataclass(frozen=True)
class Settings:
    netid: str
    first_year: int
    last_year: int
    hdfs_root: str
    hive_db: str
    base_url: str
    local_raw_dir: str
    fivethirtyeight_dir: str
    manifests_dir: str
    results_dir: str
    figures_dir: str

    @property
    def years(self) -> range:
        return range(self.first_year, self.last_year + 1)

    @property
    def raw_zone(self) -> str:
        return f"{self.hdfs_root}/raw"

    @property
    def clean_zone(self) -> str:
        return f"{self.hdfs_root}/clean"

    @property
    def fivethirtyeight_zone(self) -> str:
        return f"{self.hdfs_root}/fivethirtyeight"

    @property
    def results_zone(self) -> str:
        return f"{self.hdfs_root}/results"

    def raw_file(self, station_id: str, year: int) -> str:
        """HDFS path of one raw station-year file."""
        return f"{self.raw_zone}/{station_id}/{lcd_filename(station_id, year)}"

    def fivethirtyeight_file(self, city_code: str) -> str:
        """HDFS path of one FiveThirtyEight validation file."""
        return f"{self.fivethirtyeight_zone}/{city_code}.csv"


def _year(env: Mapping[str, str], name: str, default: int) -> int:
    raw = env.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError as error:
        raise ValueError(f"{name} must be a year such as {default}, got {raw!r}") from error


def _cluster_uri(root: str) -> str:
    """``root`` without a trailing slash, as ``hdfs://`` when it names no scheme."""
    root = root.rstrip("/")
    return root if "://" in root else f"{HDFS_SCHEME}{root}"


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    """Build the settings from ``env`` (the process environment when omitted)."""
    env = os.environ if env is None else env

    def text(name: str, default: str) -> str:
        return env.get(name) or default

    netid = text(ENV_NETID, DEFAULT_NETID)
    first_year = _year(env, ENV_FIRST_YEAR, DEFAULT_FIRST_YEAR)
    last_year = _year(env, ENV_LAST_YEAR, DEFAULT_LAST_YEAR)
    if first_year > last_year:
        raise ValueError(f"{ENV_FIRST_YEAR}={first_year} is after {ENV_LAST_YEAR}={last_year}")
    return Settings(
        netid=netid,
        first_year=first_year,
        last_year=last_year,
        hdfs_root=_cluster_uri(text(ENV_HDFS_ROOT, f"hdfs:///user/{netid}_nyu_edu/lcd")),
        hive_db=text(ENV_HIVE_DB, f"{netid}_nyu_edu"),
        base_url=text(ENV_BASE_URL, DEFAULT_BASE_URL).rstrip("/"),
        local_raw_dir=text(ENV_LOCAL_RAW_DIR, DEFAULT_LOCAL_RAW_DIR),
        fivethirtyeight_dir=text(ENV_FIVETHIRTYEIGHT_DIR, DEFAULT_FIVETHIRTYEIGHT_DIR),
        manifests_dir=text(ENV_MANIFESTS_DIR, DEFAULT_MANIFESTS_DIR),
        results_dir=text(ENV_RESULTS_DIR, DEFAULT_RESULTS_DIR),
        figures_dir=text(ENV_FIGURES_DIR, DEFAULT_FIGURES_DIR),
    )
