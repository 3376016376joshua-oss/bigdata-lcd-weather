"""The three job entry points, each run the way a ``--local`` user runs it."""

from __future__ import annotations

import csv
import os
import subprocess
import sys

from ingest_support import (
    FIVETHIRTYEIGHT_DIR,
    RAW_DIR,
    REPO_ROOT,
    STATIONS_CSV,
    expected_row_count,
)

JOB_TIMEOUT_SECONDS = 600


def _run_job(job, arguments, warehouse):
    environment = dict(
        os.environ,
        PYTHONPATH=os.pathsep.join(
            filter(None, [str(REPO_ROOT / "src"), os.environ.get("PYTHONPATH")])
        ),
        # The Spark workers must run the interpreter that runs the driver.
        PYSPARK_PYTHON=sys.executable,
        LCD_LOCAL_WAREHOUSE=str(warehouse),
    )
    completed = subprocess.run(
        [sys.executable, str(REPO_ROOT / "jobs" / job), "--local", *arguments],
        cwd=warehouse.parent,
        env=environment,
        capture_output=True,
        text=True,
        timeout=JOB_TIMEOUT_SECONDS,
    )
    assert completed.returncode == 0, completed.stderr[-4000:]
    return completed.stdout


def _read(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


# ``spark`` is requested only so that the test is skipped where Spark cannot start.
def test_phase2_then_phase3_jobs_in_local_mode(spark, tmp_path):
    warehouse, clean, results = (tmp_path / name for name in ("warehouse", "clean", "results"))
    years = "2010-2015,2024"

    ingest_output = _run_job(
        "phase2_ingest.py",
        ["--input", str(RAW_DIR), "--output", str(clean), "--years", years]
        + ["--stations", str(STATIONS_CSV), "--db", "lcd_job_test"],
        warehouse,
    )
    _run_job(
        "phase3_validate.py",
        ["--clean", str(clean), "--results", str(results)]
        + ["--fivethirtyeight", str(FIVETHIRTYEIGHT_DIR)],
        warehouse,
    )
    _run_job(
        "phase3_profile.py",
        ["--input", str(RAW_DIR), "--clean", str(clean), "--results", str(results)]
        + ["--years", years],
        warehouse,
    )

    assert f"wrote lcd_job_test.lcd_daily to {clean}/lcd_daily" in ingest_output
    assert sorted(path.name for path in results.iterdir()) == [
        "profile_missing.csv",
        "profile_ranges.csv",
        "profile_report_types.csv",
        "table_row_counts.csv",
        "validation_538.csv",
        "validation_538_daily.csv",
    ]
    assert [row["city_code"] for row in _read(results / "validation_538.csv")] == ["KCQT", "KNYC"]
    counts = {row["table"]: int(row["n_rows"]) for row in _read(results / "table_row_counts.csv")}
    assert counts["lcd_daily"] == expected_row_count({"SOD"})
    assert len(_read(results / "validation_538_daily.csv")) == 13
