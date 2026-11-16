"""HTTP API and static file host for shiftsafe."""

from __future__ import annotations

import csv
import io
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from . import config, places, planner, providers
from .providers import Cache, ForecastUnavailable

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
VERSION = "1.0.0"


def _today() -> str:
    """Today in Sydney, with a safe fallback if tz data is missing."""
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo("Australia/Sydney")).date().isoformat()
    except Exception:
        return datetime.now().date().isoformat()


def create_app(cache_path: str | Path | None = None, fetcher=providers.fetch_live) -> FastAPI:
    """Build the app. Tests pass a private cache path and a stub fetcher."""
    app = FastAPI(
        title="shiftsafe",
        version=VERSION,
        description="Heat-safe shift planner. Estimates WBGT and returns work-rest cycles.",
    )
    cache = Cache(cache_path)

    def resolve_place(place: str | None, lat: float | None, lon: float | None) -> dict:
        if place:
            found = places.get(place)
            if found is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Unknown place '{place}'. Try /api/places?q= to search.",
                )
            return found
        if lat is None or lon is None:
            raise HTTPException(
                status_code=400,
                detail="Provide a place name, or both lat and lon.",
            )
        if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
            raise HTTPException(status_code=400, detail="lat or lon is out of range.")
        return {
            "id": None,
            "name": f"{lat:.3f}, {lon:.3f}",
            "state": "",
            "lat": float(lat),
            "lon": float(lon),
        }

    def validate(intensity: str, exposure: str, crew: int, shift_hours: int,
                 earliest: int, latest: int) -> None:
        if intensity not in config.INTENSITIES:
            raise HTTPException(
                status_code=400,
                detail=f"intensity must be one of {sorted(config.INTENSITIES)}.",
            )
        if exposure not in ("sun", "shade", "mixed"):
            raise HTTPException(
                status_code=400, detail="exposure must be one of sun, shade, mixed."
            )
        if not (1 <= crew <= 200):
            raise HTTPException(status_code=400, detail="crew must be between 1 and 200.")
        if not (config.MIN_SHIFT_HOURS <= shift_hours <= config.MAX_SHIFT_HOURS):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"shift_hours must be between {config.MIN_SHIFT_HOURS} and "
                    f"{config.MAX_SHIFT_HOURS}."
                ),
            )
        if not (0 <= earliest <= 23) or not (0 <= latest <= 23):
            raise HTTPException(status_code=400, detail="start hours must be between 0 and 23.")
        if earliest > latest:
            raise HTTPException(status_code=400, detail="earliest_start must not exceed latest_start.")
        if latest + shift_hours > 24:
            raise HTTPException(
                status_code=400,
                detail="latest_start plus shift_hours must finish by 24:00.",
            )

    def build(lat, lon, date, intensity, crew, shift_hours, earliest, latest,
              exposure, acclimatised, measured_wbgt, tz) -> dict:
        try:
            hours, meta = providers.get_forecast(lat, lon, cache, fetcher=fetcher, tz=tz)
        except ForecastUnavailable as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

        available = sorted({row["time"][:10] for row in hours})
        chosen = date or (_today() if _today() in available else available[0])
        if chosen not in available:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": f"No forecast for {chosen}.",
                    "available_dates": available,
                },
            )

        try:
            plan = planner.build_plan(
                hours,
                chosen,
                intensity,
                crew,
                shift_hours,
                earliest,
                latest,
                exposure,
                acclimatised,
                measured_wbgt,
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        return {
            "place": {"name": None, "state": None, "lat": lat, "lon": lon},
            "date": chosen,
            "available_dates": available,
            "data": meta,
            "plan": plan,
        }

    @app.get("/api/health")
    def health() -> dict:
        return {"ok": True, "service": "shiftsafe", "version": VERSION}

    @app.get("/api/places")
    def list_places(q: str = "") -> dict:
        results = places.search(q)
        return {"places": results, "count": len(results), "total": len(places.PLACES)}

    @app.get("/api/meta")
    def meta() -> dict:
        return {
            "version": VERSION,
            "intensities": [
                {"id": key, "label": config.INTENSITY_LABELS[key], "rate_wm2": config.INTENSITIES[key]}
                for key in config.INTENSITIES
            ],
            "defaults": {
                "intensity": config.DEFAULT_INTENSITY,
                "crew": config.DEFAULT_CREW,
                "shift_hours": config.DEFAULT_SHIFT_HOURS,
                "earliest_start": config.DEFAULT_EARLIEST_START,
                "latest_start": config.DEFAULT_LATEST_START,
            },
            "places": len(places.PLACES),
            "max_shift_hours": config.MAX_SHIFT_HOURS,
        }

    @app.get("/api/plan")
    def plan_endpoint(
        place: str | None = Query(default=None),
        lat: float | None = Query(default=None),
        lon: float | None = Query(default=None),
        date: str | None = Query(default=None),
        intensity: str = Query(default=config.DEFAULT_INTENSITY),
        crew: int = Query(default=config.DEFAULT_CREW),
        shift_hours: int = Query(default=config.DEFAULT_SHIFT_HOURS),
        earliest_start: int = Query(default=config.DEFAULT_EARLIEST_START),
        latest_start: int = Query(default=config.DEFAULT_LATEST_START),
        exposure: str = Query(default="sun"),
        acclimatised: bool = Query(default=True),
        measured_wbgt: float | None = Query(default=None, ge=-10.0, le=60.0),
    ) -> dict:
        resolved = resolve_place(place, lat, lon)
        validate(intensity, exposure, crew, shift_hours, earliest_start, latest_start)
        document = build(
            resolved["lat"],
            resolved["lon"],
            date,
            intensity,
            crew,
            shift_hours,
            earliest_start,
            latest_start,
            exposure,
            acclimatised,
            measured_wbgt,
            places.timezone_for(resolved),
        )
        document["place"] = resolved
        return document

    @app.get("/api/plan.csv")
    def plan_csv(
        place: str | None = Query(default=None),
        lat: float | None = Query(default=None),
        lon: float | None = Query(default=None),
        date: str | None = Query(default=None),
        intensity: str = Query(default=config.DEFAULT_INTENSITY),
        crew: int = Query(default=config.DEFAULT_CREW),
        shift_hours: int = Query(default=config.DEFAULT_SHIFT_HOURS),
        earliest_start: int = Query(default=config.DEFAULT_EARLIEST_START),
        latest_start: int = Query(default=config.DEFAULT_LATEST_START),
        exposure: str = Query(default="sun"),
        acclimatised: bool = Query(default=True),
        measured_wbgt: float | None = Query(default=None, ge=-10.0, le=60.0),
    ) -> Response:
        resolved = resolve_place(place, lat, lon)
        validate(intensity, exposure, crew, shift_hours, earliest_start, latest_start)
        document = build(
            resolved["lat"],
            resolved["lon"],
            date,
            intensity,
            crew,
            shift_hours,
            earliest_start,
            latest_start,
            exposure,
            acclimatised,
            measured_wbgt,
            places.timezone_for(resolved),
        )
        plan = document["plan"]

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            [
                "date",
                "place",
                "start",
                "finish",
                "intensity",
                "crew",
                "hour",
                "temp_c",
                "rh_percent",
                "wind_ms",
                "shortwave_wm2",
                "wbgt_c",
                "limit_c",
                "work_min",
                "rest_min",
                "water_l_per_worker",
                "class",
            ]
        )
        for row in plan["hours"]:
            writer.writerow(
                [
                    plan["date"],
                    resolved["name"],
                    plan["start"],
                    plan["finish"],
                    plan["intensity"],
                    plan["crew"],
                    row["label"],
                    row["temp_c"],
                    row["rh"],
                    row["wind_ms"],
                    row["shortwave_wm2"],
                    row["wbgt"],
                    row["limit"],
                    row["work_min"],
                    row["rest_min"],
                    row["water_l"],
                    row["class"],
                ]
            )
        filename = f"shiftsafe-{plan['date']}-{resolved['name'].replace(' ', '-').lower()}.csv"
        return Response(
            content=buffer.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    if STATIC_DIR.is_dir():
        app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

    return app


app = create_app()