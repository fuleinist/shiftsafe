"""Psychrometrics and the WBGT estimate.

The estimate follows the ISO 7243 outdoor composition:

    WBGT = 0.7 * Tnw + 0.2 * Tg + 0.1 * Ta

The natural wet bulb temperature (Tnw) comes from Stull's wet-bulb fit, which is
bounded by the air temperature. The globe temperature (Tg) is the air temperature
plus a solar uplift. The uplift grows with shortwave radiation and falls with wind.
In shade the uplift is zero, so the composition reduces to 0.7 * Tnw + 0.3 * Ta.

This is an estimate from weather data. It is not a measurement.
"""

from __future__ import annotations

import math

from . import config

EXPOSURES = ("sun", "shade", "mixed")


def saturation_vapour_pressure(temp_c: float) -> float:
    """Saturation vapour pressure in hPa. Magnus formula."""
    return 6.112 * math.exp(17.62 * temp_c / (243.12 + temp_c))


def vapour_pressure(temp_c: float, relative_humidity: float) -> float:
    """Actual vapour pressure in hPa. RH is clamped to 0..100."""
    rh = max(0.0, min(100.0, float(relative_humidity)))
    return saturation_vapour_pressure(temp_c) * rh / 100.0


def wet_bulb(temp_c: float, relative_humidity: float) -> float:
    """Wet-bulb temperature in degC. Stull (2011) fit, valid near sea level.

    The result is capped at the dry-bulb temperature. At 100 % RH the two are equal.
    """
    rh = max(1.0, min(100.0, float(relative_humidity)))
    temp = float(temp_c)
    value = (
        temp * math.atan(0.151977 * math.sqrt(rh + 8.313659))
        + math.atan(temp + rh)
        - math.atan(rh - 1.676331)
        + 0.00391838 * (rh ** 1.5) * math.atan(0.023101 * rh)
        - 4.686035
    )
    return min(temp, value)


def globe_uplift(shortwave_wm2: float, wind_ms: float = 0.0) -> float:
    """Globe temperature rise above air temperature, in degC.

    The rise grows with shortwave radiation and falls with wind. It is capped, so a
    bad input cannot produce an extreme value.
    """
    solar = max(0.0, float(shortwave_wm2))
    wind = max(0.0, float(wind_ms))
    raw = min(config.GLOBE_UPLIFT_MAX, config.GLOBE_UPLIFT_PER_WM2 * solar)
    return raw / (1.0 + config.GLOBE_WIND_DAMPING * wind)


def wbgt_shade(temp_c: float, relative_humidity: float) -> float:
    """WBGT in shade, degC. No solar load."""
    return round(
        0.7 * wet_bulb(temp_c, relative_humidity) + 0.3 * float(temp_c), 1
    )


def wbgt_sun(
    temp_c: float,
    relative_humidity: float,
    wind_ms: float = 0.0,
    shortwave_wm2: float = 0.0,
) -> float:
    """WBGT in sun, degC, from the ISO 7243 composition with a solar globe uplift."""
    temp = float(temp_c)
    globe = temp + globe_uplift(shortwave_wm2, wind_ms)
    value = 0.7 * wet_bulb(temp, relative_humidity) + 0.2 * globe + 0.1 * temp
    return round(value, 1)


def wbgt(
    temp_c: float,
    relative_humidity: float,
    wind_ms: float = 0.0,
    shortwave_wm2: float = 0.0,
    exposure: str = "sun",
) -> float:
    """WBGT for one exposure setting, degC."""
    if exposure not in EXPOSURES:
        raise ValueError(f"unknown exposure: {exposure!r}")
    sun = wbgt_sun(temp_c, relative_humidity, wind_ms, shortwave_wm2)
    if exposure == "sun":
        return sun
    shade = wbgt_shade(temp_c, relative_humidity)
    if exposure == "shade":
        return shade
    return round((sun + shade) / 2.0, 1)


def heat_class(value: float, limit: float) -> str:
    """Plain label for one hour, relative to the continuous work limit."""
    if value <= limit - 2.0:
        return "low"
    if value <= limit:
        return "rising"
    if value <= limit + 2.0:
        return "high"
    return "extreme"