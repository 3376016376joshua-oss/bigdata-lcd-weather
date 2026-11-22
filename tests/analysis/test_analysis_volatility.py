"""Question 6: temperature volatility, humidity and special weather reports."""

from __future__ import annotations

import statistics
from datetime import date

import pytest
from analysis_synthetic import ROUTINE, SPECIAL, daily_row, hourly_row


def pearson(xs: list, ys: list) -> float:
    mean_x, mean_y = statistics.fmean(xs), statistics.fmean(ys)
    covariance = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    spread_x = sum((x - mean_x) ** 2 for x in xs)
    spread_y = sum((y - mean_y) ** 2 for y in ys)
    return covariance / (spread_x * spread_y) ** 0.5


def volatility_tables() -> dict:
    chicago = {1: (50.0, 10.0), 2: (52.0, 20.0), 3: (50.0, 30.0), 4: (54.0, 20.0), 6: (80.0, 20.0)}
    daily = [
        daily_row("KMDW", date(2014, 1, day), tavg_f=tavg, temp_range_f=temp_range)
        for day, (tavg, temp_range) in chicago.items()
    ]
    daily += [daily_row("KPHX", date(2014, 1, day), tavg_f=70.0) for day in (1, 2, 3)]
    hourly = [
        hourly_row("KMDW", date(2014, 1, 1), 0, rh_pct=40.0, dewpt_f=30.0),
        hourly_row("KMDW", date(2014, 1, 1), 1, rh_pct=60.0, dewpt_f=40.0),
        hourly_row("KMDW", date(2014, 1, 1), 1, minute=30, report_type=SPECIAL, rh_pct=100.0),
    ]
    return {"daily": daily, "hourly": hourly}


def test_q6_city_volatility_uses_consecutive_days_only(analysis):
    analysis.load_tables(**volatility_tables())
    cities = analysis.by_key("q6_city_volatility", "city_code")
    chicago, phoenix = cities["KMDW"], cities["KPHX"]
    # Changes +2, -2, +4; the jump to January 6 follows a missing day and is ignored.
    assert (chicago["n_days"], chicago["n_changes"]) == (5, 3)
    assert chicago["tavg_change_sd_f"] == pytest.approx(statistics.stdev([2, -2, 4]), abs=0.005)
    assert chicago["mean_abs_tavg_change_f"] == pytest.approx(2.67)
    assert chicago["mean_daily_range_f"] == 20.0
    assert (chicago["mean_rh_pct"], chicago["mean_dewpt_f"]) == (50.0, 35.0)  # FM-15 only
    assert (chicago["volatility_rank"], phoenix["volatility_rank"]) == (1, 2)
    assert (phoenix["tavg_change_sd_f"], phoenix["mean_rh_pct"]) == (0.0, None)


def test_q6_seasonal_volatility(analysis):
    analysis.load_tables(**volatility_tables())
    seasons = analysis.by_key("q6_seasonal_volatility", "city_code", "season")
    assert sorted(seasons) == [("KMDW", "DJF"), ("KPHX", "DJF")]
    winter = seasons[("KMDW", "DJF")]
    assert winter["tavg_change_sd_f"] == pytest.approx(3.06)
    assert (winter["mean_daily_range_f"], winter["mean_rh_pct"]) == (20.0, 50.0)


SPECIALS_BY_DAY = [0, 1, 3, 1]
PRCP_BY_DAY = [0.0, 0.0, 2.0, 0.5]
PRESSURE_RANGE_BY_DAY = [2.0, 0.0, 10.0, 4.0]


def special_report_tables() -> dict:
    """Four Houston days with hourly reports (two dry, two wet), one dry day without
    hourly reports and one day without a precipitation value."""
    march = [date(2014, 3, day) for day in range(1, 7)]
    daily = [daily_row("KHOU", day, prcp_in=prcp) for day, prcp in zip(march, PRCP_BY_DAY)]
    daily += [daily_row("KHOU", march[4]), daily_row("KHOU", march[5], prcp_in=None)]
    reports = [(march[0], ROUTINE, 1000.0), (march[0], ROUTINE, 1002.0)]
    reports += [(march[1], ROUTINE, 1001.0), (march[1], SPECIAL, 1001.0)]
    reports += [(march[2], ROUTINE, 1000.0), (march[2], SPECIAL, 990.0)]
    reports += [(march[2], SPECIAL, 995.0), (march[2], SPECIAL, 992.0)]
    reports += [(march[3], ROUTINE, 1000.0), (march[3], SPECIAL, 996.0)]
    reports += [(march[5], SPECIAL, 1000.0)]
    hourly = [
        hourly_row("KHOU", day, hour, report_type=report_type, station_pressure_hpa=pressure)
        for hour, (day, report_type, pressure) in enumerate(reports)
    ]
    return {"daily": daily, "hourly": hourly}


def test_q6_special_reports_on_wet_and_dry_days(analysis):
    analysis.load_tables(**special_report_tables())
    day_types = analysis.by_key("q6_special_reports_by_day_type", "city_code", "day_type")
    dry, wet = day_types[("KHOU", "dry")], day_types[("KHOU", "wet")]
    assert (dry["n_days"], dry["special_reports"]) == (2, 1)
    assert (dry["mean_special_reports_per_day"], dry["pct_days_with_special"]) == (0.5, 50.0)
    assert (dry["special_share_of_reports_pct"], dry["mean_pressure_range_hpa"]) == (25.0, 1.0)
    assert (wet["n_days"], wet["special_reports"]) == (2, 4)
    assert (wet["mean_special_reports_per_day"], wet["pct_days_with_special"]) == (2.0, 100.0)
    assert wet["special_share_of_reports_pct"] == pytest.approx(66.7)
    assert wet["mean_pressure_range_hpa"] == 7.0


def test_q6_special_reports_correlation(analysis):
    analysis.load_tables(**special_report_tables())
    houston = analysis.by_key("q6_special_reports_correlation", "city_code")["KHOU"]
    assert (houston["n_days"], houston["routine_reports"], houston["special_reports"]) == (4, 5, 5)
    assert houston["mean_special_reports_per_day"] == 1.25
    assert houston["corr_special_vs_prcp"] == pytest.approx(
        pearson(SPECIALS_BY_DAY, PRCP_BY_DAY), abs=0.001
    )
    assert houston["corr_special_vs_pressure_range"] == pytest.approx(
        pearson(SPECIALS_BY_DAY, PRESSURE_RANGE_BY_DAY), abs=0.001
    )
    assert houston["mean_pressure_range_hpa"] == 4.0


def test_q6_special_reports_around_storms(analysis):
    analysis.load_tables(**special_report_tables())
    offsets = analysis.by_key("q6_special_reports_around_storms", "city_code", "day_offset")
    # Storm days are March 3 (2.0 in) and March 4 (0.5 in); each contributes its neighbours.
    summary = {
        offset: (row["n_days"], row["mean_special_reports"]) for (_, offset), row in offsets.items()
    }
    assert summary == {-3: (1, 0.0), -2: (2, 0.5), -1: (2, 2.0), 0: (2, 2.0), 1: (1, 1.0)}
    assert offsets[("KHOU", 0)]["mean_prcp_in"] == 1.25
    assert {row["city_mean_special_reports"] for row in offsets.values()} == {1.25}
