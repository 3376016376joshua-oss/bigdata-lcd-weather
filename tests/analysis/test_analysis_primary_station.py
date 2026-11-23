"""Los Angeles 2024-2025: both stations are loaded, only the primary one is analysed."""

from __future__ import annotations

from datetime import date

from analysis_synthetic import daily_row, hourly_row, monthly_row

LOS_ANGELES = "KCQT"
AIRPORT_STATION = "USW00023174"
SHARED_DAY = date(2024, 1, 15)


def airport(row: dict) -> dict:
    """The row as reported by the airport, the primary Los Angeles station from 2024."""
    return {**row, "station": AIRPORT_STATION}


def downtown(row: dict) -> dict:
    """The row as reported by Downtown/USC, which is not primary from 2024."""
    return {**row, "is_primary_station": False}


def test_los_angeles_2024_uses_only_the_primary_airport_station(analysis):
    analysis.load_tables(
        daily=[
            airport(daily_row(LOS_ANGELES, SHARED_DAY, dep_f=12.0, tavg_f=70.0, prcp_in=0.5)),
            downtown(daily_row(LOS_ANGELES, SHARED_DAY, dep_f=14.0, tavg_f=80.0, prcp_in=2.0)),
        ],
        hourly=[
            airport(hourly_row(LOS_ANGELES, SHARED_DAY, 12, temp_f=70.0)),
            downtown(hourly_row(LOS_ANGELES, SHARED_DAY, 12, temp_f=80.0)),
        ],
        monthly=[
            airport(monthly_row(LOS_ANGELES, 2024, 1, total_prcp_in=0.5, dep_prcp_in=-2.5)),
            downtown(monthly_row(LOS_ANGELES, 2024, 1, total_prcp_in=2.0, dep_prcp_in=-4.0)),
        ],
    )
    extremes = analysis.by_key("q2_extreme_days_by_year", "city_code", "yr")[(LOS_ANGELES, 2024)]
    assert (extremes["n_days"], extremes["warm_extreme_days"]) == (1, 1)

    anomaly = analysis.by_key("q1_monthly_anomaly", "city_code", "yr", "mo")[(LOS_ANGELES, 2024, 1)]
    assert (anomaly["n_days"], anomaly["anomaly_f"]) == (1, 12.0)

    precipitation = analysis.by_key("q5_monthly_precip_vs_normal", "city_code", "yr", "mo")
    january = precipitation[(LOS_ANGELES, 2024, 1)]
    assert (january["n_days"], january["total_prcp_in"]) == (1, 0.5)
    assert january["normal_prcp_in"] == 3.0  # the airport normal, not the downtown 6.0

    noon = analysis.by_key("q4_hourly_profile", "city_code", "season", "hr")[
        (LOS_ANGELES, "DJF", 12)
    ]
    assert (noon["n_obs"], noon["mean_temp_f"]) == (1, 70.0)

    storm_days = analysis.by_key("q6_special_reports_correlation", "city_code")[LOS_ANGELES]
    assert (storm_days["n_days"], storm_days["routine_reports"]) == (1, 1)
