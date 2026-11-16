import pytest

from shiftsafe import config
from shiftsafe.workrest import reason, rest_minutes, sweat_rate, water_litres, work_minutes


def test_continuous_limits_by_intensity():
    assert config.continuous_limit("light") == 30.0
    assert config.continuous_limit("moderate") == 28.0
    assert config.continuous_limit("heavy") == 26.0


def test_unacclimatised_limit_is_two_degrees_lower():
    for intensity in config.INTENSITIES:
        warm = config.continuous_limit(intensity, True)
        cold = config.continuous_limit(intensity, False)
        assert warm - cold == 2.0


def test_heavy_work_stops_at_31c():
    assert work_minutes(31.0, "heavy") == 0


def test_light_work_continues_at_26c():
    assert work_minutes(26.0, "light") == 60


def test_moderate_work_has_a_full_hour_below_limit():
    assert work_minutes(27.5, "moderate") == 60


def test_allocation_drops_with_heat():
    values = [work_minutes(value, "moderate") for value in (27.0, 28.5, 30.0, 31.5, 33.0)]
    assert values == sorted(values, reverse=True)
    assert values[0] == 60
    assert values[-1] == 0


def test_interpolation_rounds_to_five_minutes():
    assert work_minutes(29.25, "moderate") == 40


def test_rest_completes_the_hour():
    for value in (20.0, 27.0, 29.9, 35.0):
        for intensity in config.INTENSITIES:
            assert work_minutes(value, intensity) + rest_minutes(value, intensity) == 60


def test_unacclimatised_crew_works_less_in_the_same_heat():
    assert work_minutes(29.0, "moderate", False) <= work_minutes(29.0, "moderate", True)


def test_sweat_rate_grows_with_heat_and_caps():
    assert sweat_rate(25.0, "moderate") == 0.6
    assert sweat_rate(30.0, "moderate") == pytest.approx(1.35)
    assert sweat_rate(45.0, "heavy") == config.SWEAT_MAX


def test_water_scales_with_worked_minutes():
    full = water_litres(30.0, "moderate", 60)
    half = water_litres(30.0, "moderate", 30)
    assert full == pytest.approx(1.35)
    assert half == pytest.approx(0.68, abs=0.01)


def test_reason_is_never_empty_and_mentions_the_action():
    assert "Work through" in reason(26.0, 28.0, 60, "sun", 800.0)
    assert "Stop work" in reason(31.0, 28.0, 0, "sun", 800.0)
    partial = reason(29.0, 28.0, 30, "mixed", 800.0)
    assert "Work 30 min" in partial
    assert "rest 30 min" in partial
    assert "half sun and half shade" in partial


def test_reason_notes_low_sun_at_night():
    assert "Low sun" in reason(24.0, 28.0, 60, "shade", 0.0)