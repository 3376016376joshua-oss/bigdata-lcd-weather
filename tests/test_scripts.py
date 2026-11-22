"""Run the Phase 1 entry points the way the runbook does, against local stand-ins."""

import csv
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from lcd_http_server import FakeLcdServer

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts"
SAMPLE = REPO_ROOT / "tests" / "fixtures" / "LCD_USW00094728_2014_sample.csv"
STATION = "USW00094728"
LCD_FILE = "LCD_USW00094728_2014.csv"
FIVETHIRTYEIGHT_HEADER = (
    "date,actual_mean_temp,actual_min_temp,actual_max_temp,average_min_temp,average_max_temp,"
    "record_min_temp,record_max_temp,record_min_temp_year,record_max_temp_year,"
    "actual_precipitation,average_precipitation,record_precipitation"
)
CITY_CODES = ("KCLT", "KCQT", "KHOU", "KIND", "KJAX", "KMDW", "KNYC", "KPHL", "KPHX", "KSEA")
ONE_FILE = ["--years", "2014", "--stations", STATION]


class ScriptTestCase(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        self.raw = self.folder / "raw"
        self.manifests = self.folder / "manifests"

    def run_script(self, command, **environment):
        return subprocess.run(
            command,
            cwd=self.folder,
            env={**os.environ, **environment},
            capture_output=True,
            text=True,
        )

    def run_python(self, script, *arguments, **environment):
        return self.run_script([sys.executable, str(SCRIPTS / script), *arguments], **environment)

    def run_bash(self, script, *arguments, **environment):
        return self.run_script(["bash", str(SCRIPTS / script), *arguments], **environment)

    def read_csv(self, path):
        with path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))

    def place_sample(self):
        (self.raw / STATION).mkdir(parents=True)
        shutil.copy(SAMPLE, self.raw / STATION / LCD_FILE)


class DownloadScriptTest(ScriptTestCase):
    def test_downloads_into_the_raw_layout_and_writes_the_manifest(self):
        with FakeLcdServer({f"/2014/{LCD_FILE}": SAMPLE.read_bytes()}) as server:
            arguments = [*ONE_FILE, "--out", str(self.raw), "--manifest", "m/download_manifest.csv"]
            first = self.run_python("download_lcd.py", *arguments, LCD_BASE_URL=server.base_url)
            second = self.run_python("download_lcd.py", *arguments, LCD_BASE_URL=server.base_url)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertIn("downloaded 1, already present 0, failed 0", first.stdout)
        self.assertIn("downloaded 0, already present 1, failed 0", second.stdout)
        self.assertEqual((self.raw / STATION / LCD_FILE).read_bytes(), SAMPLE.read_bytes())
        (row,) = self.read_csv(self.folder / "m" / "download_manifest.csv")
        self.assertEqual(list(row), ["station", "year", "url", "bytes", "sha256", "downloaded_at"])
        self.assertEqual((row["station"], row["year"]), (STATION, "2014"))
        self.assertEqual(row["bytes"], str(SAMPLE.stat().st_size))

    def test_exit_status_reports_a_failed_download(self):
        with FakeLcdServer({}) as server:
            result = self.run_python(
                "download_lcd.py", *ONE_FILE, "--retries", "0", LCD_BASE_URL=server.base_url
            )
        self.assertEqual(result.returncode, 1)
        self.assertIn("failed 1", result.stdout)

    def test_unknown_station_is_a_usage_error(self):
        result = self.run_python("download_lcd.py", "--stations", "USW00000000")
        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown station ids", result.stderr)

    def test_bad_year_is_a_usage_error(self):
        result = self.run_python("download_lcd.py", "--years", "2015-2014")
        self.assertEqual(result.returncode, 2)


class CheckScriptTest(ScriptTestCase):
    def check(self, *arguments):
        return self.run_python(
            "check_lcd.py", "--raw", str(self.raw), "--manifests", str(self.manifests), *arguments
        )

    def test_writes_the_three_reports(self):
        self.place_sample()
        result = self.check(*ONE_FILE)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("checked 1 of 1 files, 198 rows", result.stdout)
        (file_check,) = self.read_csv(self.manifests / "file_checks.csv")
        self.assertEqual((file_check["columns"], file_check["header_ok"]), ("125", "true"))
        counts = self.read_csv(self.manifests / "report_type_counts.csv")
        self.assertEqual(
            {row["report_type"]: row["rows"] for row in counts},
            {"FM-12": "20", "FM-15": "122", "FM-16": "50", "SOD": "5", "SOM": "1"},
        )
        self.assertEqual(len(self.read_csv(self.manifests / "missing_days.csv")), 360)

    def test_checking_a_subset_keeps_the_rows_of_other_files(self):
        self.place_sample()
        other = self.raw / "USW00023174" / "LCD_USW00023174_2024.csv"
        other.parent.mkdir(parents=True)
        shutil.copy(SAMPLE, other)
        both = ["--years", "2014,2024", "--stations", f"{STATION},USW00023174"]
        self.assertEqual(self.check(*both).returncode, 1)
        names = ("file_checks.csv", "report_type_counts.csv", "missing_days.csv")
        before = {name: self.read_csv(self.manifests / name) for name in names}

        result = self.check(*ONE_FILE)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("checked 1 of 1 files", result.stdout)
        for name in names:
            self.assertEqual(self.read_csv(self.manifests / name), before[name], name)
        stations = {row["station"] for row in before["file_checks.csv"]}
        self.assertEqual(stations, {STATION, "USW00023174"})

    def test_absent_file_is_a_problem(self):
        self.place_sample()
        result = self.check("--years", "2014-2015", "--stations", STATION)
        self.assertEqual(result.returncode, 1)
        self.assertIn("LCD_USW00094728_2015.csv: file is absent", result.stderr)
        self.assertEqual(len(self.read_csv(self.manifests / "file_checks.csv")), 1)

    def test_wrong_header_is_a_problem(self):
        (self.raw / STATION).mkdir(parents=True)
        (self.raw / STATION / LCD_FILE).write_text('"STATION","DATE"\n', encoding="utf-8")
        result = self.check(*ONE_FILE)
        self.assertEqual(result.returncode, 1)
        self.assertIn("header is not the LCD v2 header (2 columns)", result.stderr)


class FetchFiveThirtyEightScriptTest(ScriptTestCase):
    def fetch(self, server):
        return self.run_bash(
            "fetch_fivethirtyeight.sh", "validation", LCD_FIVETHIRTYEIGHT_BASE_URL=server.base_url
        )

    def test_fetches_one_file_per_city(self):
        body = FIVETHIRTYEIGHT_HEADER + "\n2014-7-1,81,70,91,67,89,56,104,1919,2012,0,0.1,5.91\n"
        files = {f"/{code}.csv": body.encode() for code in CITY_CODES}
        with FakeLcdServer(files) as server:
            result = self.fetch(server)
        self.assertEqual(result.returncode, 0, result.stderr)
        fetched = sorted(path.name for path in (self.folder / "validation").iterdir())
        self.assertEqual(fetched, [f"{code}.csv" for code in CITY_CODES])
        self.assertIn("KNYC.csv 1 rows", result.stdout)

    def test_unexpected_header_fails(self):
        files = {f"/{code}.csv": b"date,temp\n" for code in CITY_CODES}
        with FakeLcdServer(files) as server:
            result = self.fetch(server)
        self.assertEqual(result.returncode, 1)
        self.assertIn("unexpected header", result.stderr)
        self.assertEqual(list((self.folder / "validation").iterdir()), [])


class UploadScriptTest(ScriptTestCase):
    def upload(self, *arguments):
        return self.run_bash(
            "upload_hdfs.sh",
            *arguments,
            LCD_NETID="yw9614",
            LCD_LOCAL_RAW_DIR=str(self.raw),
            LCD_FIVETHIRTYEIGHT_DIR=str(self.folder / "validation"),
        )

    def place_validation_file(self):
        (self.folder / "validation").mkdir()
        (self.folder / "validation" / "KNYC.csv").write_text(FIVETHIRTYEIGHT_HEADER + "\n")

    def test_dry_run_prints_the_hdfs_commands(self):
        self.place_sample()
        self.place_validation_file()
        result = self.upload("--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        zone = "hdfs:///user/yw9614_nyu_edu/lcd"
        self.assertEqual(
            [line for line in result.stdout.splitlines() if line.startswith("hdfs dfs")],
            [
                f"hdfs dfs -mkdir -p {zone}/raw/{STATION}",
                f"hdfs dfs -put -f {self.raw}/{STATION}/{LCD_FILE} {zone}/raw/{STATION}/",
                f"hdfs dfs -mkdir -p {zone}/fivethirtyeight",
                f"hdfs dfs -put -f {self.folder}/validation/KNYC.csv {zone}/fivethirtyeight/",
            ],
        )

    def test_nothing_downloaded_is_an_error(self):
        self.place_validation_file()
        result = self.upload("--dry-run")
        self.assertEqual(result.returncode, 1)
        self.assertIn("run scripts/download_lcd.py first", result.stderr)

    def test_unknown_option_is_a_usage_error(self):
        self.assertEqual(self.upload("--nope").returncode, 2)


if __name__ == "__main__":
    unittest.main()
