"""Phase 2 job: raw LCD v2 CSV files to the cleaned ORC tables lcd_hourly, lcd_daily, lcd_monthly.

    spark-submit --py-files lcdweather.zip jobs/phase2_ingest.py [--years 2010-2013] ...

``scripts/run_phase2.sh`` builds the zip and submits this job with the cluster settings.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from lcdweather.acquire.cli import parse_years
from lcdweather.config import Settings, load_settings
from lcdweather.ingest.locations import job_locations, local_warehouse
from lcdweather.ingest.pipeline import IngestRequest, run_ingest
from lcdweather.ingest.session import build_session
from lcdweather.stations import load_stations

APP_NAME = "lcd-phase2-ingest"


def parse_args(argv: Sequence[str] | None, settings: Settings) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--input", help="raw zone: folder holding LCD_<station>_<year>.csv files")
    parser.add_argument("--output", help="cleaned zone: folder that receives one folder per table")
    parser.add_argument("--db", default=settings.hive_db, help="Hive database of the tables")
    parser.add_argument(
        "--years",
        type=parse_years,
        default=list(settings.years),
        help="years to load, e.g. 2014, 2010-2013 or 2010,2014 (default: all)",
    )
    parser.add_argument(
        "--stations", type=Path, help="station list CSV (default config/stations.csv)"
    )
    parser.add_argument(
        "--table-prefix",
        default="",
        help="prefix of the table names, so a trial run does not replace the real tables",
    )
    parser.add_argument(
        "--files-only",
        action="store_true",
        help="write the ORC files without registering tables (register with hive/ddl instead)",
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
    request = IngestRequest(
        input_path=args.input or locations.raw,
        output_path=args.output or locations.clean,
        database=args.db,
        years=args.years,
        stations=load_stations(args.stations),
        register_tables=not args.files_only,
        table_prefix=args.table_prefix,
    )
    try:
        for target in run_ingest(spark, request):
            print(f"wrote {target.qualified_name} to {target.path}")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
