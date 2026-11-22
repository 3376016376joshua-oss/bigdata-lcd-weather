"""Write small result tables as CSV: one local file, or one HDFS directory each."""

from __future__ import annotations

import csv
import logging
import os
from collections.abc import Mapping, Sequence
from typing import Any, Union

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.types import StringType, StructField, StructType

from lcdweather.config import is_hdfs_uri, local_path

ResultTable = Union[DataFrame, list[dict]]

logger = logging.getLogger(__name__)


def _cell(value: Any) -> str:
    return "" if value is None else str(value)


def write_local_csv(path: str, columns: Sequence[str], rows: Sequence[Sequence[Any]]) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        writer.writerows([[_cell(value) for value in row] for row in rows])


def _rows_to_frame(spark: SparkSession, rows: list[dict]) -> DataFrame:
    columns = list(rows[0].keys())
    schema = StructType([StructField(name, StringType(), True) for name in columns])
    data = [
        tuple(None if row[name] is None else str(row[name]) for name in columns) for row in rows
    ]
    return spark.createDataFrame(data, schema)


def _export_remote(frame: DataFrame, target: str) -> None:
    # A single part file keeps `hdfs dfs -getmerge` output to one header line.
    frame.coalesce(1).write.mode("overwrite").option("header", True).csv(target)


def export_result(spark: SparkSession, table: ResultTable, name: str, results_dir: str) -> None:
    """Export one table to `<results_dir>/<name>.csv` (local) or `<name>/` (remote)."""
    is_frame = isinstance(table, DataFrame)
    if not is_frame and not table:
        logger.warning("Result %s is empty and was not exported", name)
        return
    if is_hdfs_uri(results_dir):
        frame = table if is_frame else _rows_to_frame(spark, table)
        _export_remote(frame, f"{results_dir.rstrip('/')}/{name}")
        return
    path = os.path.join(local_path(results_dir), f"{name}.csv")
    if is_frame:
        write_local_csv(path, table.columns, [tuple(row) for row in table.collect()])
    else:
        columns = list(table[0].keys())
        write_local_csv(path, columns, [[row[name_] for name_ in columns] for row in table])


def export_results(
    spark: SparkSession, tables: Mapping[str, ResultTable], results_dir: str
) -> None:
    for name, table in tables.items():
        export_result(spark, table, name, results_dir)
        logger.info("Exported %s to %s", name, results_dir)
