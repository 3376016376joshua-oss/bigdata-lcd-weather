"""Question 5 figure data: which baseline stands for the normal of a calendar month."""

from __future__ import annotations

import importlib

import pytest

pandas = pytest.importorskip("pandas")
pytest.importorskip("matplotlib")
pytest.importorskip("seaborn")
pytest.importorskip("plotly")


def monthly_result_row(yr: int, mo: int, total: float, normal: float | None, mean: float) -> dict:
    return {
        "city": "Seattle",
        "yr": yr,
        "mo": mo,
        "total_prcp_in": total,
        "normal_prcp_in": normal,
        "period_mean_prcp_in": mean,
    }


def test_only_a_month_without_any_normal_falls_back_to_the_period_mean(viz_dir, monkeypatch):
    monkeypatch.syspath_prepend(str(viz_dir))
    calendar_month_means = importlib.import_module("q5_precipitation").calendar_month_means
    monthly = pandas.DataFrame(
        [
            monthly_result_row(2014, 1, total=4.0, normal=5.5, mean=5.0),
            monthly_result_row(2015, 1, total=6.0, normal=None, mean=5.0),
            monthly_result_row(2014, 2, total=1.0, normal=None, mean=2.0),
            monthly_result_row(2015, 2, total=3.0, normal=None, mean=2.0),
        ]
    )

    means = calendar_month_means(monthly).set_index("mo")

    assert list(means.columns) == ["city", "actual_in", "normal_in"]
    assert (means.loc[1, "actual_in"], means.loc[1, "normal_in"]) == (5.0, 5.5)
    assert (means.loc[2, "actual_in"], means.loc[2, "normal_in"]) == (2.0, 2.0)
