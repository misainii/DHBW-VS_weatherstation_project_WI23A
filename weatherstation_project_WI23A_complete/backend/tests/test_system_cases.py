import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)
pytestmark = [pytest.mark.integration, pytest.mark.slow]


def test_system_case_nuremberg():
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
    data = response.json()
    assert response.status_code == 200
    assert data["stations"]
    assert "N" in data["stations"][0]["name"]
    assert data["stations"][0]["distance_km"] <= 60


def test_system_case_stuttgart():
    response = client.get(
        "/api/stations",
        params={
            "latitude": 48.7758,
            "longitude": 9.1829,
            "radius_km": 100,
            "limit": 3,
            "start_year": 1990,
            "end_year": 2025,
        },
    )
    data = response.json()
    assert response.status_code == 200
    assert data["stations"]
    assert "STUTTGART" in data["stations"][0]["name"]
    assert data["stations"][0]["distance_km"] <= 100


def test_system_case_hamburg():
    response = client.get(
        "/api/stations",
        params={
            "latitude": 53.5511,
            "longitude": 9.9937,
            "radius_km": 120,
            "limit": 3,
            "start_year": 1995,
            "end_year": 2025,
        },
    )
    data = response.json()
    assert response.status_code == 200
    assert data["stations"]
    assert "HAMBURG" in data["stations"][0]["name"]
    assert data["stations"][0]["distance_km"] <= 120
