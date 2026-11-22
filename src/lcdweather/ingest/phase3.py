"""Phase 3: run the validation and the profiling and write their result files."""

from __future__ import annotations

from collections.abc import Mapping

from pyspark.sql import DataFrame, SparkSession

from lcdweather.ingest import profile, validate_538
from lcdweather.ingest.export import write_result

VALIDATION_SUMMARY_RESULT = "validation_538"
VALIDATION_DAILY_RESULT = "validation_538_daily"
PROFILE_MISSING_RESULT = "profile_missing"
PROFILE_REPORT_TYPES_RESULT = "profile_report_types"
PROFILE_RANGES_RESULT = "profile_ranges"
TABLE_ROW_COUNTS_RESULT = "table_row_counts"


def _rows(frame: DataFrame) -> list[tuple]:
    return [tuple(row) for row in frame.collect()]


def run_validation(
    spark: SparkSession, lcd_daily: DataFrame, fivethirtyeight_folder: str, results_root: str
) -> list[str]:
    """Compare ``lcd_daily`` with FiveThirtyEight and write the summary and per-day files."""
    fivethirtyeight = validate_538.read_fivethirtyeight(spark, fivethirtyeight_folder)
    joined = validate_538.join_daily(lcd_daily, fivethirtyeight).cache()
    daily_rows = _rows(joined)
    if not daily_rows:
        raise RuntimeError(
            f"no day of lcd_daily matches the FiveThirtyEight files in {fivethirtyeight_folder} "
            f"for {validate_538.VALIDATION_START} to {validate_538.VALIDATION_END}"
        )
    summary_rows = _rows(validate_538.summarize(joined))
    joined.unpersist()
    return [
        write_result(
            spark,
            results_root,
            VALIDATION_SUMMARY_RESULT,
            validate_538.SUMMARY_COLUMNS,
            summary_rows,
        ),
        write_result(
            spark,
            results_root,
            VALIDATION_DAILY_RESULT,
            validate_538.DAILY_EXPORT_COLUMNS,
            daily_rows,
        ),
    ]


def run_profile(
    spark: SparkSession, raw: DataFrame, tables: Mapping[str, DataFrame], results_root: str
) -> list[str]:
    """Profile the raw zone and the cleaned ``tables`` and write the four result files."""
    missing, ranges, counts = [], [], []
    for name, table in tables.items():
        statistics = profile.station_statistics(table)
        missing += profile.missing_rows(name, profile.profiled_columns(table), statistics)
        ranges += profile.range_rows(name, profile.numeric_columns(table), statistics)
        counts.append(profile.row_counts(name, table))
    results = (
        (PROFILE_REPORT_TYPES_RESULT, profile.REPORT_TYPE_HEADER, profile.report_type_mix(raw)),
        (PROFILE_MISSING_RESULT, profile.MISSING_HEADER, missing),
        (PROFILE_RANGES_RESULT, profile.RANGE_HEADER, ranges),
        (TABLE_ROW_COUNTS_RESULT, profile.ROW_COUNT_HEADER, counts),
    )
    return [write_result(spark, results_root, name, header, rows) for name, header, rows in results]
