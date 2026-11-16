"""Work-rest allocation, water targets and plain-language reasons."""

from __future__ import annotations

from . import config


def work_minutes(wbgt_value: float, intensity: str, acclimatised: bool = True) -> int:
    """Minutes of work allowed in one hour, rounded to 5 minutes."""
    points = [
        (t + (0.0 if acclimatised else config.UNACCLIMATISED_OFFSET), m)
        for t, m in config.WORK_REST_TABLE[intensity]
    ]
    if wbgt_value <= points[0][0]:
        return int(points[0][1])
    for (t0, m0), (t1, m1) in zip(points, points[1:]):
        if wbgt_value <= t1:
            span = t1 - t0
            frac = 0.0 if span <= 0 else (wbgt_value - t0) / span
            raw = m0 + frac * (m1 - m0)
            return int(round(raw / 5.0) * 5)
    return 0


def rest_minutes(wbgt_value: float, intensity: str, acclimatised: bool = True) -> int:
    """Minutes of rest required in one hour."""
    return 60 - work_minutes(wbgt_value, intensity, acclimatised)


def sweat_rate(wbgt_value: float, intensity: str) -> float:
    """Litres of sweat per hour of work."""
    base = config.SWEAT_BASE[intensity]
    extra = config.SWEAT_PER_DEGREE * max(0.0, wbgt_value - config.SWEAT_FREE_WBGT)
    return round(min(config.SWEAT_MAX, base + extra), 2)


def water_litres(wbgt_value: float, intensity: str, work_min: int) -> float:
    """Litres to drink for one hour, scaled by the worked fraction."""
    return round(sweat_rate(wbgt_value, intensity) * (work_min / 60.0), 2)


def reason(
    wbgt_value: float,
    limit: float,
    work_min: int,
    exposure: str,
    shortwave_wm2: float,
) -> str:
    """One short line that explains the allocation for this hour."""
    exposure_text = {
        "sun": "full sun",
        "shade": "shade",
        "mixed": "half sun and half shade",
    }[exposure]

    if work_min >= 60:
        head = f"Work through. WBGT {wbgt_value:.1f} C is at or below the {limit:.1f} C limit."
    elif work_min == 0:
        head = f"Stop work. WBGT {wbgt_value:.1f} C is above the {limit:.1f} C limit."
    else:
        head = f"Work {work_min} min, then rest {60 - work_min} min."

    detail = f"Trade-off is {exposure_text}."
    if shortwave_wm2 < 50:
        detail += " Low sun, so shade adds little."
    return f"{head} {detail}"