from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_meta():
    response = client.get("/api/meta")
    assert response.status_code == 200
    payload = response.json()
    assert payload["latest_end_year"] == 2025


def test_search_endpoint():
    response = client.get(
        "/api/stations",
        params={
            "latitude": 49.4521,
            "longitude": 11.0767,
            "radius_km": 60,
            "limit": 3,
            "start_year": 1985,
            "end_year": 2025,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["stations"][0]["station_id"] == "GME00102380"


def test_climate_endpoint():
    response = client.get(
        "/api/stations/GME00102380/climate",
        params={"start_year": 2020, "end_year": 2025},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["station"]["station_id"] == "GME00102380"
    assert len(payload["table"]) == 6
    assert len(payload["annual_series"]) == 2
