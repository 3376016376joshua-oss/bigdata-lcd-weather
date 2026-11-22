"""Phase 3 profiling: report-type mix, missing values, value ranges and row counts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import NumericType

from lcdweather.ingest import parsing

# Identify a row rather than measure anything, so they are not profiled.
IDENTITY_COLUMNS = ("station", "city_code", "city", "yr", "is_primary_station")
GROUP_COLUMNS = ("station", "city_code")
RANGE_STATISTICS = ("min", "max", "mean", "stddev")
PERCENT = 100.0

REPORT_TYPE_HEADER = ("station", "yr", "report_type", "n_rows")
MISSING_HEADER = (
    "table",
    "station",
    "city_code",
    "column",
    "n_rows",
    "n_missing",
    "pct_missing",
)
RANGE_HEADER = ("table", "station", "city_code", "column", "n_values", *RANGE_STATISTICS)
ROW_COUNT_HEADER = (
    "table",
    "n_rows",
    "n_primary_rows",
    "n_stations",
    "n_station_years",
    "first_yr",
    "last_yr",
)


def report_type_mix(raw: DataFrame) -> list[tuple]:
    """Rows per station, year and ``REPORT_TYPE`` in the raw zone, blank types included."""
    counted = (
        raw.select(
            F.trim(F.col("STATION")).alias("station"),
            F.year(parsing.timestamp(F.col("DATE"))).alias("yr"),
            F.coalesce(F.trim(F.col("REPORT_TYPE")), F.lit("")).alias("report_type"),
        )
        .groupBy("station", "yr", "report_type")
        .agg(F.count(F.lit(1)).alias("n_rows"))
        .orderBy("station", "yr", "report_type")
    )
    return [tuple(row) for row in counted.collect()]


def profiled_columns(table: DataFrame) -> list[str]:
    return [name for name in table.columns if name not in IDENTITY_COLUMNS]


def numeric_columns(table: DataFrame) -> list[str]:
    return [
        field.name
        for field in table.schema.fields
        if isinstance(field.dataType, NumericType) and field.name not in IDENTITY_COLUMNS
    ]


def station_statistics(table: DataFrame) -> list[dict]:
    """One dict per station: ``n_rows``, ``present__<column>`` and ``<statistic>__<column>``."""
    statistics = [F.count(F.lit(1)).alias("n_rows")]
    statistics += [F.count(F.col(name)).alias(f"present__{name}") for name in table.columns]
    for name in numeric_columns(table):
        statistics += [
            F.min(F.col(name)).alias(f"min__{name}"),
            F.max(F.col(name)).alias(f"max__{name}"),
            F.avg(F.col(name)).alias(f"mean__{name}"),
            F.stddev(F.col(name)).alias(f"stddev__{name}"),
        ]
    grouped = table.groupBy(*GROUP_COLUMNS).agg(*statistics).orderBy(*GROUP_COLUMNS)
    return [row.asDict() for row in grouped.collect()]


def missing_rows(
    table_name: str, columns: Sequence[str], statistics: Sequence[Mapping]
) -> list[tuple]:
    """Per station and column: rows, missing values and their share in percent."""
    rows = []
    for station in statistics:
        n_rows = station["n_rows"]
        for column in columns:
            n_missing = n_rows - station[f"present__{column}"]
            pct_missing = PERCENT * n_missing / n_rows if n_rows else None
            rows.append(
                (
                    table_name,
                    station["station"],
                    station["city_code"],
                    column,
                    n_rows,
                    n_missing,
                    pct_missing,
                )
            )
    return rows


def range_rows(
    table_name: str, columns: Sequence[str], statistics: Sequence[Mapping]
) -> list[tuple]:
    """Per station and numeric column: values present, minimum, maximum, mean and spread."""
    rows = []
    for station in statistics:
        for column in columns:
            spread = tuple(station[f"{statistic}__{column}"] for statistic in RANGE_STATISTICS)
            rows.append(
                (
                    table_name,
                    station["station"],
                    station["city_code"],
                    column,
                    station[f"present__{column}"],
                    *spread,
                )
            )
    return rows


def row_counts(table_name: str, table: DataFrame) -> tuple:
    """Exact size of a table: all rows, primary-station rows, stations and years covered."""
    counted = table.agg(
        F.count(F.lit(1)).alias("n_rows"),
        F.sum(F.col("is_primary_station").cast("int")).alias("n_primary_rows"),
        F.countDistinct("station").alias("n_stations"),
        F.countDistinct("station", "yr").alias("n_station_years"),
        F.min("yr").alias("first_yr"),
        F.max("yr").alias("last_yr"),
    ).first()
    n_primary_rows = counted["n_primary_rows"] or 0
    return (
        table_name,
        counted["n_rows"],
        n_primary_rows,
        counted["n_stations"],
        counted["n_station_years"],
        counted["first_yr"],
        counted["last_yr"],
    )
