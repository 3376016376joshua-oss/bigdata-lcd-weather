import csv
import glob

import pytest

pytest.importorskip("pyspark")

from lcdweather.ml.export import export_result, export_results, is_remote  # noqa: E402

ROWS = [
    {"model": "linear_regression", "rmse": 4.25, "note": None},
    {"model": "gbt_regressor", "rmse": 4.5, "note": "a, quoted"},
]
EXPECTED = [
    {"model": "linear_regression", "rmse": "4.25", "note": ""},
    {"model": "gbt_regressor", "rmse": "4.5", "note": "a, quoted"},
]


def _read(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_only_filesystem_uris_are_remote():
    assert is_remote("hdfs:///user/x/lcd/results")
    assert not is_remote("results")
    assert not is_remote("/tmp/results")


def test_local_export_writes_one_csv_per_table(spark, tmp_path):
    frame = spark.createDataFrame([("KSEA", 1), ("KPHX", 2)], "city_code string, cluster int")

    export_results(spark, {"q7_metrics": ROWS, "kmeans": frame, "empty": []}, str(tmp_path))

    assert sorted(path.name for path in tmp_path.iterdir()) == ["kmeans.csv", "q7_metrics.csv"]
    assert _read(tmp_path / "q7_metrics.csv") == EXPECTED
    assert _read(tmp_path / "kmeans.csv") == [
        {"city_code": "KSEA", "cluster": "1"},
        {"city_code": "KPHX", "cluster": "2"},
    ]


def test_remote_export_writes_a_single_part_file_with_one_header(spark, tmp_path):
    results_uri = f"file://{tmp_path}"

    export_result(spark, ROWS, "q7_metrics", results_uri)
    # Overwriting must not fail when the job is run again.
    export_result(spark, ROWS, "q7_metrics", results_uri)

    parts = glob.glob(str(tmp_path / "q7_metrics" / "part-*.csv"))
    assert len(parts) == 1
    assert _read(parts[0]) == EXPECTED
