"""The text-to-value expressions, on the cell shapes found in real LCD v2 files."""

from __future__ import annotations

import pytest

pytest.importorskip("pyspark")

from pyspark.sql import functions as F  # noqa: E402

from lcdweather.ingest import parsing  # noqa: E402
from lcdweather.ingest.reports import season  # noqa: E402


def _apply(spark, expression, values, data_type="string"):
    frame = spark.createDataFrame(
        [(index, value) for index, value in enumerate(values)], f"position int, cell {data_type}"
    )
    rows = frame.select("position", expression(F.col("cell")).alias("parsed")).collect()
    return [row["parsed"] for row in sorted(rows, key=lambda row: row["position"])]


def test_number_reads_plain_signed_and_flagged_cells(spark):
    cells = ["16.093", "-11.1", "0", "270.0", "030", " 1.5 ", "0.805s", "4.023V", ".5", "+2"]

    assert _apply(spark, parsing.number, cells) == [
        16.093, -11.1, 0.0, 270.0, 30.0, 1.5, 0.805, 4.023, 0.5, 2.0,
    ]  # fmt: skip


def test_number_is_null_for_cells_without_a_value(spark):
    cells = [None, "", "  ", "T", "*", "M", "None", "VRB", "1.2*", "16-17", "BR RA", "1.5ss"]

    assert _apply(spark, parsing.number, cells) == [None] * len(cells)


def test_whole_number(spark):
    assert _apply(spark, parsing.whole_number, ["270.0", "090", "000", "7", "VRB", ""]) == [
        270, 90, 0, 7, None, None,
    ]  # fmt: skip


def test_amount_counts_a_trace_as_zero(spark):
    cells = ["T", " T ", "Ts", "0.0", "12.7", "", None, "*"]

    assert _apply(spark, parsing.amount, cells) == [0.0, 0.0, 0.0, 0.0, 12.7, None, None, None]
    assert _apply(spark, parsing.is_trace, cells) == [
        True, True, True, False, False, False, False, False,
    ]  # fmt: skip


# Oracle: METAR layer amounts are cumulative, so total cover is the largest layer amount.
def test_sky_cover_okta_is_the_total_cover_over_all_layers(spark):
    cells = [
        "CLR:00",
        "FEW:02 76.2",
        "SCT:04 9.14 BKN:07 13.41 OVC:08 30.48",
        "FEW:02 0.76 OVC:08 1.52",
        "FEW:02 BKN:07",
        "VV:09 2.74",
        "BKN:07 BKN:07",
        "X:10 1.0 OVC:08 3.0",
        "FEW:02 48.77 X:10 1.0",
        "X:10 1.0",
        "4.5",
        "",
        None,
    ]

    assert _apply(spark, parsing.sky_cover_okta, cells) == [
        0, 2, 8, 8, 7, 9, 7, 8, 2, None, None, None, None,
    ]  # fmt: skip


def test_clock_time_and_text_or_null(spark):
    assert _apply(spark, parsing.clock_time, ["0720", " 1647 ", "720", "07:20", "", None]) == [
        "0720", "1647", None, None, None, None,
    ]  # fmt: skip
    assert _apply(spark, parsing.text_or_null, ["CLR:00", "  BR RA ", "", "   ", None]) == [
        "CLR:00", "BR RA", None, None, None,
    ]  # fmt: skip


def test_timestamp_keeps_the_local_standard_time_as_written(spark):
    # 02:30 on 2014-03-09 does not exist in U.S. daylight-saving zones; LCD has no such gap.
    cells = ["2014-03-09T02:30:00", "2014-12-31T23:59:00", "not-a-date", "", None]

    def written(cell):
        # Formatted by Spark: collecting a timestamp would shift it to this machine's zone.
        return F.date_format(parsing.timestamp(cell), "yyyy-MM-dd HH:mm:ss")

    assert _apply(spark, written, cells) == [
        "2014-03-09 02:30:00",
        "2014-12-31 23:59:00",
        None,
        None,
        None,
    ]


def test_season_of_each_month(spark):
    assert _apply(spark, season, list(range(1, 13)), "int") == [
        "DJF", "DJF", "MAM", "MAM", "MAM", "JJA", "JJA", "JJA", "SON", "SON", "SON", "DJF",
    ]  # fmt: skip
