"""Write a cleaned table as ORC partitioned by station and year."""

from __future__ import annotations

from dataclasses import dataclass

from pyspark.sql import DataFrame, SparkSession

from lcdweather.ingest.contract import PARTITION_COLUMNS

STORAGE_FORMAT = "orc"


@dataclass(frozen=True)
class TableTarget:
    """Where one cleaned table goes: its folder in the cleaned zone and its Hive name."""

    name: str
    path: str
    database: str

    @property
    def qualified_name(self) -> str:
        return f"{self.database}.{self.name}"


def table_target(output_path: str, database: str, table: str, prefix: str = "") -> TableTarget:
    """Target of ``table`` under ``output_path``; ``prefix`` keeps trial runs apart."""
    name = f"{prefix}{table}"
    return TableTarget(name=name, path=f"{output_path.rstrip('/')}/{name}", database=database)


def ensure_database(spark: SparkSession, database: str) -> None:
    spark.sql(f"CREATE DATABASE IF NOT EXISTS `{database}`")


def write_table(table: DataFrame, target: TableTarget, register: bool) -> None:
    """Replace the table's files, one ORC file per station-year partition.

    With ``register`` the table is also recorded in the metastore as an external table at
    ``target.path``; without it only the files are written and ``hive/ddl`` registers them.
    """
    writer = (
        table.repartition(*PARTITION_COLUMNS)
        .write.format(STORAGE_FORMAT)
        .mode("overwrite")
        .partitionBy(*PARTITION_COLUMNS)
    )
    if register:
        writer.option("path", target.path).saveAsTable(target.qualified_name)
    else:
        writer.save(target.path)


def read_table(spark: SparkSession, target: TableTarget, registered: bool) -> DataFrame:
    """A cleaned table, from the metastore when ``registered`` and from its files otherwise."""
    if registered:
        return spark.table(target.qualified_name)
    return spark.read.format(STORAGE_FORMAT).load(target.path)
