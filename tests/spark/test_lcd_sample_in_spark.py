"""The LCD sample read by Spark the way the raw zone is read: every column as quoted text."""

from lcdweather import units
from lcdweather.acquire.checks import check_file
from lcdweather.acquire.header import LCD_V2_COLUMNS

SAMPLE_STATION = "USW00094728"
SAMPLE_YEAR = 2014


def read_raw(spark, path):
    return spark.read.option("header", True).option("inferSchema", False).csv(str(path))


def test_sample_has_the_lcd_v2_columns_as_text(spark, lcd_sample_path):
    frame = read_raw(spark, lcd_sample_path)
    assert tuple(frame.columns) == LCD_V2_COLUMNS
    assert {field.dataType.simpleString() for field in frame.schema.fields} == {"string"}


def test_spark_and_the_stdlib_check_count_the_same_rows(spark, lcd_sample_path):
    frame = read_raw(spark, lcd_sample_path)
    counted = frame.groupBy("REPORT_TYPE").count().collect()
    expected = check_file(lcd_sample_path, SAMPLE_STATION, SAMPLE_YEAR).report_type_counts
    assert {row["REPORT_TYPE"]: row["count"] for row in counted} == dict(expected)


def test_sample_carries_the_flagged_values_parsers_must_handle(spark, lcd_sample_path):
    frame = read_raw(spark, lcd_sample_path)

    def distinct(column):
        return {row[0] for row in frame.select(column).distinct().collect()}

    assert "T" in distinct("HourlyPrecipitation")
    assert "T" in distinct("DailyPrecipitation")
    assert "T" in distinct("DailySnowfall")
    assert "VRB" in distinct("HourlyWindDirection")
    assert {"5.1s"} <= distinct("HourlyWindSpeed")
    assert {"16.093s", "4.023V", "*"} <= distinct("HourlyVisibility")


def test_unit_conversions_work_on_spark_columns(spark):
    frame = spark.createDataFrame([(0.0, 25.4), (None, None)], "temp_c double, prcp_mm double")
    converted = frame.select(
        units.c_to_f(frame["temp_c"]).alias("temp_f"),
        units.mm_to_in(frame["prcp_mm"]).alias("prcp_in"),
    ).collect()
    assert (converted[0]["temp_f"], converted[0]["prcp_in"]) == (32.0, 1.0)
    assert (converted[1]["temp_f"], converted[1]["prcp_in"]) == (None, None)
