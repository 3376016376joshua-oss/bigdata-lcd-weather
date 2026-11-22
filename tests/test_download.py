import hashlib
import tempfile
import unittest
from pathlib import Path

from lcd_http_server import FakeLcdServer
from lcdweather.acquire.download import download_all
from lcdweather.acquire.fetch import DownloadError, FetchOptions, fetch_to_file
from lcdweather.acquire.manifest import read_manifest
from lcdweather.acquire.targets import DownloadTarget, build_url, raw_relative_path

STATION = "USW00094728"
URL_PATH_2014 = "/2014/LCD_USW00094728_2014.csv"
URL_PATH_2015 = "/2015/LCD_USW00094728_2015.csv"
BODY_2014 = b'"STATION","DATE"\n' + b'"USW00094728","2014-01-01T00:51:00"\n' * 4000
BODY_2015 = b'"STATION","DATE"\n"USW00094728","2015-01-01T00:51:00"\n'
CUT_AT_BYTES = 1000
FIXED_TIME = "2026-01-02T03:04:05Z"
NO_WAIT = FetchOptions(retries=3, timeout_seconds=10, backoff_seconds=0)


def no_sleep(seconds):
    """Retries in tests do not wait."""


def target_for(server, year):
    return DownloadTarget(
        station_id=STATION,
        year=year,
        url=build_url(server.base_url, STATION, year),
        relative_path=raw_relative_path(STATION, year),
    )


class ServerTestCase(unittest.TestCase):
    def setUp(self):
        self.server = FakeLcdServer({URL_PATH_2014: BODY_2014, URL_PATH_2015: BODY_2015})
        self.server.__enter__()
        self.addCleanup(self.server.__exit__, None, None, None)
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)


class FetchTest(ServerTestCase):
    def fetch(self, url_path=URL_PATH_2014, options=NO_WAIT):
        destination = self.folder / "raw" / "file.csv"
        fetch_to_file(self.server.base_url + url_path, destination, options, sleep=no_sleep)
        return destination

    def test_downloads_the_file(self):
        destination = self.fetch()
        self.assertEqual(destination.read_bytes(), BODY_2014)
        self.assertEqual([path.name for path in destination.parent.iterdir()], ["file.csv"])

    def test_retries_after_server_errors(self):
        self.server.fail_first[URL_PATH_2014] = 2
        self.assertEqual(self.fetch().read_bytes(), BODY_2014)
        self.assertEqual(len(self.server.requests_for(URL_PATH_2014)), 3)

    def test_gives_up_after_the_allowed_retries(self):
        self.server.fail_first[URL_PATH_2014] = 10
        with self.assertRaises(DownloadError):
            self.fetch()
        self.assertEqual(len(self.server.requests_for(URL_PATH_2014)), NO_WAIT.retries + 1)
        self.assertFalse((self.folder / "raw" / "file.csv").exists())

    def test_missing_file_fails_without_retrying(self):
        with self.assertRaises(DownloadError):
            self.fetch("/2014/LCD_USW00000000_2014.csv")
        self.assertEqual(len(self.server.requests), 1)

    def test_resumes_a_transfer_that_was_cut(self):
        self.server.cut_first[URL_PATH_2014] = CUT_AT_BYTES
        self.assertEqual(self.fetch().read_bytes(), BODY_2014)
        self.assertEqual(self.server.requests_for(URL_PATH_2014), [None, f"bytes={CUT_AT_BYTES}-"])

    def test_restarts_when_the_server_ignores_the_resume(self):
        self.server.cut_first[URL_PATH_2014] = CUT_AT_BYTES
        self.server.honour_range = False
        self.assertEqual(self.fetch().read_bytes(), BODY_2014)

    def test_stale_part_file_is_not_reused(self):
        part = self.folder / "raw" / "file.csv.part"
        part.parent.mkdir(parents=True)
        part.write_bytes(b"left over from an older version of the file")
        self.assertEqual(self.fetch().read_bytes(), BODY_2014)
        self.assertEqual(self.server.requests_for(URL_PATH_2014), [None])


class DownloadAllTest(ServerTestCase):
    def run_download(self, targets, **options):
        messages = []
        summary = download_all(
            targets,
            self.folder / "raw",
            self.folder / "manifests" / "download_manifest.csv",
            NO_WAIT,
            workers=2,
            now=lambda: FIXED_TIME,
            report=messages.append,
            **options,
        )
        return summary, messages

    def manifest(self):
        return read_manifest(self.folder / "manifests" / "download_manifest.csv")

    def test_records_size_hash_and_time(self):
        targets = [target_for(self.server, 2014), target_for(self.server, 2015)]
        summary, _ = self.run_download(targets)
        self.assertEqual((summary.downloaded, summary.skipped, summary.failures), (2, 0, []))
        entry = self.manifest()[(STATION, 2014)]
        self.assertEqual(entry.url, targets[0].url)
        self.assertEqual(entry.bytes, len(BODY_2014))
        self.assertEqual(entry.sha256, hashlib.sha256(BODY_2014).hexdigest())
        self.assertEqual(entry.downloaded_at, FIXED_TIME)
        saved = self.folder / "raw" / STATION / "LCD_USW00094728_2014.csv"
        self.assertEqual(saved.read_bytes(), BODY_2014)

    def test_rerun_skips_files_already_downloaded(self):
        targets = [target_for(self.server, 2014), target_for(self.server, 2015)]
        self.run_download(targets)
        summary, _ = self.run_download(targets)
        self.assertEqual((summary.downloaded, summary.skipped), (0, 2))
        self.assertEqual(len(self.server.requests), 2)

    def test_rerun_fetches_a_file_that_went_missing_or_changed_size(self):
        targets = [target_for(self.server, 2014), target_for(self.server, 2015)]
        self.run_download(targets)
        (self.folder / "raw" / targets[0].relative_path).unlink()
        (self.folder / "raw" / targets[1].relative_path).write_bytes(b"truncated")
        summary, _ = self.run_download(targets)
        self.assertEqual((summary.downloaded, summary.skipped), (2, 0))

    def test_force_downloads_again(self):
        targets = [target_for(self.server, 2015)]
        self.run_download(targets)
        summary, _ = self.run_download(targets, force=True)
        self.assertEqual((summary.downloaded, summary.skipped), (1, 0))

    def test_failure_is_reported_and_other_files_still_recorded(self):
        targets = [target_for(self.server, 2014), target_for(self.server, 2016)]
        summary, messages = self.run_download(targets)
        self.assertEqual(summary.downloaded, 1)
        self.assertEqual(len(summary.failures), 1)
        self.assertIn("HTTP 404", summary.failures[0])
        self.assertTrue(any(message.startswith("FAILED") for message in messages))
        self.assertEqual(list(self.manifest()), [(STATION, 2014)])

    def test_partial_run_keeps_other_manifest_rows(self):
        self.run_download([target_for(self.server, 2014)])
        self.run_download([target_for(self.server, 2015)])
        self.assertEqual(sorted(self.manifest()), [(STATION, 2014), (STATION, 2015)])


if __name__ == "__main__":
    unittest.main()
