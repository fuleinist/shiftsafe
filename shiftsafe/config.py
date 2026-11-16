"""Tunable constants for the heat model.

Every value here is an engineering assumption or a published reference value.
None of them is a measurement. The UI states that the plan is an estimate.
"""

# Metabolic rate for each app intensity, W/m2 of body surface (ISO 8996 classes).
INTENSITIES = {
    "light": 100.0,
    "moderate": 165.0,
    "heavy": 230.0,
}

INTENSITY_LABELS = {
    "light": "Light (walking, light tools)",
    "moderate": "Moderate (lifting, digging)",
    "heavy": "Heavy (shovelling, carrying)",
}

# ISO 7243:2017 Table 1, acclimatised workers. (metabolic rate upper bound, WBGT limit)
ISO_REFERENCE = [
    (65.0, 33.0),      # rest
    (130.0, 30.0),     # low
    (200.0, 28.0),     # moderate
    (260.0, 26.0),     # high
    (10000.0, 25.0),   # very high
]

# Field adjustment for a crew that is not used to the heat.
UNACCLIMATISED_OFFSET = -2.0

# ACGIH work/rest allocations. (WBGT degC, work minutes per hour)
WORK_REST_TABLE = {
    "light": [(30.0, 60.0), (30.6, 45.0), (31.4, 30.0), (32.2, 15.0), (33.0, 0.0)],
    "moderate": [(27.5, 60.0), (28.5, 45.0), (30.0, 30.0), (31.5, 15.0), (32.5, 0.0)],
    "heavy": [(25.0, 60.0), (26.0, 45.0), (27.5, 30.0), (29.0, 15.0), (30.0, 0.0)],
}

# Sweat model. Litres per hour of work.
SWEAT_BASE = {"light": 0.40, "moderate": 0.60, "heavy": 0.80}
SWEAT_PER_DEGREE = 0.15   # extra litres per hour for each degree above 25 C
SWEAT_FREE_WBGT = 25.0
SWEAT_MAX = 1.5

# WBGT model.
# Globe temperature rise above air temperature. The rise is capped and damped by wind.
GLOBE_UPLIFT_PER_WM2 = 0.03
GLOBE_UPLIFT_MAX = 20.0
GLOBE_WIND_DAMPING = 0.15

# Planner.
MIN_SHIFT_HOURS = 2
MAX_SHIFT_HOURS = 12
HEAT_COST_WEIGHT = 6.0
OVER_LIMIT_COST = 400.0
REST_COST_PER_MINUTE = 0.50
ZERO_WORK_COST = 250.0
LATE_COST_PER_HOUR = 0.02

# Cache.
CACHE_TTL_SECONDS = 1800
FORECAST_DAYS = 7
SNAPSHOT_TOLERANCE_DEGREES = 0.25

# Defaults for the planner form.
DEFAULT_INTENSITY = "moderate"
DEFAULT_CREW = 4
DEFAULT_SHIFT_HOURS = 8
DEFAULT_EARLIEST_START = 5
DEFAULT_LATEST_START = 14


def continuous_limit(intensity: str, acclimatised: bool = True) -> float:
    """Return the ISO 7243 WBGT limit for continuous work, in degC."""
    rate = INTENSITIES[intensity]
    limit = ISO_REFERENCE[-1][1]
    for upper, value in ISO_REFERENCE:
        if rate <= upper:
            limit = value
            break
    if not acclimatised:
        limit += UNACCLIMATISED_OFFSET
    return limit