from __future__ import annotations

import pytest

from lcdweather.config import load_settings
from lcdweather.ingest.locations import job_locations, local_warehouse, raw_file_glob


def test_cluster_run_uses_the_hdfs_zones():
    cluster = job_locations(load_settings({}), local=False, warehouse="spark-warehouse")

    assert cluster.raw == "hdfs:///user/wl3564_nyu_edu/lcd/raw"
    assert cluster.clean == "hdfs:///user/wl3564_nyu_edu/lcd/clean"
    assert cluster.fivethirtyeight == "hdfs:///user/wl3564_nyu_edu/lcd/fivethirtyeight"
    assert cluster.results == "hdfs:///user/wl3564_nyu_edu/lcd/results"


def test_local_run_uses_folders_in_the_checkout():
    settings = load_settings({"LCD_RESULTS_DIR": "out"})

    local = job_locations(settings, local=True, warehouse=local_warehouse({}))

    assert local.raw == "data/raw"
    assert local.clean == "spark-warehouse/clean"
    assert local.fivethirtyeight == "data/fivethirtyeight"
    assert local.results == "out"


def test_local_warehouse_can_be_moved():
    assert local_warehouse({"LCD_LOCAL_WAREHOUSE": "/tmp/warehouse/"}) == "/tmp/warehouse"
    assert local_warehouse({"LCD_LOCAL_WAREHOUSE": ""}) == "spark-warehouse"


def test_raw_file_glob():
    assert raw_file_glob([2014]) == "LCD_*_2014.csv"
    assert raw_file_glob([2011, 2010, 2011]) == "LCD_*_{2010,2011}.csv"
    with pytest.raises(ValueError, match="at least one year"):
        raw_file_glob([])
