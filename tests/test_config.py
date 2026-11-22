import subprocess
import unittest
from pathlib import Path

from lcdweather import config

REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_SH = REPO_ROOT / "scripts" / "env.sh"
SHARED_VARIABLES = {
    config.ENV_NETID: "netid",
    config.ENV_HDFS_ROOT: "hdfs_root",
    config.ENV_HIVE_DB: "hive_db",
    config.ENV_FIRST_YEAR: "first_year",
    config.ENV_LAST_YEAR: "last_year",
    config.ENV_BASE_URL: "base_url",
    config.ENV_LOCAL_RAW_DIR: "local_raw_dir",
    config.ENV_FIVETHIRTYEIGHT_DIR: "fivethirtyeight_dir",
    config.ENV_MANIFESTS_DIR: "manifests_dir",
    config.ENV_RESULTS_DIR: "results_dir",
    config.ENV_FIGURES_DIR: "figures_dir",
}


def values_from_env_sh(overrides: dict) -> dict:
    """What scripts/env.sh exports when sourced with only ``overrides`` set."""
    printing = "; ".join(f'echo "{name}=${name}"' for name in SHARED_VARIABLES)
    completed = subprocess.run(
        ["bash", "-c", f'source "{ENV_SH}"; {printing}'],
        env={"PATH": "/usr/bin:/bin", **overrides},
        check=True,
        capture_output=True,
        text=True,
    )
    return dict(line.split("=", 1) for line in completed.stdout.splitlines())


class SettingsTest(unittest.TestCase):
    def test_defaults_match_the_cluster_conventions(self):
        settings = config.load_settings({})
        self.assertEqual(settings.netid, "wl3564")
        self.assertEqual(settings.hive_db, "wl3564_nyu_edu")
        self.assertEqual(list(settings.years), list(range(2010, 2026)))
        self.assertEqual(settings.raw_zone, "hdfs:///user/wl3564_nyu_edu/lcd/raw")
        self.assertEqual(settings.clean_zone, "hdfs:///user/wl3564_nyu_edu/lcd/clean")
        self.assertEqual(settings.results_zone, "hdfs:///user/wl3564_nyu_edu/lcd/results")
        self.assertEqual(
            settings.raw_file("USW00094728", 2014),
            "hdfs:///user/wl3564_nyu_edu/lcd/raw/USW00094728/LCD_USW00094728_2014.csv",
        )
        self.assertEqual(
            settings.fivethirtyeight_file("KNYC"),
            "hdfs:///user/wl3564_nyu_edu/lcd/fivethirtyeight/KNYC.csv",
        )

    def test_netid_changes_the_derived_defaults(self):
        settings = config.load_settings({config.ENV_NETID: "yw9614"})
        self.assertEqual(settings.hdfs_root, "hdfs:///user/yw9614_nyu_edu/lcd")
        self.assertEqual(settings.hive_db, "yw9614_nyu_edu")

    def test_explicit_values_win(self):
        settings = config.load_settings(
            {
                config.ENV_HDFS_ROOT: "file:///tmp/lcd/",
                config.ENV_HIVE_DB: "scratch",
                config.ENV_FIRST_YEAR: "2014",
                config.ENV_LAST_YEAR: "2015",
            }
        )
        self.assertEqual(settings.raw_zone, "file:///tmp/lcd/raw")
        self.assertEqual(settings.hive_db, "scratch")
        self.assertEqual(list(settings.years), [2014, 2015])

    def test_scheme_less_hdfs_root_stays_on_hdfs(self):
        settings = config.load_settings({config.ENV_HDFS_ROOT: "/user/yw9614_nyu_edu/lcd/"})
        self.assertEqual(settings.hdfs_root, "hdfs:///user/yw9614_nyu_edu/lcd")
        self.assertEqual(settings.results_zone, "hdfs:///user/yw9614_nyu_edu/lcd/results")

    def test_bad_years_are_rejected(self):
        with self.assertRaises(ValueError):
            config.load_settings({config.ENV_FIRST_YEAR: "twenty"})
        with self.assertRaises(ValueError):
            config.load_settings({config.ENV_FIRST_YEAR: "2020", config.ENV_LAST_YEAR: "2010"})

    def test_env_sh_agrees_with_python(self):
        cases = (
            {},
            {config.ENV_NETID: "lz3516"},
            {config.ENV_HDFS_ROOT: "hdfs:///tmp/lcd/", config.ENV_LAST_YEAR: "2012"},
            {config.ENV_HDFS_ROOT: "/user/lz3516_nyu_edu/lcd/"},
            {config.ENV_HDFS_ROOT: "file:///tmp/lcd"},
        )
        for overrides in cases:
            with self.subTest(overrides=overrides):
                settings = config.load_settings(overrides)
                expected = {
                    name: str(getattr(settings, attribute))
                    for name, attribute in SHARED_VARIABLES.items()
                }
                self.assertEqual(values_from_env_sh(overrides), expected)


if __name__ == "__main__":
    unittest.main()
