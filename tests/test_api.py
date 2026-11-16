import csv
import io

import pytest
from fastapi.testclient import TestClient

from shiftsafe.app import create_app
from shiftsafe.providers import ForecastUnavailable

from conftest import make_payload

DATE = "2026-11-17"


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_place_search_finds_cherrybrook(client):
    body = client.get("/api/places", params={"q": "cherry"}).json()
    assert body["places"][0]["name"] == "Cherrybrook"
    assert body["places"][0]["state"] == "NSW"


def test_place_search_returns_everything_for_an_empty_query(client):
    body = client.get("/api/places").json()
    assert body["count"] == body["total"] >= 50


def test_unknown_place_is_404(client):
    response = client.get("/api/plan", params={"place": "atlantis"})
    assert response.status_code == 404
    assert "Unknown place" in response.json()["detail"]


def test_plan_happy_path(client):
    response = client.get("/api/plan", params={"place": "cherrybrook", "date": DATE})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["place"]["name"] == "Cherrybrook"
    assert body["date"] == DATE
    assert body["plan"]["start"] == "05:00"
    assert len(body["plan"]["hours"]) == 8
    assert body["data"]["mode"] == "live"
    assert body["available_dates"] == [DATE]


def test_plan_defaults_to_the_first_available_date(client):
    body = client.get("/api/plan", params={"place": "cherrybrook"}).json()
    assert body["date"] in body["available_dates"]


def test_bad_date_lists_available_dates(client):
    response = client.get("/api/plan", params={"place": "cherrybrook", "date": "2026-12-01"})
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["available_dates"] == [DATE]


def test_unknown_intensity_is_rejected(client):
    response = client.get(
        "/api/plan", params={"place": "cherrybrook", "date": DATE, "intensity": "sprint"}
    )
    assert response.status_code == 400
    assert "intensity" in response.json()["detail"]


def test_shift_that_runs_past_midnight_is_rejected(client):
    response = client.get(
        "/api/plan",
        params={"place": "cherrybrook", "date": DATE, "latest_start": 20, "shift_hours": 8},
    )
    assert response.status_code == 400
    assert "24:00" in response.json()["detail"]


def test_csv_export_has_one_row_per_hour(client):
    response = client.get("/api/plan.csv", params={"place": "cherrybrook", "date": DATE})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert len(rows) == 8
    assert rows[0]["hour"] == "05:00"
    assert "wbgt_c" in rows[0]


def test_csv_export_sets_a_filename(client):
    response = client.get("/api/plan.csv", params={"place": "cherrybrook", "date": DATE})
    assert "shiftsafe-2026-11-17-cherrybrook.csv" in response.headers["content-disposition"]


def test_second_request_is_served_from_cache(tmp_path):
    calls = {"count": 0}

    def counting_fetcher(lat, lon):
        calls["count"] += 1
        return make_payload()

    app = create_app(cache_path=tmp_path / "cache.db", fetcher=counting_fetcher)
    client = TestClient(app)
    first = client.get("/api/plan", params={"place": "cherrybrook", "date": DATE})
    second = client.get("/api/plan", params={"place": "cherrybrook", "date": DATE})
    assert first.status_code == 200 and second.status_code == 200
    assert calls["count"] == 1
    assert second.json()["data"]["mode"] == "cache"


def test_snapshot_is_used_when_the_api_is_down(snapshot_client):
    response = snapshot_client.get(
        "/api/plan", params={"place": "cherrybrook", "date": "2026-11-17"}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["data"]["mode"] == "snapshot"
    assert "not a current forecast" in body["data"]["note"]
    assert len(body["plan"]["hours"]) == 8


def test_far_away_point_has_no_snapshot(snapshot_client):
    response = snapshot_client.get(
        "/api/plan", params={"lat": -12.4634, "lon": 130.8456, "date": "2026-11-17"}
    )
    assert response.status_code == 503


def test_lat_lon_without_place_works(client):
    response = client.get(
        "/api/plan", params={"lat": -33.733, "lon": 151.05, "date": DATE, "crew": 2}
    )
    assert response.status_code == 200
    assert response.json()["place"]["name"] == "-33.733, 151.050"


def test_missing_location_is_rejected(client):
    response = client.get("/api/plan", params={"date": DATE})
    assert response.status_code == 400
    assert "place" in response.json()["detail"]


def test_meta_lists_the_three_intensities(client):
    body = client.get("/api/meta").json()
    assert [item["id"] for item in body["intensities"]] == ["light", "moderate", "heavy"]
    assert body["places"] >= 50


def test_index_page_is_served(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "shiftsafe" in response.text.lower()