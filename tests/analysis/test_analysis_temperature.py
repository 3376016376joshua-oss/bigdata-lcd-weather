"""Questions 1-3: anomalies, extreme days and the warm/cold balance."""

from __future__ import annotations

from datetime import date

import pytest
from analysis_synthetic import daily_row

WEST_CITY = "KSEA"
EAST_CITY = "KNYC"
OTHER_CITY = "KCLT"


def month_starts(first: date, n_months: int) -> list[date]:
    months = []
    for offset in range(n_months):
        total = first.year * 12 + first.month - 1 + offset
        months.append(date(total // 12, total % 12 + 1, 15))
    return months


def west_east_days() -> list[dict]:
    """One day per month from 2013-07 to 2015-07: a flat July-June year, then a
    warm-West and cold-East year, then one month of an incomplete year."""
    rows = []
    for day in month_starts(date(2013, 7, 1), 25):
        contrast_year = day >= date(2014, 7, 1)
        rows.append(daily_row(WEST_CITY, day, dep_f=5.0 if contrast_year else 1.0))
        rows.append(daily_row(EAST_CITY, day, dep_f=-5.0 if contrast_year else 1.0))
        rows.append(daily_row(OTHER_CITY, day, dep_f=0.0))
    return rows


def test_q1_monthly_anomaly_counts_extremes_at_the_threshold(analysis):
    january = [12.0, -11.0, 2.0, None]
    february = [10.0, -10.0, 9.9, -9.9]
    analysis.load_tables(
        daily=[daily_row("KNYC", date(2014, 1, i + 1), dep_f=dep) for i, dep in enumerate(january)]
        + [daily_row("KNYC", date(2014, 2, i + 1), dep_f=dep) for i, dep in enumerate(february)]
    )
    months = analysis.by_key("q1_monthly_anomaly", "city_code", "yr", "mo")
    january_row = months[("KNYC", 2014, 1)]
    assert january_row["city"] == "New York"
    assert (january_row["n_days"], january_row["anomaly_f"]) == (3, 1.0)
    assert (january_row["warm_extreme_days"], january_row["cold_extreme_days"]) == (1, 1)
    february_row = months[("KNYC", 2014, 2)]
    assert (february_row["n_days"], february_row["anomaly_f"]) == (4, 0.0)
    assert (february_row["warm_extreme_days"], february_row["cold_extreme_days"]) == (1, 1)


def test_q1_west_east_pattern_ranks_2014_15_first(analysis):
    analysis.load_tables(daily=west_east_days())
    periods = analysis.by_key("q1_west_east_pattern", "start_yr")
    assert sorted(periods) == [2013, 2014]  # the single month of 2015-16 is dropped
    reference = periods[2014]
    assert reference["period_label"] == "2014-07..2015-06"
    assert (reference["west_anomaly_f"], reference["east_anomaly_f"]) == (5.0, -5.0)
    assert reference["west_minus_east_f"] == 10.0
    assert (reference["contrast_rank"], reference["n_periods"]) == (1, 2)
    assert (reference["west_warm_rank"], reference["east_cold_rank"]) == (1, 1)
    assert (reference["west_cities"], reference["east_cities"]) == (1, 1)
    assert reference["is_2014_15"] == 1
    assert (periods[2013]["west_minus_east_f"], periods[2013]["contrast_rank"]) == (0.0, 2)
    assert periods[2013]["is_2014_15"] == 0


def test_q1_jul_jun_city_anomaly_labels_regions(analysis):
    analysis.load_tables(daily=west_east_days())
    cities = analysis.by_key("q1_jul_jun_city_anomaly", "city_code", "start_yr")
    assert len(cities) == 6
    regions = {code: cities[(code, 2014)]["region"] for code in (WEST_CITY, EAST_CITY, OTHER_CITY)}
    assert regions == {WEST_CITY: "West", EAST_CITY: "East", OTHER_CITY: "Other"}
    assert cities[(WEST_CITY, 2014)]["anomaly_f"] == 5.0
    assert cities[(WEST_CITY, 2014)]["warm_rank_in_city"] == 1
    assert cities[(EAST_CITY, 2014)]["warm_rank_in_city"] == 2
    assert cities[(EAST_CITY, 2014)]["n_days"] == 12


def test_q1_annual_anomaly_and_city_ranking(analysis):
    analysis.load_tables(daily=west_east_days())
    annual = analysis.by_key("q1_annual_anomaly", "city_code", "yr")
    assert annual[(WEST_CITY, 2014)]["anomaly_f"] == 3.0  # six months at +1, six at +5
    assert annual[(EAST_CITY, 2014)]["anomaly_f"] == -2.0
    ranks_2014 = {
        code: annual[(code, 2014)]["warm_rank_in_year"]
        for code in (WEST_CITY, OTHER_CITY, EAST_CITY)
    }
    assert ranks_2014 == {WEST_CITY: 1, OTHER_CITY: 2, EAST_CITY: 3}
    assert annual[(WEST_CITY, 2015)]["abs_anomaly_rank"] == 1

    ranking = analysis.by_key("q1_city_deviation_ranking", "city_code")
    assert ranking[WEST_CITY]["mean_abs_monthly_anomaly_f"] == 3.08  # (12 * 1 + 13 * 5) / 25
    assert ranking[WEST_CITY]["deviation_rank"] == ranking[EAST_CITY]["deviation_rank"] == 1
    assert ranking[OTHER_CITY]["deviation_rank"] == 3
    assert ranking[WEST_CITY]["warmest_yyyymm"] == 201407
    assert ranking[WEST_CITY]["warmest_month_anomaly_f"] == 5.0
    assert ranking[EAST_CITY]["coldest_yyyymm"] == 201407
    assert ranking[EAST_CITY]["mean_monthly_anomaly_f"] == -2.12  # (12 * 1 - 13 * 5) / 25


def extreme_days() -> list[dict]:
    summer = [(date(2012, 7, 1), 10.0), (date(2012, 7, 2), 15.0), (date(2012, 7, 3), 11.0)]
    winter = [(date(2012, 1, 5), -12.0)]
    spring = [(date(2012, 3, 1), 0.0), (date(2012, 3, 2), 9.9), (date(2012, 3, 3), -9.9)]
    no_departure = [(date(2012, 3, 4), None)]
    phoenix = summer + winter + spring + no_departure
    rows = [daily_row("KPHX", day, dep_f=dep) for day, dep in phoenix]
    return rows + [daily_row("KSEA", date(2012, 7, 1), dep_f=1.0)]


def test_q2_extreme_days_by_year(analysis):
    analysis.load_tables(daily=extreme_days())
    years = analysis.by_key("q2_extreme_days_by_year", "city_code", "yr")
    phoenix = years[("KPHX", 2012)]
    assert phoenix["n_days"] == 7  # the day without a departure is not counted
    assert (phoenix["warm_extreme_days"], phoenix["cold_extreme_days"]) == (3, 1)
    assert phoenix["extreme_days"] == 4
    assert phoenix["extreme_day_pct"] == pytest.approx(57.14)
    assert years[("KSEA", 2012)]["extreme_days"] == 0


def test_q2_extreme_days_by_season(analysis):
    analysis.load_tables(daily=extreme_days())
    seasons = analysis.by_key("q2_extreme_days_by_season", "city_code", "season")
    summer, winter, spring = (seasons[("KPHX", season)] for season in ("JJA", "DJF", "MAM"))
    assert (summer["warm_extreme_days"], summer["cold_extreme_days"]) == (3, 0)
    assert summer["warm_extreme_day_pct"] == 100.0
    assert (summer["share_of_city_warm_pct"], summer["share_of_city_cold_pct"]) == (100.0, 0.0)
    assert (winter["cold_extreme_days"], winter["share_of_city_cold_pct"]) == (1, 100.0)
    assert (spring["n_days"], spring["warm_extreme_days"], spring["cold_extreme_days"]) == (3, 0, 0)
    seattle = seasons[("KSEA", "JJA")]  # no extremes at all: the shares are undefined
    assert seattle["share_of_city_warm_pct"] is None
    assert seattle["share_of_city_cold_pct"] is None


def balance_days() -> list[dict]:
    """KIND gains one warm extreme per year; KJAX goes from two cold extremes to a warm one."""
    warm_cold_by_year = {
        "KIND": {2010: (0, 0), 2011: (1, 0), 2012: (2, 0), 2013: (3, 0)},
        "KJAX": {2010: (0, 2), 2011: (0, 1), 2012: (0, 0), 2013: (1, 0)},
    }
    rows = []
    for city_code, years in warm_cold_by_year.items():
        for yr, (warm, cold) in years.items():
            departures = [0.0] + [12.0] * warm + [-12.0] * cold
            rows += [
                daily_row(city_code, date(yr, 1, i + 1), dep_f=dep)
                for i, dep in enumerate(departures)
            ]
    return rows


def test_q3_balance_by_year_has_city_and_overall_rows(analysis):
    analysis.load_tables(daily=balance_days())
    balance = analysis.by_key("q3_balance_by_year", "city_code", "yr")
    assert len(balance) == 12  # two cities and ALL, four years each
    overall_2013 = balance[("ALL", 2013)]
    assert overall_2013["city"] == "All cities"
    assert (overall_2013["warm_extreme_days"], overall_2013["cold_extreme_days"]) == (4, 0)
    assert (overall_2013["warm_minus_cold"], overall_2013["warm_share"]) == (4, 1.0)
    overall_2010 = balance[("ALL", 2010)]
    assert (overall_2010["warm_minus_cold"], overall_2010["warm_share"]) == (-2, 0.0)
    assert balance[("ALL", 2011)]["warm_share"] == 0.5
    assert balance[("KIND", 2010)]["warm_share"] is None  # no extreme day that year
    assert balance[("KJAX", 2010)]["n_days"] == 3


def test_q3_balance_trend_slopes_per_decade(analysis):
    analysis.load_tables(daily=balance_days())
    trend = analysis.by_key("q3_balance_trend", "city_code")
    indianapolis = trend["KIND"]
    assert indianapolis["balance_slope_per_decade"] == pytest.approx(10.0)  # +1 day per year
    assert indianapolis["balance_trend_r"] == pytest.approx(1.0)
    assert indianapolis["n_years"] == 4
    assert (indianapolis["first_yr"], indianapolis["last_yr"]) == (2010, 2013)
    assert (indianapolis["mean_yr"], indianapolis["mean_warm_minus_cold"]) == (2011.5, 1.5)
    assert indianapolis["warm_to_cold_ratio"] is None
    overall = trend["ALL"]
    assert overall["balance_slope_per_decade"] == pytest.approx(20.0)
    assert overall["warm_slope_per_decade"] == pytest.approx(13.0)
    assert overall["cold_slope_per_decade"] == pytest.approx(-7.0)
    assert (overall["warm_extreme_days"], overall["cold_extreme_days"]) == (7, 3)
    assert overall["warm_to_cold_ratio"] == pytest.approx(2.33)


def test_q3_balance_trend_is_undefined_for_a_single_year(analysis):
    analysis.load_tables(daily=[daily_row("KIND", date(2010, 1, 1), dep_f=12.0)])
    trend = analysis.by_key("q3_balance_trend", "city_code")
    assert trend["KIND"]["balance_slope_per_decade"] is None
    assert trend["KIND"]["warm_extreme_days"] == 1
