"""Phase 3 job: profile the raw zone and the cleaned tables.

Writes profile_report_types (rows per station, year and report type in the raw zone),
profile_missing and profile_ranges (per station and column of each cleaned table) and
table_row_counts (exact size of lcd_hourly, lcd_daily and lcd_monthly).
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from lcdweather.acquire.cli import parse_years
from lcdweather.config import Settings, load_settings
from lcdweather.ingest.contract import TABLE_COLUMNS
from lcdweather.ingest.locations import job_locations, local_warehouse
from lcdweather.ingest.phase3 import run_profile
from lcdweather.ingest.reader import read_raw
from lcdweather.ingest.session import build_session
from lcdweather.ingest.writer import read_table, table_target

APP_NAME = "lcd-phase3-profile"


def parse_args(argv: Sequence[str] | None, settings: Settings) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--input", help="raw zone: folder holding LCD_<station>_<year>.csv files")
    parser.add_argument("--clean", help="cleaned zone holding one folder per table")
    parser.add_argument("--db", default=settings.hive_db, help="Hive database of the tables")
    parser.add_argument(
        "--years",
        type=parse_years,
        default=list(settings.years),
        help="years of raw files to count, e.g. 2010-2013 (default: all)",
    )
    parser.add_argument("--results", help="folder that receives the result CSVs")
    parser.add_argument(
        "--from-files",
        action="store_true",
        help="read the ORC files in --clean instead of the Hive tables",
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="run on this machine without Hive, reading and writing local folders",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    settings = load_settings()
    args = parse_args(argv, settings)
    warehouse = local_warehouse()
    locations = job_locations(settings, args.local, warehouse)
    spark = build_session(APP_NAME, args.local, warehouse)
    clean = args.clean or locations.clean
    registered = not (args.local or args.from_files)
    try:
        tables = {
            name: read_table(spark, table_target(clean, args.db, name), registered)
            for name in TABLE_COLUMNS
        }
        raw = read_raw(spark, args.input or locations.raw, args.years)
        for path in run_profile(spark, raw, tables, args.results or locations.results):
            print(f"wrote {path}")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
