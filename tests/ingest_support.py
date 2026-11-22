"""Paths to the ingest fixtures and helpers shared by the ingest and validation tests.

The raw fixture holds real LCD v2 rows (New York 2014, Los Angeles Downtown 2015 and 2024,
Los Angeles Intl 2024, Seattle 2010) on the real 125-column header, plus a few edited rows:
an exact duplicate, a row of flagged values, a row with an unreadable DATE and a station
that is not in the station list.
"""

from __future__ import annotations

import csv
from pathlib import Path

from lcdweather.stations import load_stations

REPO_ROOT = Path(__file__).resolve().parents[1]
INGEST_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "ingest"
RAW_DIR = INGEST_FIXTURES / "raw"
STATIONS_CSV = REPO_ROOT / "config" / "stations.csv"
FIVETHIRTYEIGHT_DIR = INGEST_FIXTURES / "fivethirtyeight"

FIXTURE_YEARS = (2010, 2014, 2015, 2024)
NEW_YORK = "USW00094728"
LA_DOWNTOWN = "USW00093134"
LA_AIRPORT = "USW00023174"
SEATTLE = "USW00024233"
UNLISTED_STATION = "USW00000001"
TIMESTAMP_LENGTH = len("2014-01-01T00:00:00")


def ingest_fixture(spark, output_dir, database, **overrides):
    """Run Phase 2 on the raw fixture and return the table targets."""
    # Imported here so the tests that need no Spark can use this module without pyspark.
    from lcdweather.ingest.pipeline import IngestRequest, run_ingest

    settings = {
        "input_path": str(RAW_DIR),
        "output_path": str(output_dir),
        "database": database,
        "years": FIXTURE_YEARS,
        "stations": load_stations(STATIONS_CSV),
    }
    settings.update(overrides)
    return run_ingest(spark, IngestRequest(**settings))


def raw_fixture_rows() -> list[dict]:
    """Every row of the raw fixture, read with the csv module."""
    rows = []
    for path in sorted(RAW_DIR.glob("*/LCD_*.csv")):
        with path.open(newline="", encoding="utf-8") as handle:
            rows.extend(csv.DictReader(handle))
    return rows


def expected_row_count(report_types, years=FIXTURE_YEARS) -> int:
    """Distinct fixture rows of ``report_types`` that Phase 2 should keep."""
    listed = {station.station_id for station in load_stations(STATIONS_CSV)}
    kept = {
        tuple(row.values())
        for row in raw_fixture_rows()
        if row["REPORT_TYPE"] in report_types
        and row["STATION"] in listed
        and len(row["DATE"]) == TIMESTAMP_LENGTH
        and int(row["DATE"][:4]) in years
    }
    return len(kept)
