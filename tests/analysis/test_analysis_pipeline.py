"""End to end: every query on a synthetic data set, CSV export, then every figure."""

from __future__ import annotations

import importlib
import random
from datetime import date, timedelta
from functools import partial

import pytest
from analysis_synthetic import SPECIAL, daily_row, hourly_row, monthly_row

from lcdweather.analysis.export import write_cluster_csv, write_result
from lcdweather.analysis.runner import run_analysis

CITY_CODES = ("KCQT", "KNYC", "KPHL", "KSEA")
FIRST_DAY = date(2011, 7, 1)
LAST_DAY = date(2014, 6, 30)
HOURLY_FIRST_DAY = date(2013, 1, 1)
HOURLY_DAYS = 45
RANDOM_SEED = 2014
EXPECTED_FIGURES = {
    "q1_anomaly": ["q1_anomaly_heatmap", "q1_west_east_pattern"],
    "q2_extremes": ["q2_extreme_days_by_year", "q2_extreme_days_by_season"],
    "q3_balance": ["q3_balance_by_year", "q3_balance_trend_by_city"],
    "q4_cycles": ["q4_hourly_cycle", "q4_monthly_climatology"],
    "q5_precipitation": [
        "q5_precip_actual_vs_normal",
        "q5_longest_dry_spells",
        "q5_heaviest_rain_days",
    ],
    "q6_volatility": [
        "q6_city_volatility",
        "q6_special_reports_wet_vs_dry",
        "q6_special_reports_around_storms",
    ],
}


def synthetic_daily(rng: random.Random) -> list[dict]:
    rows = []
    for city_code in CITY_CODES:
        day = FIRST_DAY
        while day <= LAST_DAY:
            wet = rng.random() < 0.3
            rows.append(
                daily_row(
                    city_code,
                    day,
                    dep_f=rng.gauss(0, 7),
                    tavg_f=55 + 20 * (1 if 4 <= day.month <= 9 else -1) + rng.gauss(0, 5),
                    temp_range_f=rng.uniform(8, 30),
                    prcp_in=round(rng.expovariate(2), 2) + 0.01 if wet else 0.0,
                )
            )
            day += timedelta(days=1)
    return rows


def synthetic_hourly(rng: random.Random, daily: list[dict]) -> list[dict]:
    wet_days = {(row["city_code"], row["obs_date"]) for row in daily if row["prcp_in"] > 0}
    rows = []
    for city_code in CITY_CODES:
        for offset in range(HOURLY_DAYS):
            day = HOURLY_FIRST_DAY + timedelta(days=offset)
            for hour in range(24):
                temp_f = 50 - 10 * abs(hour - 15) / 15 + rng.gauss(0, 2)
                pressure = 1010 + rng.gauss(0, 3)
                rows.append(
                    hourly_row(city_code, day, hour, temp_f=temp_f, station_pressure_hpa=pressure)
                )
            specials = rng.randint(1, 5) if (city_code, day) in wet_days else rng.randint(0, 1)
            rows += [
                hourly_row(city_code, day, hour, minute=30, report_type=SPECIAL)
                for hour in range(specials)
            ]
    return rows


def synthetic_monthly(daily: list[dict]) -> list[dict]:
    totals: dict = {}
    for row in daily:
        key = (row["city_code"], row["yr"], row["month"])
        totals[key] = totals.get(key, 0.0) + row["prcp_in"]
    return [
        monthly_row(city_code, yr, month, total_prcp_in=total, dep_prcp_in=total - 3.0)
        for (city_code, yr, month), total in totals.items()
    ]


@pytest.fixture()
def results_dir(analysis, tmp_path):
    """All Phase 4 results for the synthetic data set, as CSV files."""
    rng = random.Random(RANDOM_SEED)
    daily = synthetic_daily(rng)
    analysis.load_tables(
        daily=daily, hourly=synthetic_hourly(rng, daily), monthly=synthetic_monthly(daily)
    )
    target = tmp_path / "results"
    written = run_analysis(
        analysis.spark,
        analysis.queries.values(),
        "global_temp",
        partial(write_result, results_dir=str(target)),
    )
    assert sorted(written) == sorted(analysis.queries)
    return target


def test_pipeline_exports_one_csv_per_query_and_draws_every_figure(
    analysis, results_dir, viz_dir, tmp_path, monkeypatch
):
    pandas = pytest.importorskip("pandas")
    for name in analysis.queries:
        result = pandas.read_csv(results_dir / f"{name}.csv")
        assert len(result) > 0, name
    pattern = pandas.read_csv(results_dir / "q1_west_east_pattern.csv")
    assert list(pattern["start_yr"]) == [2011, 2012, 2013]

    pytest.importorskip("matplotlib")
    pytest.importorskip("seaborn")
    pytest.importorskip("plotly")
    monkeypatch.syspath_prepend(str(viz_dir))
    figures_dir = tmp_path / "figures"
    arguments = ["--results-dir", str(results_dir), "--figures-dir", str(figures_dir)]
    for script, figures in EXPECTED_FIGURES.items():
        importlib.import_module(script).main(arguments)
        for figure in figures:
            for extension in ("png", "html"):
                written = figures_dir / f"{figure}.{extension}"
                assert written.is_file() and written.stat().st_size > 0, written.name


def test_write_cluster_csv_writes_one_part_file_with_header(analysis, tmp_path):
    analysis.load_tables(daily=[daily_row("KNYC", date(2014, 1, 1), dep_f=12.0)])
    target = write_cluster_csv(analysis.frame("q1_monthly_anomaly"), str(tmp_path / "q1"))
    parts = sorted((tmp_path / "q1").glob("part-*.csv"))
    assert target == str(tmp_path / "q1")
    assert len(parts) == 1
    header, row = parts[0].read_text(encoding="utf-8").splitlines()
    assert header.split(",")[:4] == ["city_code", "city", "yr", "mo"]
    assert row.split(",")[:4] == ["KNYC", "New York", "2014", "1"]


def test_write_result_accepts_a_file_uri(analysis, tmp_path):
    analysis.load_tables(daily=[daily_row("KNYC", date(2014, 1, 1), dep_f=12.0)])
    written = write_result(analysis.frame("q1_monthly_anomaly"), "q1", f"file://{tmp_path}")
    assert written == str(tmp_path / "q1.csv")
    assert (tmp_path / "q1.csv").read_text(encoding="utf-8").startswith("city_code,city,yr,mo")
