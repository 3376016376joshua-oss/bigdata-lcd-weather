from __future__ import annotations

import datetime

import pytest

pytest.importorskip("pyspark")

from lcdweather.ingest.export import (  # noqa: E402
    format_cell,
    is_local_path,
    write_hadoop_csv,
    write_local_csv,
    write_result,
)


@pytest.mark.parametrize(
    ("value", "text"),
    [
        (None, ""),
        (True, "true"),
        (False, "false"),
        (3, "3"),
        (0.5, "0.5"),
        ("KNYC", "KNYC"),
        (datetime.date(2014, 7, 1), "2014-07-01"),
    ],
)
def test_format_cell(value, text):
    assert format_cell(value) == text


@pytest.mark.parametrize(
    ("path", "local"),
    [
        ("results", True),
        ("/tmp/results", True),
        ("file:///tmp/results", True),
        ("hdfs:///user/wl3564_nyu_edu/lcd/results", False),
        ("gs://bucket/results", False),
    ],
)
def test_is_local_path(path, local):
    assert is_local_path(path) is local


def test_write_local_csv_creates_the_folder_and_quotes_commas(tmp_path):
    path = tmp_path / "new" / "result.csv"

    write_local_csv(
        path, ("city", "n", "flag"), [("New York, NY", 2, True), ("Chicago", None, False)]
    )

    assert path.read_text(encoding="utf-8").splitlines() == [
        "city,n,flag",
        '"New York, NY",2,true',
        "Chicago,,false",
    ]


def test_write_result_to_a_local_folder_needs_no_spark(tmp_path):
    written = write_result(None, f"file://{tmp_path}", "counts", ("table", "n"), [("lcd_daily", 5)])

    assert written == str(tmp_path / "counts.csv")
    assert (tmp_path / "counts.csv").read_text(encoding="utf-8") == "table,n\nlcd_daily,5\n"


def test_write_hadoop_csv_writes_one_part_file_that_getmerge_can_copy(spark, tmp_path):
    destination = tmp_path / "counts"
    rows = [("lcd_daily", 5, True), ("lcd_monthly", None, False)]

    write_hadoop_csv(spark, str(destination), ("table", "n", "flag"), rows)
    write_hadoop_csv(spark, str(destination), ("table", "n", "flag"), rows)

    parts = sorted(destination.glob("part-*.csv"))
    assert len(parts) == 1
    assert parts[0].read_text(encoding="utf-8").splitlines() == [
        "table,n,flag",
        "lcd_daily,5,true",
        "lcd_monthly,,false",
    ]
