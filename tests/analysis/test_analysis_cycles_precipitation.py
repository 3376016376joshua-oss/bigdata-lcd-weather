"""Questions 4-5: temperature cycles, precipitation against normal, dry spells."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from analysis_synthetic import SPECIAL, daily_row, hourly_row, monthly_row


def test_q4_hourly_profile_uses_routine_reports_only(analysis):
    july_1, july_2 = date(2014, 7, 1), date(2014, 7, 2)
    analysis.load_tables(
        hourly=[
            hourly_row("KSEA", july_1, 0, temp_f=50.0),
            hourly_row("KSEA", july_2, 23, minute=53, temp_f=54.0),
            hourly_row("KSEA", july_1, 11, minute=53, temp_f=70.0),
            hourly_row("KSEA", july_1, 0, minute=20, report_type=SPECIAL, temp_f=90.0),
            hourly_row("KSEA", july_2, 12, temp_f=None),
            hourly_row("KSEA", date(2014, 1, 1), 12, temp_f=40.0),
        ]
    )
    profile = analysis.by_key("q4_hourly_profile", "city_code", "season", "hr")
    assert len(profile) == 3
    midnight, noon = profile[("KSEA", "JJA", 0)], profile[("KSEA", "JJA", 12)]
    assert (midnight["n_obs"], midnight["mean_temp_f"]) == (2, 52.0)
    assert (noon["n_obs"], noon["mean_temp_f"]) == (1, 70.0)
    assert (midnight["diurnal_anomaly_f"], noon["diurnal_anomaly_f"]) == (-9.0, 9.0)
    assert profile[("KSEA", "DJF", 12)]["diurnal_anomaly_f"] == 0.0


def test_q4_hourly_profile_keeps_the_hour_in_a_session_of_another_time_zone(analysis, tmp_path):
    analysis.load_tables(hourly=[hourly_row("KSEA", date(2014, 7, 1), 11, minute=53)])
    # Stored the way Phase 2 stores it: an instant written in a UTC session.
    stored = str(tmp_path / "lcd_hourly")
    analysis.spark.table("global_temp.lcd_hourly").write.orc(stored)
    analysis.spark.read.orc(stored).createOrReplaceGlobalTempView("lcd_hourly")
    session_time_zone = "spark.sql.session.timeZone"
    analysis.spark.conf.set(session_time_zone, "America/Los_Angeles")
    try:
        (row,) = analysis.rows("q4_hourly_profile")
    finally:
        analysis.spark.conf.set(session_time_zone, "UTC")
    assert row["hr"] == 12


def test_q4_monthly_climatology_and_cycle_amplitude(analysis):
    analysis.load_tables(
        daily=[
            daily_row("KSEA", date(2010, 1, 1), tavg_f=40.0, temp_range_f=10.0),
            daily_row("KSEA", date(2011, 1, 1), tavg_f=44.0, temp_range_f=10.0),
            daily_row("KSEA", date(2010, 7, 1), tavg_f=66.0, temp_range_f=20.0),
            daily_row("KSEA", date(2010, 7, 2), tavg_f=None, temp_range_f=None),
        ]
    )
    months = analysis.by_key("q4_monthly_climatology", "city_code", "mo")
    january = months[("KSEA", 1)]
    assert (january["n_days"], january["mean_tavg_f"]) == (2, 42.0)
    assert (january["mean_tmax_f"], january["mean_tmin_f"]) == (47.0, 37.0)
    assert january["mean_daily_range_f"] == 10.0
    assert months[("KSEA", 7)]["n_days"] == 1

    cycle = analysis.by_key("q4_cycle_amplitude", "city_code")["KSEA"]
    assert cycle["annual_mean_f"] == 50.0
    assert (cycle["warmest_month_mean_f"], cycle["coldest_month_mean_f"]) == (66.0, 42.0)
    assert cycle["seasonal_amplitude_f"] == 24.0
    assert cycle["mean_daily_range_f"] == pytest.approx(13.33)


def phoenix_precipitation() -> list[dict]:
    """A five-day dry spell across New Year, then shorter runs broken by a wet day, a
    missing day (January 7) and a day without a precipitation value (January 10)."""
    rows = [daily_row("KPHX", date(2011, 12, 29) + timedelta(days=i)) for i in range(5)]
    january = {
        3: {"prcp_in": 0.5},
        4: {"prcp_in": 0.0, "prcp_trace": True},
        5: {"prcp_in": 0.004},
        6: {},
        8: {},
        9: {},
        10: {"prcp_in": None},
        11: {},
        12: {"prcp_in": 0.01},
        13: {},
    }
    return rows + [
        daily_row("KPHX", date(2012, 1, day), **values) for day, values in january.items()
    ]


def seattle_precipitation() -> list[dict]:
    return [
        daily_row("KSEA", date(2012, 1, 1)),
        daily_row("KSEA", date(2012, 1, 2), prcp_in=1.25),
        daily_row("KSEA", date(2012, 1, 3)),
    ]


def test_q5_dry_spells_gaps_and_islands(analysis):
    analysis.load_tables(daily=phoenix_precipitation() + seattle_precipitation())
    spells = analysis.by_key("q5_dry_spells", "city_code", "spell_rank")
    ranked = [spells[("KPHX", rank)] for rank in range(1, 6)]
    phoenix = [(spell["start_date"], spell["end_date"], spell["length_days"]) for spell in ranked]
    assert phoenix == [
        ("2011-12-29", "2012-01-02", 5),  # continues across the year boundary
        ("2012-01-04", "2012-01-06", 3),  # trace and 0.004 in count as dry
        ("2012-01-08", "2012-01-09", 2),  # the missing January 7 starts a new spell
        ("2012-01-11", "2012-01-11", 1),  # the unknown January 10 is not a dry day
        ("2012-01-13", "2012-01-13", 1),  # 0.01 in on January 12 is a wet day
    ]
    seattle = [spells[("KSEA", rank)] for rank in (1, 2)]
    assert [(spell["start_date"], spell["length_days"]) for spell in seattle] == [
        ("2012-01-01", 1),
        ("2012-01-03", 1),
    ]
    assert ("KSEA", 3) not in spells


def test_q5_dry_spells_keeps_the_five_longest_per_city(analysis):
    rows, day = [], date(2012, 1, 1)
    for length in (1, 2, 3, 4, 5, 6, 7):
        rows += [daily_row("KPHX", day + timedelta(days=i)) for i in range(length)]
        rows.append(daily_row("KPHX", day + timedelta(days=length), prcp_in=0.2))
        day += timedelta(days=length + 1)
    analysis.load_tables(daily=rows)
    spells = analysis.rows("q5_dry_spells")
    assert [spell["length_days"] for spell in spells] == [7, 6, 5, 4, 3]


def test_q5_heaviest_rain_days(analysis):
    analysis.load_tables(daily=phoenix_precipitation() + seattle_precipitation())
    rain = analysis.by_key("q5_heaviest_rain_days", "city_code", "city_rank")
    assert len(rain) == 3  # only days with at least 0.01 in
    assert (rain[("KSEA", 1)]["obs_date"], rain[("KSEA", 1)]["overall_rank"]) == ("2012-01-02", 1)
    wettest = rain[("KPHX", 1)]
    assert (wettest["obs_date"], wettest["prcp_in"]) == ("2012-01-03", 0.5)
    assert wettest["overall_rank"] == 2
    assert (wettest["yr"], wettest["season"]) == (2012, "DJF")
    assert (rain[("KPHX", 2)]["prcp_in"], rain[("KPHX", 2)]["overall_rank"]) == (0.01, 3)


def test_q5_monthly_and_annual_precipitation_against_normal(analysis):
    analysis.load_tables(
        daily=phoenix_precipitation(),
        monthly=[monthly_row("KPHX", 2012, 1, total_prcp_in=0.51, dep_prcp_in=-0.40)],
    )
    months = analysis.by_key("q5_monthly_precip_vs_normal", "city_code", "yr", "mo")
    january = months[("KPHX", 2012, 1)]
    assert (january["n_days"], january["wet_days"]) == (11, 2)
    assert january["total_prcp_in"] == 0.51  # 0.5 + 0.004 + 0.01
    assert january["normal_prcp_in"] == 0.91  # monthly total minus its departure
    assert january["dep_prcp_in"] == pytest.approx(-0.4)
    assert (january["period_mean_prcp_in"], january["dep_vs_period_mean_in"]) == (0.51, 0.0)
    december = months[("KPHX", 2011, 12)]  # no monthly summary: no station normal
    assert (december["total_prcp_in"], december["normal_prcp_in"]) == (0.0, None)
    assert december["dep_prcp_in"] is None

    years = analysis.by_key("q5_annual_precip_vs_normal", "city_code", "yr")
    wet_year, dry_year = years[("KPHX", 2012)], years[("KPHX", 2011)]
    assert (wet_year["n_months"], wet_year["normal_prcp_in"]) == (1, 0.91)
    assert wet_year["pct_of_normal"] == pytest.approx(56.5)
    assert wet_year["pct_of_period_mean"] == pytest.approx(200.0)
    assert (dry_year["dryness_rank_in_city"], wet_year["dryness_rank_in_city"]) == (1, 2)
    assert (dry_year["normal_prcp_in"], dry_year["pct_of_normal"]) == (None, None)


def test_q5_california_drought_compares_2012_2016_with_other_years(analysis):
    def year_of_rain(yr: int, january_1_rain: float, dry_days_after: int) -> list[dict]:
        rows = [daily_row("KCQT", date(yr, 1, 1), prcp_in=january_1_rain)]
        return rows + [daily_row("KCQT", date(yr, 1, 2 + i)) for i in range(dry_days_after)]

    analysis.load_tables(
        daily=year_of_rain(2011, 10.0, 0)
        + year_of_rain(2012, 2.0, 4)
        + year_of_rain(2013, 4.0, 0)
        + year_of_rain(2017, 20.0, 2)
        + [daily_row("KPHX", date(2012, 1, 1), prcp_in=9.0)]
    )
    periods = analysis.by_key("q5_california_drought", "period_label")
    drought, other = periods["drought 2012-2016"], periods["other years"]
    assert (drought["n_years"], drought["mean_annual_prcp_in"]) == (2, 3.0)
    assert (drought["driest_year_prcp_in"], drought["mean_wet_days_per_year"]) == (2.0, 1.0)
    assert drought["longest_dry_spell_days"] == 4
    assert (other["n_years"], other["mean_annual_prcp_in"]) == (2, 15.0)
    assert other["longest_dry_spell_days"] == 2
