"""Weather data for the planner.

Live data comes from the Open-Meteo forecast API. It is free and it needs no key.
When the API is unreachable, the app may use a bundled snapshot. The snapshot is a
real response for one point. The app uses it only near that point, and it says so.
"""

from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

from . import config

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SNAPSHOT_PATH = DATA_DIR / "sample_forecast.json"
API_URL = "https://api.open-meteo.com/v1/forecast"
FIELDS = "temperature_2m,relative_humidity_2m,wind_speed_10m,shortwave_radiation"


class ForecastUnavailable(RuntimeError):
    """Raised when no live or bundled forecast covers the request."""


def _clean(value, fallback=0.0):
    if value is None:
        return fallback
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def parse_payload(payload: dict) -> list[dict]:
    """Turn an Open-Meteo payload into one dict per hour."""
    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    temps = hourly.get("temperature_2m") or []
    rhs = hourly.get("relative_humidity_2m") or []
    winds = hourly.get("wind_speed_10m") or []
    solar = hourly.get("shortwave_radiation") or []

    rows = []
    for index, stamp in enumerate(times):
        rows.append(
            {
                "time": str(stamp)[:16],
                "temp_c": _clean(temps[index] if index < len(temps) else None, 20.0),
                "rh": _clean(rhs[index] if index < len(rhs) else None, 60.0),
                "wind_ms": _clean(winds[index] if index < len(winds) else None, 0.0),
                "solar": _clean(solar[index] if index < len(solar) else None, 0.0),
            }
        )
    return rows


def fetch_live(
    lat: float, lon: float, timeout: float = 8.0, tz: str = "Australia/Sydney"
) -> dict:
    """Fetch a live forecast. Raises ForecastUnavailable on any failure."""
    import urllib.parse
    import urllib.request

    query = urllib.parse.urlencode(
        {
            "latitude": f"{lat:.3f}",
            "longitude": f"{lon:.3f}",
            "hourly": FIELDS,
            "forecast_days": config.FORECAST_DAYS,
            "timezone": tz,
        }
    )
    url = f"{API_URL}?{query}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as error:  # network, DNS, TLS, JSON, timeout
        raise ForecastUnavailable(f"live forecast failed: {error}") from error


_snapshot_cache: dict | None = None


def load_snapshot() -> dict:
    """Load and memoise the bundled snapshot."""
    global _snapshot_cache
    if _snapshot_cache is None:
        with open(SNAPSHOT_PATH, "r", encoding="utf-8") as handle:
            _snapshot_cache = json.load(handle)
    return _snapshot_cache


def snapshot_meta(lat: float, lon: float) -> dict:
    """Describe the snapshot for this point, or raise if it is too far away."""
    snap = load_snapshot()
    forecast = snap["forecast"]
    dlat = abs(float(forecast["latitude"]) - lat)
    dlon = abs(float(forecast["longitude"]) - lon)
    if max(dlat, dlon) > config.SNAPSHOT_TOLERANCE_DEGREES:
        raise ForecastUnavailable("no bundled snapshot near this location")
    meta = snap.get("meta", {})
    return {
        "mode": "snapshot",
        "source": meta.get("source", "Open-Meteo"),
        "source_url": meta.get("source_url", API_URL),
        "fetched_at": meta.get("fetched_at"),
        "location": meta.get("location_label"),
        "note": (
            "Live weather is unreachable. This plan uses a bundled snapshot for "
            f"{meta.get('location_label', 'one point')}. It is not a current forecast."
        ),
    }


def get_forecast(
    lat: float,
    lon: float,
    cache: "Cache",
    ttl: int = config.CACHE_TTL_SECONDS,
    fetcher=fetch_live,
    tz: str = "Australia/Sydney",
) -> tuple[list[dict], dict]:
    """Return hourly rows and a data-description dict."""
    key = f"forecast:{lat:.3f}:{lon:.3f}:{tz}"
    cached = cache.get(key, ttl)
    if cached is not None:
        return parse_payload(cached), {
            "mode": "cache",
            "source": "Open-Meteo",
            "source_url": API_URL,
            "fetched_at": datetime.fromtimestamp(cache.age_of(key), tz=timezone.utc).isoformat(
                timespec="seconds"
            ),
            "note": "Cached forecast. It refreshes every 30 minutes.",
        }

    try:
        payload = fetcher(lat, lon)
    except ForecastUnavailable as error:
        snapshot = load_snapshot()
        meta = snapshot_meta(lat, lon)
        meta["reason"] = str(error)
        return parse_payload(snapshot["forecast"]), meta

    cache.set(key, payload)
    return parse_payload(payload), {
        "mode": "live",
        "source": "Open-Meteo",
        "source_url": API_URL,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "note": "Live forecast from the Open-Meteo API.",
    }


class Cache:
    """Small SQLite cache for forecast payloads."""

    def __init__(self, path: str | Path | None = None):
        self.path = str(path or (DATA_DIR / "cache.db"))
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.execute(
            "create table if not exists cache (key text primary key, body text not null, "
            "fetched_at real not null)"
        )
        return connection

    def _init(self) -> None:
        with self._connect() as connection:
            connection.commit()

    def get(self, key: str, ttl: int) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                "select body, fetched_at from cache where key = ?", (key,)
            ).fetchone()
        if row is None:
            return None
        if ttl and (time.time() - float(row[1])) > ttl:
            return None
        try:
            return json.loads(row[0])
        except json.JSONDecodeError:
            return None

    def set(self, key: str, payload: dict) -> None:
        with self._connect() as connection:
            connection.execute(
                "insert into cache (key, body, fetched_at) values (?, ?, ?) "
                "on conflict(key) do update set body = excluded.body, "
                "fetched_at = excluded.fetched_at",
                (key, json.dumps(payload), time.time()),
            )
            connection.commit()

    def age_of(self, key: str) -> float:
        with self._connect() as connection:
            row = connection.execute(
                "select fetched_at from cache where key = ?", (key,)
            ).fetchone()
        return float(row[0]) if row else time.time()