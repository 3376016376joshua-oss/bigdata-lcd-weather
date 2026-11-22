"""Run the Phase 5-6 wrapper scripts against stand-in `spark-submit` and `hdfs` commands."""

import csv
import os
import stat
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_URI = "hdfs:///user/tester_nyu_edu/lcd/results"

FAKE_SPARK_SUBMIT = """#!/usr/bin/env bash
echo "$*" >> "$FAKE_LOG"
"""
# Lists one result directory per requested prefix and "merges" it into a small CSV.
FAKE_HDFS = """#!/usr/bin/env bash
echo "hdfs $*" >> "$FAKE_LOG"
if [[ "$2" == "-ls" ]]; then
  pattern="${@: -1}"
  echo "${pattern%\\*}table"
elif [[ "$2" == "-getmerge" ]]; then
  echo "merged from $3" > "$4"
elif [[ "$2" == "-du" ]]; then
  for path in "${@:3}"; do echo "1000  3000  $path"; done
elif [[ "$2" == "-cat" ]]; then
  for path in "${@:3}"; do printf 'header\\nrow\\nrow\\n'; done
fi
"""


@pytest.fixture
def cluster(tmp_path):
    """A PATH with fake cluster commands, plus the environment the scripts read."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, body in (("spark-submit", FAKE_SPARK_SUBMIT), ("hdfs", FAKE_HDFS)):
        command = bin_dir / name
        command.write_text(body, encoding="utf-8")
        command.chmod(command.stat().st_mode | stat.S_IXUSR)
    log = tmp_path / "commands.log"
    log.touch()
    environment = {
        **os.environ,
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "FAKE_LOG": str(log),
        "LCD_NETID": "tester",
        "LCD_RESULTS_DIR": str(tmp_path / "results"),
    }
    for inherited in ("LCD_HDFS_ROOT", "LCD_HIVE_DB", "LCD_RESULTS_URI", "SPARK_SUBMIT"):
        environment.pop(inherited, None)
    return environment, log, tmp_path / "results"


def _run(script, arguments, environment):
    return subprocess.run(
        ["bash", str(REPO_ROOT / "scripts" / script), *arguments],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def test_phase5_submits_every_job_and_fetches_the_results(cluster):
    environment, log, results = cluster

    completed = _run("run_phase5.sh", [], environment)

    assert completed.returncode == 0, completed.stderr
    submitted = [line for line in log.read_text().splitlines() if not line.startswith("hdfs")]
    assert len(submitted) == 3
    for line, job in zip(submitted, ("regression", "classification", "kmeans")):
        assert line.startswith("--master yarn --deploy-mode client --py-files ")
        assert f"jobs/phase5_{job}.py --database tester_nyu_edu" in line
        assert f"--results-dir {RESULTS_URI}" in line
        assert ("--grid full" in line) == (job != "kmeans")
    assert sorted(path.name for path in results.iterdir()) == [
        "kmeans_table.csv",
        "q7_table.csv",
        "q8_table.csv",
    ]
    assert (results / "q7_table.csv").read_text() == f"merged from {RESULTS_URI}/q7_table\n"


def test_phase5_fetch_only_downloads(cluster):
    environment, log, results = cluster

    completed = _run("run_phase5.sh", ["fetch"], environment)

    assert completed.returncode == 0, completed.stderr
    assert all(line.startswith("hdfs") for line in log.read_text().splitlines())
    assert len(list(results.iterdir())) == 3


def test_phase5_rejects_an_unknown_job(cluster):
    environment, log, _ = cluster

    completed = _run("run_phase5.sh", ["forecast"], environment)

    assert completed.returncode == 2
    assert "Unknown job 'forecast'" in completed.stderr
    assert log.read_text() == ""


def test_phase6_times_both_jobs_on_hdfs_input(cluster):
    environment, log, results = cluster

    completed = _run("run_phase6_timing.sh", ["--sizes", "1", "4"], environment)

    assert completed.returncode == 0, completed.stderr
    with open(results / "runtime_scaling.csv", newline="", encoding="utf-8") as handle:
        runs = list(csv.DictReader(handle))
    assert [(run["job"], run["start_year"], run["end_year"]) for run in runs] == [
        ("ingest", "2025", "2025"),
        ("analysis", "2025", "2025"),
        ("ingest", "2022", "2025"),
        ("analysis", "2022", "2025"),
    ]
    # The fake hdfs reports one 1000-byte file of two data rows per yearly glob.
    assert [(run["input_bytes"], run["input_rows"]) for run in runs] == [
        ("1000", "2"),
        ("1000", "2"),
        ("4000", "8"),
        ("4000", "8"),
    ]
    submitted = [line for line in log.read_text().splitlines() if not line.startswith("hdfs")]
    assert submitted[0].endswith("jobs/phase2_ingest.py --years 2025-2025")
    assert submitted[-1].endswith("jobs/phase4_analysis.py --years 2022-2025")
    assert "hdfs dfs -du hdfs:///user/tester_nyu_edu/lcd/raw/*/LCD_*_2025.csv" in log.read_text()
    assert (results / "runtime_scaling_summary.csv").exists()
