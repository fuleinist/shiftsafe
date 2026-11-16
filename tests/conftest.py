import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shiftsafe.app import create_app  # noqa: E402
from shiftsafe.providers import ForecastUnavailable  # noqa: E402

DATE = "2026-11-17"


def make_payload(date=DATE, hot_afternoon=True):
    """Synthetic hourly payload. Cool morning, hot afternoon."""
    temps = []
    rhs = []
    winds = []
    solar = []
    for hour in range(24):
        if hot_afternoon:
            temp = 17.0 + (hour - 5) * 1.0 if 5 <= hour <= 15 else (34.0 if 15 < hour < 18 else 19.0)
        else:
            temp = 22.0
        temps.append(round(temp, 1))
        rhs.append(70 if hour < 9 else 38)
        winds.append(2.5)
        solar.append(0.0 if hour < 6 or hour > 19 else float(min(950, (hour - 6) * 150)))
    times = [f"{date}T{hour:02d}:00" for hour in range(24)]
    return {
        "latitude": -33.733,
        "longitude": 151.05,
        "timezone": "Australia/Sydney",
        "hourly_units": {"time": "iso8601", "temperature_2m": "°C"},
        "hourly": {
            "time": times,
            "temperature_2m": temps,
            "relative_humidity_2m": rhs,
            "wind_speed_10m": winds,
            "shortwave_radiation": solar,
        },
    }


def failing_fetcher(lat, lon):
    raise ForecastUnavailable("no network in the test harness")


@pytest.fixture
def client(tmp_path):
    app = create_app(cache_path=tmp_path / "cache.db", fetcher=lambda lat, lon: make_payload())
    return TestClient(app)


@pytest.fixture
def snapshot_client(tmp_path):
    app = create_app(cache_path=tmp_path / "cache.db", fetcher=failing_fetcher)
    return TestClient(app)