"""Read the raw zone: LCD v2 station-year CSV files, every column as text."""

from __future__ import annotations

from collections.abc import Sequence

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.types import StringType, StructField, StructType

from lcdweather.acquire.header import LCD_V2_COLUMNS
from lcdweather.ingest.locations import raw_file_glob

CSV_QUOTE = '"'


def raw_schema() -> StructType:
    """All 125 LCD v2 columns as nullable strings."""
    return StructType([StructField(name, StringType(), True) for name in LCD_V2_COLUMNS])


def read_raw(spark: SparkSession, input_path: str, years: Sequence[int]) -> DataFrame:
    """Rows of every ``LCD_<station>_<year>.csv`` under ``input_path`` for ``years``.

    The files may sit in per-station folders or directly in ``input_path``. The schema is
    given, not inferred, and Spark checks each file's header against it, so a file with
    other columns fails the job instead of loading into the wrong fields.
    """
    return (
        spark.read.schema(raw_schema())
        .option("header", True)
        .option("enforceSchema", False)
        .option("quote", CSV_QUOTE)
        .option("escape", CSV_QUOTE)
        .option("recursiveFileLookup", True)
        .option("pathGlobFilter", raw_file_glob(years))
        .csv(input_path)
    )
