"""Tiny synthetic rows shaped like the cleaned ``lcd_daily``, ``lcd_hourly`` and
``lcd_monthly`` tables (the shared column contract), for the analysis tests."""

from __future__ import annotations

from datetime import date

DAILY_SCHEMA = (
    "city_code string, city string, obs_date date, tmax_f double, tmin_f double, "
    "tavg_f double, dep_f double, prcp_in double, prcp_trace boolean, snow_in double, "
    "snow_depth_in double, hdd double, cdd double, peak_wind_mph double, "
    "sustained_wind_mph double, sunrise string, sunset string, month int, season string, "
    "doy int, temp_range_f double, is_warm_extreme boolean, is_cold_extreme boolean, "
    "is_dry_day boolean, is_wet_day boolean, is_primary_station boolean, station string, yr int"
)
# obs_ts and obs_date are given as text and cast by Spark, so the hour of a report does
# not depend on the time zone of the machine running the tests.
HOURLY_TEXT_SCHEMA = (
    "city_code string, city string, obs_ts string, obs_date string, report_type string, "
    "temp_f double, dewpt_f double, wetbulb_f double, rh_pct double, wind_speed_mph double, "
    "wind_gust_mph double, wind_dir_deg double, station_pressure_hpa double, "
    "sea_level_pressure_hpa double, pressure_change_hpa double, visibility_mi double, "
    "sky_conditions string, sky_cover_okta int, precip_in double, hour int, month int, "
    "season string, is_special boolean, is_primary_station boolean, station string, yr int"
)
MONTHLY_SCHEMA = (
    "city_code string, city string, month int, mean_tmax_f double, mean_tmin_f double, "
    "mean_tavg_f double, dep_tavg_f double, total_prcp_in double, dep_prcp_in double, "
    "total_snow_in double, days_max_ge_90 int, days_min_le_32 int, hdd double, cdd double, "
    "normal_tavg_f double, is_primary_station boolean, station string, yr int"
)

CITIES = {
    "KCLT": ("Charlotte", "USW00013881"),
    "KCQT": ("Los Angeles", "USW00093134"),
    "KHOU": ("Houston", "USW00012918"),
    "KIND": ("Indianapolis", "USW00093819"),
    "KJAX": ("Jacksonville", "USW00013889"),
    "KMDW": ("Chicago", "USW00014819"),
    "KNYC": ("New York", "USW00094728"),
    "KPHL": ("Philadelphia", "USW00013739"),
    "KPHX": ("Phoenix", "USW00023183"),
    "KSEA": ("Seattle", "USW00024233"),
}
SEASON_MONTHS = {"DJF": (12, 1, 2), "MAM": (3, 4, 5), "JJA": (6, 7, 8), "SON": (9, 10, 11)}
SEASON_BY_MONTH = {month: season for season, months in SEASON_MONTHS.items() for month in months}
EXTREME_DEPARTURE_F = 10.0
WET_DAY_IN = 0.01
ROUTINE = "FM-15"
SPECIAL = "FM-16"


def daily_row(
    city_code: str,
    day: date,
    *,
    dep_f: float | None = 0.0,
    tavg_f: float | None = 60.0,
    temp_range_f: float | None = 20.0,
    prcp_in: float | None = 0.0,
    prcp_trace: bool = False,
) -> dict:
    city, station = CITIES[city_code]
    half_range = None if temp_range_f is None else temp_range_f / 2
    known_temps = tavg_f is not None and half_range is not None
    return {
        "city_code": city_code,
        "city": city,
        "obs_date": day,
        "tmax_f": tavg_f + half_range if known_temps else None,
        "tmin_f": tavg_f - half_range if known_temps else None,
        "tavg_f": tavg_f,
        "dep_f": dep_f,
        "prcp_in": prcp_in,
        "prcp_trace": prcp_trace,
        "month": day.month,
        "season": SEASON_BY_MONTH[day.month],
        "doy": day.timetuple().tm_yday,
        "temp_range_f": temp_range_f,
        "is_warm_extreme": None if dep_f is None else dep_f >= EXTREME_DEPARTURE_F,
        "is_cold_extreme": None if dep_f is None else dep_f <= -EXTREME_DEPARTURE_F,
        "is_dry_day": None if prcp_in is None else prcp_in < WET_DAY_IN,
        "is_wet_day": None if prcp_in is None else prcp_in >= WET_DAY_IN,
        "is_primary_station": True,
        "station": station,
        "yr": day.year,
    }


def hourly_row(
    city_code: str,
    day: date,
    hour: int,
    *,
    minute: int = 0,
    report_type: str = ROUTINE,
    temp_f: float | None = 60.0,
    rh_pct: float | None = 50.0,
    dewpt_f: float | None = 40.0,
    station_pressure_hpa: float | None = 1000.0,
) -> dict:
    city, station = CITIES[city_code]
    return {
        "city_code": city_code,
        "city": city,
        "obs_ts": f"{day.isoformat()} {hour:02d}:{minute:02d}:00",
        "obs_date": day.isoformat(),
        "report_type": report_type,
        "temp_f": temp_f,
        "dewpt_f": dewpt_f,
        "rh_pct": rh_pct,
        "station_pressure_hpa": station_pressure_hpa,
        "hour": hour,
        "month": day.month,
        "season": SEASON_BY_MONTH[day.month],
        "is_special": report_type == SPECIAL,
        "is_primary_station": True,
        "station": station,
        "yr": day.year,
    }


def monthly_row(
    city_code: str, yr: int, month: int, *, total_prcp_in: float, dep_prcp_in: float | None
) -> dict:
    city, station = CITIES[city_code]
    return {
        "city_code": city_code,
        "city": city,
        "month": month,
        "total_prcp_in": total_prcp_in,
        "dep_prcp_in": dep_prcp_in,
        "is_primary_station": True,
        "station": station,
        "yr": yr,
    }
