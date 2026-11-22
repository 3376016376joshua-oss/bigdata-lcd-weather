import tempfile
import unittest
from pathlib import Path

from lcdweather.acquire.targets import build_url, plan_targets
from lcdweather.config import load_settings
from lcdweather.stations import STATION_COLUMNS, city_codes, load_stations, station_for

REPO_ROOT = Path(__file__).resolve().parents[1]
STATIONS_CSV = REPO_ROOT / "config" / "stations.csv"
FIVETHIRTYEIGHT_CODES = [
    "KCLT",
    "KCQT",
    "KHOU",
    "KIND",
    "KJAX",
    "KMDW",
    "KNYC",
    "KPHL",
    "KPHX",
    "KSEA",
]
USC = "USW00093134"
LAX = "USW00023174"
CENTRAL_PARK = "USW00094728"


class StationListTest(unittest.TestCase):
    def setUp(self):
        self.stations = load_stations(STATIONS_CSV)
        self.settings = load_settings({})

    def test_ten_cities_from_eleven_stations(self):
        self.assertEqual(len(self.stations), 11)
        self.assertEqual(city_codes(self.stations), FIVETHIRTYEIGHT_CODES)

    def test_every_city_has_exactly_one_station_each_year(self):
        for code in FIVETHIRTYEIGHT_CODES:
            for year in self.settings.years:
                with self.subTest(code=code, year=year):
                    self.assertEqual(station_for(self.stations, code, year).city_code, code)

    def test_los_angeles_switches_to_the_airport_in_2024(self):
        self.assertEqual(station_for(self.stations, "KCQT", 2023).station_id, USC)
        self.assertEqual(station_for(self.stations, "KCQT", 2024).station_id, LAX)
        self.assertEqual(station_for(self.stations, "KCQT", 2025).station_id, LAX)

    def test_unknown_city_or_year_is_an_error(self):
        with self.assertRaises(LookupError):
            station_for(self.stations, "KXXX", 2014)
        with self.assertRaises(LookupError):
            station_for(self.stations, "KNYC", 2009)

    def test_coordinates_are_in_the_contiguous_united_states(self):
        for station in self.stations:
            with self.subTest(station=station.station_id):
                self.assertTrue(24 < station.lat < 50)
                self.assertTrue(-125 < station.lon < -66)


class StationListValidationTest(unittest.TestCase):
    def load(self, text):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "stations.csv"
            path.write_text(text, encoding="utf-8")
            return load_stations(path)

    def test_wrong_columns(self):
        with self.assertRaises(ValueError):
            self.load("station,city\nUSW1,X\n")

    def test_bad_number(self):
        header = ",".join(STATION_COLUMNS)
        with self.assertRaises(ValueError):
            self.load(f"{header}\nUSW1,X,KX,NY,north,-73,2010,2025\n")

    def test_years_out_of_order(self):
        header = ",".join(STATION_COLUMNS)
        with self.assertRaises(ValueError):
            self.load(f"{header}\nUSW1,X,KX,NY,40,-73,2025,2010\n")

    def test_duplicate_station(self):
        header = ",".join(STATION_COLUMNS)
        row = "USW1,X,KX,NY,40,-73,2010,2025\n"
        with self.assertRaises(ValueError):
            self.load(f"{header}\n{row}{row}")

    def test_empty_list(self):
        with self.assertRaises(ValueError):
            self.load(",".join(STATION_COLUMNS) + "\n")


class DownloadPlanTest(unittest.TestCase):
    def setUp(self):
        self.stations = load_stations(STATIONS_CSV)
        self.settings = load_settings({})

    def test_url_is_built_from_station_and_year(self):
        self.assertEqual(
            build_url(self.settings.base_url, CENTRAL_PARK, 2014),
            "https://www.ncei.noaa.gov/oa/local-climatological-data/v2/access/"
            "2014/LCD_USW00094728_2014.csv",
        )

    def test_full_plan_is_160_files_plus_the_two_airport_files(self):
        targets = plan_targets(self.stations, self.settings)
        self.assertEqual(len(targets), 162)
        self.assertEqual(len({target.url for target in targets}), 162)
        years_by_station = {}
        for target in targets:
            years_by_station.setdefault(target.station_id, []).append(target.year)
        self.assertEqual(years_by_station[LAX], [2024, 2025])
        self.assertEqual(years_by_station[USC], list(range(2010, 2026)))
        self.assertEqual(years_by_station[CENTRAL_PARK], list(range(2010, 2026)))

    def test_local_path_mirrors_the_raw_zone(self):
        (target,) = plan_targets(
            self.stations, self.settings, years=[2014], station_ids=[CENTRAL_PARK]
        )
        self.assertEqual(target.relative_path, "USW00094728/LCD_USW00094728_2014.csv")
        self.assertTrue(
            self.settings.raw_file(CENTRAL_PARK, 2014).endswith("/raw/" + target.relative_path)
        )

    def test_year_filter(self):
        targets = plan_targets(self.stations, self.settings, years=[2014, 2024])
        self.assertEqual(len(targets), 10 + 11)

    def test_unknown_station_is_rejected(self):
        with self.assertRaises(ValueError):
            plan_targets(self.stations, self.settings, station_ids=["USW00000000"])


if __name__ == "__main__":
    unittest.main()
