# shiftsafe — SPEC

## Problem

A heat rule states a threshold. It does not give a supervisor a plan.
A site manager needs one answer: when should the crew start, when must they rest,
and how much water does each worker need?

shiftsafe turns a public weather forecast into that plan. It estimates WBGT (wet bulb
globe temperature) for each hour. It then returns a start time, a work-rest table and
a water target per worker. Every estimate carries a label that says so.

## Scope of this build

A local-first web app. One location, one date and one task intensity go in.
A shift plan comes out. No account. No API key.

### In scope

1. Location. The user picks an Australian suburb from a bundled table of 53 places,
   or enters a latitude and longitude.
2. Forecast. Hourly temperature, relative humidity, wind speed and shortwave
   radiation come from the free Open-Meteo API.
   - Live fetch with a 7-day horizon.
   - The app uses a bundled snapshot only when the live API is unreachable. The point
     must be within 0.25 degrees of the snapshot point. The UI shows a banner.
3. WBGT estimate per hour, for two exposures: `sun` and `shade`.
4. Thresholds from ISO 7243 for acclimatised and unacclimatised workers.
5. Work-rest allocation from ACGIH-style work/rest tables, per intensity.
6. Shift planner. It scans start hours across the day and returns the plan with the
   lowest heat cost.
7. Water target per worker, from a sweat-rate model.
8. Per-hour table and one reason per hour.
9. Printable crew card, plus CSV export.
10. Measured WBGT input. A site can enter a meter reading and see the difference.
11. SQLite response cache with a visible fetch time. TTL is 30 minutes.
12. Tests with pytest.

### Out of scope

- Medical advice, first aid, or return-to-work decisions.
- On-site sensors, wearables or hardware integration.
- Official warnings. The app never replaces a BOM warning or a site emergency plan.
- Indoor work, radiant heat from plant, or clothing ensembles other than summer workwear.
- Non-Australian time zones in the bundled place table.

## Acceptance criteria

| # | Criterion | How to check it |
|---|-----------|-----------------|
| 1 | `GET /api/health` returns `{"ok": true}` | test |
| 2 | A place search for "cherry" returns Cherrybrook, NSW | test |
| 3 | An unknown place returns 404 with a clear message | test |
| 4 | WBGT at 30 °C and 50 % RH in sun is between 27 and 31 °C | test |
| 5 | Shade WBGT is lower than sun WBGT when shortwave radiation is above 400 W/m² | test |
| 6 | Shade WBGT equals sun WBGT when shortwave radiation is zero | test |
| 7 | Heavy work at WBGT 31 °C returns 0 work minutes | test |
| 8 | Light work at WBGT 26 °C returns 60 work minutes | test |
| 9 | Unacclimatised limits are 2 °C lower than acclimatised limits | test |
| 10 | A hot afternoon forecast produces a start time before 10:00 | test |
| 11 | Every hour of a plan has a WBGT, work minutes, rest minutes, water and a reason | test |
| 12 | A plan for a date outside the forecast returns 400 with the available dates | test |
| 13 | The planner evaluates 12 candidate starts in under 1 second | test with a timer |
| 14 | Cache returns the same payload twice with one upstream call | test with a counter |
| 15 | The page renders summary cards, a WBGT chart, a work-rest strip and a table | screenshot |
| 16 | `GET /api/plan.csv` returns one row per shift hour | test |
| 17 | `python -m pytest` passes | local run |

## Model definitions

### Wet bulb

Stull (2011) fit for wet-bulb temperature, °C. The dry-bulb temperature bounds it, so
it cannot run away at high humidity.

```
Tw = T * atan(0.151977 * sqrt(RH + 8.313659))
   + atan(T + RH)
   - atan(RH - 1.676331)
   + 0.00391838 * RH^1.5 * atan(0.023101 * RH)
   - 4.686035
Tw = min(T, Tw)
```

### WBGT in shade

The ISO 7243 composition without a solar load:

```
WBGT_shade = 0.7 * Tw + 0.3 * T
```

### WBGT in sun

A globe temperature stands in for the radiant load. The globe sits above air
temperature by a solar uplift. Wind damps the uplift. The cap is 20 °C.

```
uplift = min(20, 0.03 * shortwave_wm2) / (1 + 0.15 * wind_ms)
Tg     = T + uplift
WBGT_sun = 0.7 * Tw + 0.2 * Tg + 0.1 * T
```

With no sun the uplift is zero, and `WBGT_sun` equals `WBGT_shade`. The cap keeps the
estimate within a plausible band. An early draft used the BOM Heat Stress Adviser fit.
It reached 46 °C at 38 °C and 80 % RH, which is not physical, so this build uses the
composition above.

### Mixed exposure

For a crew that moves between sun and shade, the app takes the mean of the two
values and states the split in the reason text.

### Reference thresholds

ISO 7243:2017 Table 1, acclimatised workers, °C WBGT.

| Metabolic class | Rate (W/m²) | WBGT limit |
|-----------------|-------------|------------|
| Rest | 65 | 33 |
| Low | 130 | 30 |
| Moderate | 200 | 28 |
| High | 260 | 26 |
| Very high | above 260 | 25 |

The app maps task intensity to those classes:

| App intensity | Rate (W/m²) |
|---------------|-------------|
| light | 100 |
| moderate | 165 |
| heavy | 230 |

An unacclimatised crew works to limits 2 °C lower. This is the usual field adjustment.

### Work-rest allocation

Minutes of work per hour, by WBGT. Values follow ACGIH TLV work/rest allocations.
The app interpolates between the points and rounds to 5 minutes.

| WBGT (light) | Work | WBGT (moderate) | Work | WBGT (heavy) | Work |
|--------------|------|-----------------|------|--------------|------|
| 30.0 | 60 | 27.5 | 60 | 25.0 | 60 |
| 30.6 | 45 | 28.5 | 45 | 26.0 | 45 |
| 31.4 | 30 | 30.0 | 30 | 27.5 | 30 |
| 32.2 | 15 | 31.5 | 15 | 29.0 | 15 |
| 33.0 | 0 | 32.5 | 0 | 30.0 | 0 |

### Water target

Sweat rate in litres per hour of work:

```
rate = base[intensity] + 0.15 * max(0, WBGT - 25)
rate = min(1.5, rate)
base = {light: 0.40, moderate: 0.60, heavy: 0.80}
```

Water for the shift is the sum of `rate * work_fraction` for each hour. The card
shows litres per worker and litres for the crew.

## Planner

Candidate start hours run from `earliest_start` to `latest_start`, on the hour.
A candidate must fit the full shift length inside the available forecast.

Cost for one candidate:

```
per hour:
  excess  = max(0, wbgt - continuous_limit)
  cost   += 6.0 * excess^2
  cost   += 400 * max(0, wbgt - continuous_limit - 4)
  cost   += 0.50 * rest_minutes
  cost   += 250 when the hour allows no work at all
late_penalty = 0.02 * hours_after_earliest
```

Lost work time costs five times more than it did in the first draft. Without that
weight, an afternoon start scored best on a hot day, because the last hours of the
shift fell into the cool evening. That plan gave the crew 1.3 hours of work in an
8-hour shift. A zero-work hour now carries a heavy penalty, so the planner prefers a
cool morning start.

The planner returns the cheapest candidate. Ties go to the earlier start.
The response reports the total cost, so the user can compare options.

## Data sources

- Open-Meteo Forecast API — <https://open-meteo.com/en/docs>
  Fields: `temperature_2m`, `relative_humidity_2m`, `wind_speed_10m`,
  `shortwave_radiation`. Free for non-commercial use. No key.
- ISO 7243:2017 — ergonomics of the thermal environment, WBGT index.
- ACGIH TLV — heat stress, work/rest allocations.
- Safe Work Australia — guidance on heat and outdoor work.
- Bundled snapshot — `data/sample_forecast.json`. A real Open-Meteo response for
  Cherrybrook, NSW. Collected on 2026-11-16. It exists for offline demos and tests.

## Risks and limits

- WBGT from weather data is an estimate. It is not a measurement. The header of every
  plan says so. A site can enter a measured value and compare.
- The model assumes summer workwear and no radiant heat from plant or surfaces.
- The globe uplift and its wind damping are engineering assumptions. They have bounds,
  but they are not a published fit.
- The bundled snapshot covers three days. It is not a forecast for any other site.
- A plan is guidance. It never replaces an official warning, a site procedure, or
  the judgement of a supervisor.

## Done when

The app starts with `python run.py`. A user picks a place and a date, sets intensity,
crew size and shift length, and sees a start time, an hourly work-rest table, a water
target and a printable crew card. Tests pass. The README shows a real screenshot.