"""Phase 2: raw LCD v2 CSV files to the three cleaned ORC tables."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from pyspark.sql import SparkSession

from lcdweather.ingest.contract import DAILY_TABLE, HOURLY_TABLE, MONTHLY_TABLE
from lcdweather.ingest.daily import build_daily
from lcdweather.ingest.hourly import build_hourly
from lcdweather.ingest.monthly import build_monthly
from lcdweather.ingest.reader import read_raw
from lcdweather.ingest.reports import stations_frame, with_report_keys, with_station_identity
from lcdweather.ingest.writer import TableTarget, ensure_database, table_target, write_table
from lcdweather.stations import Station

TABLE_BUILDERS = (
    (HOURLY_TABLE, build_hourly),
    (DAILY_TABLE, build_daily),
    (MONTHLY_TABLE, build_monthly),
)


@dataclass(frozen=True)
class IngestRequest:
    input_path: str
    output_path: str
    database: str
    years: Sequence[int]
    stations: Sequence[Station]
    register_tables: bool = True
    table_prefix: str = ""


def run_ingest(spark: SparkSession, request: IngestRequest) -> list[TableTarget]:
    """Build and write ``lcd_hourly``, ``lcd_daily`` and ``lcd_monthly``; return their targets."""
    raw = read_raw(spark, request.input_path, request.years)
    reports = with_station_identity(
        with_report_keys(raw, request.years), stations_frame(spark, request.stations)
    )
    if request.register_tables:
        ensure_database(spark, request.database)
    targets = []
    for table, build in TABLE_BUILDERS:
        target = table_target(request.output_path, request.database, table, request.table_prefix)
        write_table(build(reports), target, request.register_tables)
        targets.append(target)
    return targets
