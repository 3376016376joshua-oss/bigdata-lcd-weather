"""Where the Phase 2 and 3 jobs read and write: HDFS zones, or local folders with ``--local``."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from lcdweather.config import Settings, lcd_filename

ENV_LOCAL_WAREHOUSE = "LCD_LOCAL_WAREHOUSE"
# Already in .gitignore: Spark names its default warehouse folder the same.
DEFAULT_LOCAL_WAREHOUSE = "spark-warehouse"
ANY_STATION = "*"


@dataclass(frozen=True)
class Locations:
    """Where one run reads the raw and FiveThirtyEight files and writes tables and results."""

    raw: str
    clean: str
    fivethirtyeight: str
    results: str


def local_warehouse(env: Mapping[str, str] | None = None) -> str:
    """Folder of a ``--local`` run's tables: ``LCD_LOCAL_WAREHOUSE`` or ``spark-warehouse``."""
    env = os.environ if env is None else env
    return (env.get(ENV_LOCAL_WAREHOUSE) or DEFAULT_LOCAL_WAREHOUSE).rstrip("/")


def job_locations(settings: Settings, local: bool, warehouse: str) -> Locations:
    """The HDFS zones on the cluster, or folders in the checkout for a ``--local`` run."""
    if local:
        return Locations(
            raw=settings.local_raw_dir,
            clean=f"{warehouse}/clean",
            fivethirtyeight=settings.fivethirtyeight_dir,
            results=settings.results_dir,
        )
    return Locations(
        raw=settings.raw_zone,
        clean=settings.clean_zone,
        fivethirtyeight=settings.fivethirtyeight_zone,
        results=settings.results_zone,
    )


def raw_file_glob(years: Sequence[int]) -> str:
    """Hadoop glob matching the raw file names ``LCD_<station>_<year>.csv`` of ``years``."""
    distinct = sorted(set(years))
    if not distinct:
        raise ValueError("at least one year is required")
    if len(distinct) == 1:
        return lcd_filename(ANY_STATION, distinct[0])
    alternatives = ",".join(str(year) for year in distinct)
    return lcd_filename(ANY_STATION, f"{{{alternatives}}}")
