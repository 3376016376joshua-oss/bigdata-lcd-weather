import csv
import sys

import pytest

from lcdweather.timing.cli import main
from lcdweather.timing.driver import Experiment, any_failed, run_experiment
from lcdweather.timing.inputs import InputStats
from lcdweather.timing.plan import YearWindow, year_windows
from lcdweather.timing.runner import TimedRun, build_command, run_timed
from lcdweather.timing.summary import loglog_slope, summarize


def test_build_command_substitutes_spark_submit_and_years():
    command = build_command(
        "{spark_submit} jobs/phase2_ingest.py --years {start}-{end}",
        YearWindow(2022, 2025),
        "spark-submit --master yarn --conf 'spark.app.name=lcd timing'",
    )

    assert command == [
        "spark-submit",
        "--master",
        "yarn",
        "--conf",
        "spark.app.name=lcd timing",
        "jobs/phase2_ingest.py",
        "--years",
        "2022-2025",
    ]


def test_run_timed_reports_elapsed_clock_time_and_exit_code():
    ticks = iter([100.0, 142.5])

    timed = run_timed(["job"], execute=lambda command: 3, clock=lambda: next(ticks))

    assert timed == TimedRun(wall_seconds=42.5, exit_code=3)


def test_run_timed_executes_a_real_command():
    timed = run_timed([sys.executable, "-c", "raise SystemExit(4)"])

    assert timed.exit_code == 4
    assert timed.wall_seconds > 0


def test_experiment_records_every_window_job_and_repeat():
    experiment = Experiment(
        windows=year_windows(sizes=[1, 4]),
        templates={
            "ingest": "{spark_submit} ingest {start}-{end}",
            "analysis": "{spark_submit} analysis {n_years}",
        },
        spark_submit="submit",
        repeats=2,
    )
    executed = []

    def run(command):
        executed.append(list(command))
        return TimedRun(wall_seconds=float(len(executed)), exit_code=0)

    records = run_experiment(
        experiment,
        measure=lambda window: InputStats(
            files=window.n_years, bytes=window.n_years * 100, rows=None
        ),
        run=run,
    )

    assert len(records) == 2 * 2 * 2
    assert executed[0] == ["submit", "ingest", "2025-2025"]
    assert executed[-1] == ["submit", "analysis", "4"]
    first = records[0]
    assert (first["job"], first["n_years"], first["repeat"]) == ("ingest", 1, 1)
    assert (first["input_files"], first["input_bytes"], first["input_rows"]) == (
        1,
        100,
        None,
    )
    assert first["command"] == "submit ingest 2025-2025"
    assert not any_failed(records)


def test_failed_runs_are_recorded_and_flagged():
    experiment = Experiment(year_windows(sizes=[1]), {"ingest": "{spark_submit} x"}, "submit")

    records = run_experiment(
        experiment,
        measure=lambda window: InputStats(1, 10, 5),
        run=lambda command: TimedRun(1.0, 2),
    )

    assert records[0]["exit_code"] == 2
    assert any_failed(records)


def test_loglog_slope_recovers_linear_and_quadratic_growth():
    assert loglog_slope([(1, 3), (4, 12), (16, 48)]) == pytest.approx(1.0)
    assert loglog_slope([(1, 2), (2, 8), (4, 32)]) == pytest.approx(2.0)
    assert loglog_slope([(1, 2)]) is None


def test_summary_uses_medians_of_successful_runs():
    def record(n_years, seconds, exit_code=0):
        return {
            "job": "ingest",
            "n_years": n_years,
            "input_bytes": n_years * 1024**3,
            "wall_seconds": seconds,
            "exit_code": exit_code,
        }

    rows = summarize(
        [record(1, 10), record(1, 30), record(1, 20), record(4, 80), record(4, 999, 1)]
    )

    assert [row["n_years"] for row in rows] == [1, 4]
    assert rows[0]["median_wall_seconds"] == 20
    assert rows[1]["median_wall_seconds"] == 80
    assert rows[1]["input_ratio"] == pytest.approx(4.0)
    assert rows[1]["time_ratio"] == pytest.approx(4.0)
    assert rows[1]["seconds_per_gb"] == pytest.approx(20.0)
    assert rows[0]["loglog_slope"] == pytest.approx(1.0)


def test_cli_times_commands_and_writes_both_csvs(tmp_path):
    raw = tmp_path / "raw" / "USW00000001"
    raw.mkdir(parents=True)
    for year in (2024, 2025):
        (raw / f"LCD_USW00000001_{year}.csv").write_text("h\nrow\n", encoding="utf-8")
    output = tmp_path / "out" / "runtime_scaling.csv"
    summary = tmp_path / "out" / "runtime_scaling_summary.csv"

    exit_code = main(
        [
            "--sizes",
            "1",
            "2",
            "--first-year",
            "2024",
            "--raw-root",
            str(tmp_path / "raw"),
            "--spark-submit",
            sys.executable,
            "--ingest-command",
            "{spark_submit} -c pass",
            "--analysis-command",
            "{spark_submit} -c 'raise SystemExit(0)'",
            "--output",
            str(output),
            "--summary-output",
            str(summary),
        ]
    )

    assert exit_code == 0
    with open(output, newline="", encoding="utf-8") as handle:
        runs = list(csv.DictReader(handle))
    assert [(run["job"], run["n_years"]) for run in runs] == [
        ("ingest", "1"),
        ("analysis", "1"),
        ("ingest", "2"),
        ("analysis", "2"),
    ]
    assert [run["input_rows"] for run in runs] == ["1", "1", "2", "2"]
    assert all(run["exit_code"] == "0" for run in runs)
    with open(summary, newline="", encoding="utf-8") as handle:
        assert len(list(csv.DictReader(handle))) == 4


def test_cli_exits_nonzero_when_a_job_fails(tmp_path):
    exit_code = main(
        [
            "--sizes",
            "1",
            "--jobs",
            "ingest",
            "--raw-root",
            str(tmp_path),
            "--spark-submit",
            sys.executable,
            "--ingest-command",
            "{spark_submit} -c 'raise SystemExit(5)'",
            "--output",
            str(tmp_path / "runs.csv"),
            "--summary-output",
            str(tmp_path / "summary.csv"),
        ]
    )

    assert exit_code == 1
