import math

import pytest

from shiftsafe import config
from shiftsafe.wbgt import (
    globe_uplift,
    heat_class,
    saturation_vapour_pressure,
    vapour_pressure,
    wbgt,
    wbgt_shade,
    wbgt_sun,
    wet_bulb,
)


def test_saturation_vapour_pressure_at_30c():
    value = saturation_vapour_pressure(30.0)
    assert 42.0 < value < 42.7


def test_vapour_pressure_scales_with_humidity():
    assert vapour_pressure(30.0, 50.0) == pytest.approx(saturation_vapour_pressure(30.0) * 0.5)
    assert vapour_pressure(30.0, 0.0) == 0.0
    assert vapour_pressure(30.0, 100.0) == pytest.approx(saturation_vapour_pressure(30.0))


def test_vapour_pressure_clamps_humidity():
    assert vapour_pressure(30.0, 140.0) == pytest.approx(vapour_pressure(30.0, 100.0))
    assert vapour_pressure(30.0, -20.0) == 0.0


def test_wet_bulb_never_exceeds_air_temperature():
    for rh in (0, 25, 50, 75, 100):
        assert wet_bulb(32.0, rh) <= 32.0


def test_wet_bulb_equals_air_temperature_at_saturation():
    assert wet_bulb(24.0, 100.0) == pytest.approx(24.0, abs=0.2)


def test_wet_bulb_at_30c_and_50_percent_is_about_22():
    assert 21.0 < wet_bulb(30.0, 50.0) < 22.6


def test_globe_uplift_is_capped():
    assert globe_uplift(0.0, 0.0) == 0.0
    assert globe_uplift(5000.0, 0.0) == config.GLOBE_UPLIFT_MAX


def test_wind_lowers_the_globe_uplift():
    assert globe_uplift(800.0, 4.0) < globe_uplift(800.0, 0.0)


def test_wbgt_sun_is_plausible_at_30c_and_50_percent():
    value = wbgt_sun(30.0, 50.0, 0.0, 800.0)
    assert 27.0 <= value <= 31.0


def test_shade_is_cooler_than_sun_in_full_sun():
    sun = wbgt_sun(31.0, 50.0, 2.0, 800.0)
    shade = wbgt_shade(31.0, 50.0)
    assert shade < sun


def test_shade_equals_sun_without_solar_load():
    assert wbgt_sun(19.0, 80.0, 2.0, 0.0) == wbgt_shade(19.0, 80.0)


def test_mixed_is_the_mean():
    sun = wbgt(30.0, 50.0, 2.0, 800.0, "sun")
    shade = wbgt(30.0, 50.0, 2.0, 800.0, "shade")
    mixed = wbgt(30.0, 50.0, 2.0, 800.0, "mixed")
    assert mixed == pytest.approx((sun + shade) / 2.0, abs=0.1)


def test_unknown_exposure_is_rejected():
    with pytest.raises(ValueError):
        wbgt(30.0, 50.0, 1.0, 100.0, "indoor")


def test_heat_class_bands():
    limit = 28.0
    assert heat_class(25.0, limit) == "low"
    assert heat_class(27.5, limit) == "rising"
    assert heat_class(29.0, limit) == "high"
    assert heat_class(32.0, limit) == "extreme"


def test_hot_and_humid_stays_bounded():
    value = wbgt_sun(38.0, 80.0, 2.0, 800.0)
    assert math.isfinite(value)
    assert 30.0 < value < 45.0


def test_wbgt_never_runs_far_above_air_temperature():
    for temp in (10.0, 25.0, 38.0, 48.0):
        for rh in (10.0, 50.0, 95.0):
            value = wbgt_sun(temp, rh, 0.0, 1100.0)
            assert value <= temp + 8.0