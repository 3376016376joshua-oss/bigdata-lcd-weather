"""The Hive DDL, the raw column list and the fixture agree with the table contract."""

from __future__ import annotations

import csv
import re

import pytest

from ingest_support import RAW_DIR, REPO_ROOT, ingest_fixture
from lcdweather.acquire.header import LCD_V2_COLUMNS
from lcdweather.ingest.contract import PARTITION_COLUMNS, TABLE_COLUMNS

DDL_DIR = REPO_ROOT / "hive" / "ddl"
DDL_DATABASE = "lcd_test_ddl"
HIVEVAR = re.compile(r"\$\{hivevar:(\w+)\}")
SQL_COMMENT_PREFIX = "--"
EXTERNAL_TABLE_TYPE = "EXTERNAL"


def test_fixture_files_carry_the_real_header():
    paths = sorted(RAW_DIR.glob("*/LCD_*.csv"))
    assert paths
    for path in paths:
        with path.open(newline="", encoding="utf-8") as handle:
            assert tuple(next(csv.reader(handle))) == LCD_V2_COLUMNS, path


def _ddl_statements(table, hivevars):
    """The statements of ``hive/ddl/<table>.sql`` with the ``--hivevar`` values filled in."""
    lines = (DDL_DIR / f"{table}.sql").read_text(encoding="utf-8").splitlines()
    script = "\n".join(line for line in lines if not line.lstrip().startswith(SQL_COMMENT_PREFIX))
    script = HIVEVAR.sub(lambda match: hivevars[match.group(1)], script)
    return [statement.strip() for statement in script.split(";") if statement.strip()]


@pytest.fixture(scope="module")
def phase2_files(spark, tmp_path_factory):
    """Folder of the ORC files Phase 2 writes, without registering any table."""
    output = tmp_path_factory.mktemp("clean")
    ingest_fixture(spark, output, DDL_DATABASE, register_tables=False)
    return output


# Oracle: Hive itself. Running the DDL the way Beeline does must register a table over the
# Phase 2 files whose columns, types and partitions are those Phase 2 wrote; a typo'd type
# or a DOUBLE declared over an int column would fail here.
@pytest.mark.parametrize("table", sorted(TABLE_COLUMNS))
def test_ddl_registers_the_phase2_files_with_the_contract_schema(spark, phase2_files, table):
    hivevars = {"db": DDL_DATABASE, "clean_zone": str(phase2_files)}
    # A --files-only run leaves no database behind, so the DDL has to create it itself.
    spark.sql(f"DROP DATABASE IF EXISTS {DDL_DATABASE} CASCADE")
    current_database = spark.catalog.currentDatabase()
    try:
        for statement in _ddl_statements(table, hivevars):
            spark.sql(statement)
    finally:
        spark.catalog.setCurrentDatabase(current_database)

    registered = spark.table(f"{DDL_DATABASE}.{table}")
    written = spark.read.orc(str(phase2_files / table))
    partitions = tuple(
        column.name
        for column in spark.catalog.listColumns(table, DDL_DATABASE)
        if column.isPartition
    )

    assert tuple(registered.columns) == TABLE_COLUMNS[table]
    assert dict(registered.dtypes) == dict(written.dtypes)
    assert partitions == PARTITION_COLUMNS
    assert spark.catalog.getTable(f"{DDL_DATABASE}.{table}").tableType == EXTERNAL_TABLE_TYPE
    assert written.count() > 0
    assert registered.count() == written.count()
