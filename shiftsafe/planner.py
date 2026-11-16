"""Shift planner.

The planner scores every legal start hour and returns the plan with the lowest
heat cost. Cost grows with WBGT above the continuous limit, with lost work time,
and with a late start.
"""

from __future__ import annotations

from datetime import datetime

from . import config
from .workrest import reason, water_litres, work_minutes
from .wbgt import heat_class, wbgt


def _hour_label(iso_time: str) -> str:
    return iso_time[11:16]


def _hour_of_day(iso_time: str) -> int:
    return int(iso_time[11:13])


def annotate_hours(hours: list[dict], exposure: str) -> list[dict]:
    """Add a WBGT value and a heat class to each raw forecast hour."""
    out = []
    for row in hours:
        value = wbgt(
            row["temp_c"],
            row["rh"],
            row.get("wind_ms", 0.0),
            row.get("solar", 0.0),
            exposure,
        )
        out.append({**row, "wbgt": value})
    return out


def _shift_cost(block: list[dict], intensity: str, acclimatised: bool) -> float:
    limit = config.continuous_limit(intensity, acclimatised)
    cost = 0.0
    for row in block:
        excess = max(0.0, row["wbgt"] - limit)
        cost += config.HEAT_COST_WEIGHT * excess * excess
        cost += config.OVER_LIMIT_COST * max(0.0, row["wbgt"] - limit - 4.0)
        worked = work_minutes(row["wbgt"], intensity, acclimatised)
        cost += config.REST_COST_PER_MINUTE * (60 - worked)
        if worked == 0:
            cost += config.ZERO_WORK_COST
    return cost


def candidate_starts(day_hours: list[dict], shift_hours: int, earliest: int, latest: int) -> list[int]:
    """Legal start hours for the day. A start must fit the shift inside the day."""
    available = {_hour_of_day(row["time"]) for row in day_hours}
    starts = []
    for start in range(earliest, latest + 1):
        if all((start + offset) in available for offset in range(shift_hours)):
            starts.append(start)
    return starts


def _build_block(day_hours, start, shift_hours):
    by_hour = {_hour_of_day(row["time"]): row for row in day_hours}
    return [by_hour[start + offset] for offset in range(shift_hours)]


def _recommendation(start_hour, finish_hour, peak, limit, total_rest, water_worker, over_hours):
    text = f"Start at {start_hour:02d}:00 and finish at {finish_hour:02d}:00."
    text += f" Peak WBGT is {peak['wbgt']:.1f} C at {peak['time'][11:16]}."
    if over_hours:
        text += f" {over_hours} hour(s) sit above the {limit:.1f} C continuous limit."
    else:
        text += f" Every hour sits at or below the {limit:.1f} C continuous limit."
    if total_rest:
        text += f" The crew rests {total_rest} min in total."
    text += f" Water target is {water_worker:.1f} L per worker."
    return text


def build_plan(
    hours: list[dict],
    date: str,
    intensity: str,
    crew: int,
    shift_hours: int,
    earliest_start: int,
    latest_start: int,
    exposure: str,
    acclimatised: bool,
    measured_wbgt: float | None = None,
) -> dict:
    """Return the full plan document for one day and one set of settings."""
    day_hours = [row for row in hours if row["time"][:10] == date]
    if not day_hours:
        raise ValueError(f"no forecast for {date}")

    day_hours = annotate_hours(day_hours, exposure)
    limit = config.continuous_limit(intensity, acclimatised)
    starts = candidate_starts(day_hours, shift_hours, earliest_start, latest_start)
    if not starts:
        raise ValueError(
            f"no start time fits a {shift_hours} hour shift between "
            f"{earliest_start:02d}:00 and {latest_start:02d}:00 on {date}"
        )

    scored = []
    for start in starts:
        block = _build_block(day_hours, start, shift_hours)
        cost = _shift_cost(block, intensity, acclimatised)
        cost += config.LATE_COST_PER_HOUR * (start - earliest_start)
        scored.append((cost, start, block))
    scored.sort(key=lambda item: (item[0], item[1]))
    cost, start, block = scored[0]

    rows = []
    total_work = 0
    total_rest = 0
    total_water = 0.0
    over_hours = 0
    for row in block:
        work = work_minutes(row["wbgt"], intensity, acclimatised)
        rest = 60 - work
        water = water_litres(row["wbgt"], intensity, work)
        if work == 0:
            over_hours += 1
        total_work += work
        total_rest += rest
        total_water += water
        rows.append(
            {
                "time": row["time"],
                "label": _hour_label(row["time"]),
                "temp_c": row["temp_c"],
                "rh": row["rh"],
                "wind_ms": row.get("wind_ms", 0.0),
                "shortwave_wm2": row.get("solar", 0.0),
                "wbgt": row["wbgt"],
                "limit": round(limit, 1),
                "work_min": work,
                "rest_min": rest,
                "water_l": water,
                "class": heat_class(row["wbgt"], limit),
                "reason": reason(row["wbgt"], limit, work, exposure, row.get("solar", 0.0)),
            }
        )

    peak = max(rows, key=lambda item: item["wbgt"])
    hottest_allowed = max(row["wbgt"] for row in day_hours)

    warnings = []
    if over_hours:
        warnings.append(
            f"Work stops for {over_hours} hour(s). Move the shift earlier or add a night crew."
        )
    if peak["wbgt"] >= limit + 4.0:
        warnings.append(
            "Peak WBGT is 4 C or more above the continuous limit. Consider a night shift."
        )
    if not acclimatised:
        warnings.append("Limits are 2 C lower because the crew is not acclimatised.")

    measured = None
    if measured_wbgt is not None:
        delta = round(float(measured_wbgt) - peak["wbgt"], 1)
        if delta > 0:
            note = f"Measured WBGT is {delta:.1f} C above the modelled peak. Trust the meter."
        elif delta < 0:
            note = f"Measured WBGT is {abs(delta):.1f} C below the modelled peak. Trust the meter."
        else:
            note = "Measured WBGT matches the modelled peak."
        measured = {"wbgt": round(float(measured_wbgt), 1), "delta_vs_peak": delta, "note": note}

    alternatives = [
        {
            "start": f"{candidate[1]:02d}:00",
            "cost": round(candidate[0], 2),
            "peak_wbgt": max(row["wbgt"] for row in candidate[2]),
        }
        for candidate in scored[:3]
    ]

    return {
        "date": date,
        "start": f"{start:02d}:00",
        "finish": f"{start + shift_hours:02d}:00",
        "start_hour": start,
        "shift_hours": shift_hours,
        "cost": round(cost, 2),
        "limit_c": round(limit, 1),
        "exposure": exposure,
        "intensity": intensity,
        "crew": crew,
        "acclimatised": acclimatised,
        "hours": rows,
        "totals": {
            "work_minutes": total_work,
            "rest_minutes": total_rest,
            "work_hours": round(total_work / 60.0, 1),
            "rest_hours": round(total_rest / 60.0, 1),
            "water_per_worker_l": round(total_water, 1),
            "water_crew_l": round(total_water * crew, 1),
            "peak_wbgt": peak["wbgt"],
            "peak_time": peak["time"][11:16],
            "peak_temp_c": peak["temp_c"],
            "hours_above_limit": sum(1 for row in rows if row["wbgt"] > limit),
            "hottest_available_wbgt": hottest_allowed,
        },
        "warnings": warnings,
        "measured": measured,
        "recommendation": _recommendation(
            start,
            start + shift_hours,
            peak,
            limit,
            total_rest,
            total_water,
            over_hours,
        ),
        "alternatives": alternatives,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }