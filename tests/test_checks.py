import csv
import tempfile
import unittest
from datetime import date
from pathlib import Path

from lcdweather.acquire.checks import check_file, days_of_year
from lcdweather.acquire.header import LCD_V2_COLUMNS
from lcdweather.acquire.reports import write_reports

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "tests" / "fixtures"
SAMPLE = FIXTURES / "LCD_USW00094728_2014_sample.csv"
SAMPLE_REPORT_TYPE_COUNTS = {"FM-15": 122, "FM-16": 50, "FM-12": 20, "SOD": 5, "SOM": 1}
SAMPLE_DAYS = 5
STATION = "USW00094728"


def lcd_row(timestamp, report_type, station=STATION):
    row = [""] * len(LCD_V2_COLUMNS)
    row[LCD_V2_COLUMNS.index("STATION")] = station
    row[LCD_V2_COLUMNS.index("DATE")] = timestamp
    row[LCD_V2_COLUMNS.index("REPORT_TYPE")] = report_type
    return row


def write_lcd_file(folder, rows, header=LCD_V2_COLUMNS):
    path = Path(folder) / "LCD_USW00094728_2015.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, quoting=csv.QUOTE_ALL, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)
    return path


class HeaderTest(unittest.TestCase):
    def test_lcd_v2_header_has_125_distinct_columns(self):
        self.assertEqual(len(LCD_V2_COLUMNS), 125)
        self.assertEqual(len(set(LCD_V2_COLUMNS)), 125)
        self.assertEqual(LCD_V2_COLUMNS[:2], ("STATION", "DATE"))


class SampleFileTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.check = check_file(SAMPLE, STATION, 2014)

    def test_header_and_rows_are_sound(self):
        self.assertEqual(self.check.columns, 125)
        self.assertTrue(self.check.header_ok)
        self.assertTrue(self.check.is_sound)
        self.assertEqual(self.check.rows, sum(SAMPLE_REPORT_TYPE_COUNTS.values()))

    def test_rows_per_report_type(self):
        self.assertEqual(dict(self.check.report_type_counts), SAMPLE_REPORT_TYPE_COUNTS)

    def test_observation_span(self):
        self.assertEqual(self.check.first_obs, "2014-01-01T00:00:00")
        self.assertEqual(self.check.last_obs, "2014-01-31T23:59:00")

    def test_days_present_and_missing(self):
        self.assertEqual(self.check.days_in_year, 365)
        self.assertEqual(self.check.days_with_hourly, SAMPLE_DAYS)
        self.assertEqual(self.check.days_with_daily_summary, SAMPLE_DAYS)
        self.assertEqual(len(self.check.missing_days), 365 - SAMPLE_DAYS)
        first_missing = self.check.missing_days[0]
        self.assertEqual(first_missing.day, date(2014, 1, 6))
        self.assertTrue(first_missing.missing_hourly and first_missing.missing_daily_summary)

    def test_monthly_summary_alone_does_not_make_a_day_present(self):
        january_31 = [day for day in self.check.missing_days if day.day == date(2014, 1, 31)]
        self.assertEqual(len(january_31), 1)


class ProblemFileTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = folder.name

    def check_2015(self, rows, header=LCD_V2_COLUMNS):
        return check_file(write_lcd_file(self.folder, rows, header), STATION, 2015)

    def test_leap_year_has_366_days(self):
        self.assertEqual(len(days_of_year(2024)), 366)
        self.assertEqual(len(days_of_year(2015)), 365)

    def test_day_missing_only_hourly_or_only_summary(self):
        rows = [
            lcd_row("2015-01-01T00:51:00", "FM-15"),
            lcd_row("2015-01-01T00:00:00", "SOD"),
            lcd_row("2015-01-02T00:00:00", "SOD"),
            lcd_row("2015-01-03T12:00:00", "FM-12"),
        ]
        check = self.check_2015(rows)
        gaps = {
            day.day: (day.missing_hourly, day.missing_daily_summary) for day in check.missing_days
        }
        self.assertNotIn(date(2015, 1, 1), gaps)
        self.assertEqual(gaps[date(2015, 1, 2)], (True, False))
        self.assertEqual(gaps[date(2015, 1, 3)], (False, True))
        self.assertEqual(gaps[date(2015, 1, 4)], (True, True))

    def test_rows_dated_outside_the_year_do_not_fill_days(self):
        check = self.check_2015([lcd_row("2014-12-31T23:51:00", "FM-15")])
        self.assertEqual(check.rows, 1)
        self.assertEqual(check.days_with_hourly, 0)

    def test_header_with_a_renamed_column(self):
        header = list(LCD_V2_COLUMNS)
        header[-1] = "SomethingElse"
        check = self.check_2015([], header=header)
        self.assertEqual(check.columns, 125)
        self.assertFalse(check.header_ok)
        self.assertFalse(check.is_sound)

    def test_header_with_a_missing_column(self):
        check = self.check_2015([], header=LCD_V2_COLUMNS[:-1])
        self.assertEqual(check.columns, 124)
        self.assertFalse(check.header_ok)

    def test_row_with_wrong_column_count(self):
        rows = [lcd_row("2015-01-01T00:51:00", "FM-15"), ["USW00094728", "2015-01-01T01:51:00"]]
        check = self.check_2015(rows)
        self.assertEqual((check.rows, check.malformed_rows), (2, 1))
        self.assertEqual(dict(check.report_type_counts), {"FM-15": 1})
        self.assertFalse(check.is_sound)

    def test_row_of_another_station(self):
        rows = [lcd_row("2015-01-01T00:51:00", "FM-15", station="USW00013739")]
        check = self.check_2015(rows)
        self.assertEqual(check.station_mismatch_rows, 1)
        self.assertFalse(check.is_sound)


class ReportsTest(unittest.TestCase):
    def test_reports_for_the_sample(self):
        with tempfile.TemporaryDirectory() as folder:
            write_reports([check_file(SAMPLE, STATION, 2014)], Path(folder))

            def read(name):
                with (Path(folder) / name).open(newline="", encoding="utf-8") as handle:
                    return list(csv.DictReader(handle))

            (file_check,) = read("file_checks.csv")
            self.assertEqual(file_check["station"], STATION)
            self.assertEqual(file_check["header_ok"], "true")
            self.assertEqual(file_check["rows"], "198")
            self.assertEqual(file_check["days_missing_hourly"], "360")
            counts = read("report_type_counts.csv")
            self.assertEqual(
                {row["report_type"]: int(row["rows"]) for row in counts}, SAMPLE_REPORT_TYPE_COUNTS
            )
            missing = read("missing_days.csv")
            self.assertEqual(len(missing), 360)
            self.assertEqual(
                missing[0],
                {
                    "station": STATION,
                    "year": "2014",
                    "date": "2014-01-06",
                    "missing_hourly": "true",
                    "missing_daily_summary": "true",
                },
            )


if __name__ == "__main__":
    unittest.main()
