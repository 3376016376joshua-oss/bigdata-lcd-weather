"""Phase 3 job: compare lcd_daily with FiveThirtyEight for 2014-07-01 to 2015-06-30.

Writes validation_538 (per-city correlation and mean absolute difference of daily maximum,
minimum and mean temperature and precipitation) and validation_538_daily (the joined days).
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from lcdweather.config import Settings, load_settings
from lcdweather.ingest.contract import DAILY_TABLE
from lcdweather.ingest.locations import job_locations, local_warehouse
from lcdweather.ingest.phase3 import run_validation
from lcdweather.ingest.session import build_session
from lcdweather.ingest.writer import read_table, table_target

APP_NAME = "lcd-phase3-validate"


def parse_args(argv: Sequence[str] | None, settings: Settings) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--clean", help="cleaned zone holding the lcd_daily folder")
    parser.add_argument("--db", default=settings.hive_db, help="Hive database of lcd_daily")
    parser.add_argument("--fivethirtyeight", help="folder holding the <CODE>.csv files")
    parser.add_argument("--results", help="folder that receives the result CSVs")
    parser.add_argument(
        "--from-files",
        action="store_true",
        help="read the ORC files in --clean instead of the Hive table",
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
    target = table_target(args.clean or locations.clean, args.db, DAILY_TABLE)
    registered = not (args.local or args.from_files)
    try:
        written = run_validation(
            spark,
            read_table(spark, target, registered),
            args.fivethirtyeight or locations.fivethirtyeight,
            args.results or locations.results,
        )
        for path in written:
            print(f"wrote {path}")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
