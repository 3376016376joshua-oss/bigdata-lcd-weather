"""Pure-Python generator of small, plausible hourly and daily weather rows."""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta

ROUTINE = "FM-15"
SPECIAL = "FM-16"
ANOMALY_PERSISTENCE = 0.7
ANOMALY_NOISE_F = 4.0
MEAN_DAILY_RANGE_F = 14.0
WARMEST_HOUR = 15
COLDEST_DAY_OF_YEAR = 15
BASE_PRESSURE_HPA = 1013.0
PRESSURE_FALL_BEFORE_RAIN_HPA = -7.0
PRESSURE_RISE_WHEN_FAIR_HPA = 1.5
HUMID_RH_PCT = 86.0
DRY_RH_PCT = 52.0
OVERCAST_OKTA = 7
FAIR_OKTA = 2
RH_TO_DEWPOINT_DEPRESSION_F = 0.36
PRECURSOR_RELIABILITY = 0.9


@dataclass(frozen=True)
class SyntheticCity:
    code: str
    name: str
    mean_temp_f: float
    seasonal_amplitude_f: float
    wet_probability: float


@dataclass(frozen=True)
class SyntheticSpec:
    cities: Sequence[SyntheticCity]
    years: Sequence[int]
    days_of_year: Sequence[int]
    hours: Sequence[int]
    seed: int = 7


def _seasonal_mean(city: SyntheticCity, day_of_year: int) -> float:
    angle = 2.0 * math.pi * (day_of_year - COLDEST_DAY_OF_YEAR) / 365.25
    return city.mean_temp_f - city.seasonal_amplitude_f * math.cos(angle)


def _routine_readings(hour: int, n_hours: int, state: dict, front_coming: bool, rng) -> tuple:
    """Temperature to precipitation columns of one routine hourly report."""
    wet_signal = state["wet"] or front_coming
    trend = PRESSURE_FALL_BEFORE_RAIN_HPA if front_coming else PRESSURE_RISE_WHEN_FAIR_HPA
    cycle = math.cos(2.0 * math.pi * (hour - WARMEST_HOUR) / 24.0)
    temp = state["tavg"] + state["range"] / 2.0 * cycle + rng.gauss(0.0, 0.5)
    humidity = (HUMID_RH_PCT if wet_signal else DRY_RH_PCT) + rng.gauss(0.0, 4.0)
    humidity = max(5.0, min(100.0, humidity))
    dewpoint = temp - (100.0 - humidity) * RH_TO_DEWPOINT_DEPRESSION_F
    pressure = BASE_PRESSURE_HPA + trend * hour / 24.0 + rng.gauss(0.0, 0.2)
    wind = max(0.0, 6.0 + (5.0 if state["wet"] else 0.0) + rng.gauss(0.0, 1.5))
    gust = wind + 8.0 if state["wet"] else None
    sky = OVERCAST_OKTA if wet_signal else FAIR_OKTA
    precip = state["prcp"] / n_hours
    return (temp, dewpoint, humidity, wind, gust, pressure, sky, precip)


def _hourly_rows(city, day, hours, state, rng) -> list[tuple]:
    """Routine reports for one day, plus one special report on wet days."""
    # Precursors are right most of the time, not always, so models cannot be perfect.
    front_coming = state["wet_tomorrow"] == (rng.random() < PRECURSOR_RELIABILITY)
    identity = (city.code, city.name)
    rows = []
    for hour in hours:
        stamp = f"{day.isoformat()} {hour:02d}:00:00"
        readings = _routine_readings(hour, len(hours), state, front_coming, rng)
        rows.append((*identity, stamp, day.isoformat(), ROUTINE, *readings, False))
    if state["wet"]:
        stamp = f"{day.isoformat()} {hours[0]:02d}:30:00"
        no_readings = (None, None, None, None, None, None, OVERCAST_OKTA, None)
        rows.append((*identity, stamp, day.isoformat(), SPECIAL, *no_readings, True))
    return rows


def _city_rows(city: SyntheticCity, spec: SyntheticSpec, rng) -> tuple[list[tuple], list[tuple]]:
    days = [
        date(year, 1, 1) + timedelta(days=day_of_year - 1)
        for year in spec.years
        for day_of_year in spec.days_of_year
    ]
    wet_flags = [rng.random() < city.wet_probability for _ in range(len(days) + 1)]
    hourly: list[tuple] = []
    daily: list[tuple] = []
    anomaly = 0.0
    for index, day in enumerate(days):
        anomaly = ANOMALY_PERSISTENCE * anomaly + rng.gauss(0.0, ANOMALY_NOISE_F)
        daily_range = MEAN_DAILY_RANGE_F + abs(rng.gauss(0.0, 2.0))
        tavg = _seasonal_mean(city, day.timetuple().tm_yday) + anomaly
        state = {
            "tavg": tavg,
            "range": daily_range,
            "wet": wet_flags[index],
            "wet_tomorrow": wet_flags[index + 1],
            "prcp": round(0.05 + rng.random() * 0.6, 2) if wet_flags[index] else 0.0,
        }
        hourly.extend(_hourly_rows(city, day, spec.hours, state, rng))
        daily.append(
            (
                city.code,
                city.name,
                day.isoformat(),
                tavg + daily_range / 2.0,
                tavg - daily_range / 2.0,
                tavg,
                anomaly,
                state["prcp"],
            )
        )
    return hourly, daily


def generate_rows(spec: SyntheticSpec) -> tuple[list[tuple], list[tuple]]:
    """Deterministic (hourly rows, daily rows) for the given spec."""
    rng = random.Random(spec.seed)
    hourly: list[tuple] = []
    daily: list[tuple] = []
    for city in spec.cities:
        city_hourly, city_daily = _city_rows(city, spec, rng)
        hourly.extend(city_hourly)
        daily.extend(city_daily)
    return hourly, daily
