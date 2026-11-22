"""Write a small result table as CSV.

A local results folder gets one file ``<name>.csv``. A folder on HDFS (or any other
Hadoop file system) gets a directory ``<name>/`` holding one part file with a header,
which ``hdfs dfs -getmerge`` turns into ``results/<name>.csv``.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable, Sequence
from pathlib import Path
from urllib.parse import urlparse

from pyspark.sql import SparkSession
from pyspark.sql.types import StringType, StructField, StructType

LOCAL_SCHEMES = ("", "file")
CSV_SUFFIX = ".csv"


def is_local_path(path: str) -> bool:
    return urlparse(path).scheme in LOCAL_SCHEMES


def format_cell(value: object) -> str:
    """Text of one CSV cell: blank for missing, ``true``/``false`` for flags."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def format_rows(rows: Iterable[Sequence[object]]) -> list[list[str]]:
    return [[format_cell(value) for value in row] for row in rows]


def write_local_csv(path: Path, header: Sequence[str], rows: Iterable[Sequence[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(format_rows(rows))


def write_hadoop_csv(
    spark: SparkSession,
    destination: str,
    header: Sequence[str],
    rows: Iterable[Sequence[object]],
) -> None:
    """Replace the directory ``destination`` with one headed CSV part file."""
    schema = StructType([StructField(column, StringType(), True) for column in header])
    cells = [[None if value is None else format_cell(value) for value in row] for row in rows]
    frame = spark.createDataFrame(cells, schema)
    frame.coalesce(1).write.mode("overwrite").option("header", True).csv(destination)


def write_result(
    spark: SparkSession,
    results_root: str,
    name: str,
    header: Sequence[str],
    rows: Sequence[Sequence[object]],
) -> str:
    """Write ``rows`` under ``results_root`` and return where they went."""
    if is_local_path(results_root):
        path = Path(urlparse(results_root).path) / f"{name}{CSV_SUFFIX}"
        write_local_csv(path, header, rows)
        return str(path)
    destination = f"{results_root.rstrip('/')}/{name}"
    write_hadoop_csv(spark, destination, header, rows)
    return destination
