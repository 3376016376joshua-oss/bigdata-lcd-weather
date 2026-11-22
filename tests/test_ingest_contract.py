"""The Hive DDL, the raw column list and the fixture agree with the table contract."""

from __future__ import annotations

import csv
import re

import pytest

from ingest_support import RAW_DIR, REPO_ROOT
from lcdweather.acquire.header import LCD_V2_COLUMNS
from lcdweather.ingest.contract import PARTITION_COLUMNS, TABLE_COLUMNS

DDL_DIR = REPO_ROOT / "hive" / "ddl"
COLUMN_LINE = re.compile(r"^\s+(\w+)\s+(?:STRING|INT|DOUBLE|BOOLEAN|DATE|TIMESTAMP),?$")
PARTITION_CLAUSE = re.compile(r"PARTITIONED BY \((\w+) STRING, (\w+) INT\)")


def test_fixture_files_carry_the_real_header():
    paths = sorted(RAW_DIR.glob("*/LCD_*.csv"))
    assert paths
    for path in paths:
        with path.open(newline="", encoding="utf-8") as handle:
            assert tuple(next(csv.reader(handle))) == LCD_V2_COLUMNS, path


@pytest.mark.parametrize("table", sorted(TABLE_COLUMNS))
def test_ddl_declares_the_contract_columns_in_order(table):
    ddl = (DDL_DIR / f"{table}.sql").read_text(encoding="utf-8")
    declared = [match.group(1) for line in ddl.splitlines() if (match := COLUMN_LINE.match(line))]
    partitions = PARTITION_CLAUSE.search(ddl)

    assert partitions is not None
    assert (*declared, *partitions.groups()) == TABLE_COLUMNS[table]
    assert partitions.groups() == PARTITION_COLUMNS
    assert f"CREATE EXTERNAL TABLE IF NOT EXISTS {table} (" in ddl
    assert f"LOCATION '${{hivevar:clean_zone}}/{table}'" in ddl
    assert f"MSCK REPAIR TABLE {table};" in ddl
