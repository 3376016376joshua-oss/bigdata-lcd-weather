"""Metric to U.S. customary conversions for LCD v2 values.

LCD v2 reports temperatures in degC, precipitation and snow in mm, pressure in hPa, wind
speed in m/s and visibility in km. The functions are plain arithmetic, so they accept a
float, a NumPy array, a pandas Series or a Spark Column; a ``None`` input gives ``None``.
"""

FAHRENHEIT_PER_CELSIUS = 9.0 / 5.0
FAHRENHEIT_AT_ZERO_CELSIUS = 32.0
MM_PER_INCH = 25.4
HPA_PER_INHG = 33.8638866667
MPH_PER_MS = 3600.0 / 1609.344
KM_PER_MILE = 1.609344


def c_to_f(celsius):
    """Temperature in degC to degF."""
    if celsius is None:
        return None
    return celsius * FAHRENHEIT_PER_CELSIUS + FAHRENHEIT_AT_ZERO_CELSIUS


def delta_c_to_f(delta_celsius):
    """Temperature difference to degF: departures from normal, ranges and degree days."""
    if delta_celsius is None:
        return None
    return delta_celsius * FAHRENHEIT_PER_CELSIUS


def mm_to_in(millimetres):
    """Precipitation, snowfall or snow depth in mm to inches."""
    if millimetres is None:
        return None
    return millimetres / MM_PER_INCH


def hpa_to_inhg(hectopascals):
    """Pressure in hPa to inches of mercury."""
    if hectopascals is None:
        return None
    return hectopascals / HPA_PER_INHG


def ms_to_mph(metres_per_second):
    """Wind speed in m/s to miles per hour."""
    if metres_per_second is None:
        return None
    return metres_per_second * MPH_PER_MS


def km_to_mi(kilometres):
    """Visibility in km to statute miles."""
    if kilometres is None:
        return None
    return kilometres / KM_PER_MILE
