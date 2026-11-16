import time

import pytest

from shiftsafe import planner
from shiftsafe.providers import parse_payload

from conftest import make_payload


def hours_for(date="2026-11-17"):
    return planner.annotate_hours(parse_payload(make_payload(date)), "sun")


def test_hot_afternoon_pushes_the_start_early():
    plan = planner.build_plan(
        hours_for(),
        "2026-11-17",
        intensity="moderate",
        crew=4,
        shift_hours=8,
        earliest_start=5,
        latest_start=14,
        exposure="sun",
        acclimatised=True,
    )
    assert plan["start_hour"] < 10
    assert plan["start"] == "05:00"
    assert plan["finish"] == "13:00"


def test_plan_rows_are_complete():
    plan = planner.build_plan(
        hours_for(),
        "2026-11-17",
        intensity="moderate",
        crew=4,
        shift_hours=8,
        earliest_start=5,
        latest_start=14,
        exposure="sun",
        acclimatised=True,
    )
    assert len(plan["hours"]) == 8
    for row in plan["hours"]:
        assert row["reason"].strip()
        assert 0 <= row["work_min"] <= 60
        assert row["work_min"] + row["rest_min"] == 60
        assert row["water_l"] >= 0
        assert row["wbgt"] > 0
        assert row["class"] in ("low", "rising", "high", "extreme")


def test_totals_match_the_rows():
    plan = planner.build_plan(
        hours_for(),
        "2026-11-17",
        intensity="heavy",
        crew=6,
        shift_hours=6,
        earliest_start=6,
        latest_start=12,
        exposure="sun",
        acclimatised=False,
    )
    assert plan["totals"]["work_minutes"] == sum(row["work_min"] for row in plan["hours"])
    assert plan["totals"]["rest_minutes"] == sum(row["rest_min"] for row in plan["hours"])
    assert plan["totals"]["water_crew_l"] == pytest.approx(
        round(plan["totals"]["water_per_worker_l"] * 6, 1), abs=0.2
    )


def test_missing_date_raises():
    with pytest.raises(ValueError):
        planner.build_plan(
            hours_for(),
            "2026-12-01",
            "moderate",
            4,
            8,
            5,
            14,
            "sun",
            True,
        )


def test_shift_that_does_not_fit_raises():
    with pytest.raises(ValueError):
        planner.build_plan(
            hours_for(),
            "2026-11-17",
            "moderate",
            4,
            8,
            20,
            21,
            "sun",
            True,
        )


def test_candidate_starts_respect_the_window():
    hours = hours_for()
    day = [row for row in hours if row["time"][:10] == "2026-11-17"]
    assert planner.candidate_starts(day, 8, 5, 14) == list(range(5, 15))


def test_planner_is_fast():
    hours = hours_for()
    started = time.perf_counter()
    planner.build_plan(hours, "2026-11-17", "moderate", 4, 8, 5, 14, "sun", True)
    elapsed = time.perf_counter() - started
    assert elapsed < 1.0


def test_measured_reading_reports_the_delta():
    plan = planner.build_plan(
        hours_for(),
        "2026-11-17",
        "moderate",
        4,
        8,
        5,
        14,
        "sun",
        True,
        measured_wbgt=40.0,
    )
    assert plan["measured"]["wbgt"] == 40.0
    assert plan["measured"]["delta_vs_peak"] > 0
    assert "Trust the meter" in plan["measured"]["note"]


def test_alternatives_are_ranked_by_cost():
    plan = planner.build_plan(
        hours_for(), "2026-11-17", "moderate", 4, 8, 5, 14, "shade", True
    )
    costs = [item["cost"] for item in plan["alternatives"]]
    assert costs == sorted(costs)