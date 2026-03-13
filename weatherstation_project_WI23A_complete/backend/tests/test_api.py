import pytest
from fastapi.testclient import TestClient

from app.main import app
import app.main as main_module
from app.models import Station


client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.integration
def test_meta():
    response = client.get("/api/meta")
    assert response.status_code == 200
    payload = response.json()
    assert payload["latest_end_year"] >= payload["earliest_start_year"]
    assert payload["source_mode"]


@pytest.mark.integration
@pytest.mark.slow
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


@pytest.mark.unit
def test_search_endpoint_rejects_invalid_latitude():
    response = client.get(
        "/api/stations",
        params={
            "latitude": 91,
            "longitude": 11.0767,
            "radius_km": 60,
            "limit": 3,
            "start_year": 1985,
            "end_year": 2025,
        },
    )

    assert response.status_code == 400
    assert "latitude" in response.json()["detail"]


@pytest.mark.unit
def test_search_endpoint_rejects_inverted_year_range():
    response = client.get(
        "/api/stations",
        params={
            "latitude": 49.4521,
            "longitude": 11.0767,
            "radius_km": 60,
            "limit": 3,
            "start_year": 2025,
            "end_year": 1985,
        },
    )

    assert response.status_code == 400
    assert "start_year" in response.json()["detail"]


@pytest.mark.unit
def test_search_endpoint_rejects_invalid_longitude():
    response = client.get(
        "/api/stations",
        params={
            "latitude": 49.4521,
            "longitude": 181,
            "radius_km": 60,
            "limit": 3,
            "start_year": 1985,
            "end_year": 2025,
        },
    )

    assert response.status_code == 400
    assert "longitude" in response.json()["detail"]


@pytest.mark.unit
def test_search_endpoint_rejects_invalid_limit_via_query_validation():
    response = client.get(
        "/api/stations",
        params={
            "latitude": 49.4521,
            "longitude": 11.0767,
            "radius_km": 60,
            "limit": 0,
            "start_year": 1985,
            "end_year": 2025,
        },
    )

    assert response.status_code == 422


@pytest.mark.unit
def test_search_endpoint_rejects_non_positive_radius_via_query_validation():
    response = client.get(
        "/api/stations",
        params={
            "latitude": 49.4521,
            "longitude": 11.0767,
            "radius_km": 0,
            "limit": 3,
            "start_year": 1985,
            "end_year": 2025,
        },
    )

    assert response.status_code == 422


@pytest.mark.integration
@pytest.mark.slow
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


@pytest.mark.unit
def test_climate_endpoint_adjusts_requested_period_to_available_range(monkeypatch):
    station = Station(
        station_id="GME00102380",
        name="NUERNBERG",
        latitude=49.4521,
        longitude=11.0767,
        elevation_m=314.0,
    )

    monkeypatch.setattr(
        main_module.service,
        "get_station_years_range",
        lambda station_id: {"first_year": 1940, "last_year": 2020},
    )
    monkeypatch.setattr(
        main_module.service,
        "get_climate_summary",
        lambda station_id, start_year, end_year: {
            "station": station,
            "data_gap_warning": False,
            "missing_years": [],
            "expected_years": end_year - start_year + 1,
            "annual_series": [],
            "seasonal_series": [],
            "table": [{"year": year} for year in range(start_year, end_year + 1)],
        },
    )

    response = client.get(
        "/api/stations/GME00102380/climate",
        params={"start_year": 1930, "end_year": 2025},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["requested_period"] == {"start_year": 1930, "end_year": 2025, "adjusted": True}
    assert payload["actual_period"] == {"start_year": 1940, "end_year": 2020}


@pytest.mark.unit
def test_climate_endpoint_returns_400_when_adjusted_range_has_no_overlap(monkeypatch):
    monkeypatch.setattr(
        main_module.service,
        "get_station_years_range",
        lambda station_id: {"first_year": 1940, "last_year": 1950},
    )

    response = client.get(
        "/api/stations/GME00102380/climate",
        params={"start_year": 1960, "end_year": 1970},
    )

    assert response.status_code == 400
    assert "no available data" in response.json()["detail"]


@pytest.mark.integration
def test_climate_endpoint_returns_400_for_unknown_station():
    response = client.get(
        "/api/stations/UNKNOWN-STATION/climate",
        params={"start_year": 2020, "end_year": 2025, "adjust_to_available": "false"},
    )

    assert response.status_code == 400
    assert "not found" in response.json()["detail"]


@pytest.mark.unit
def test_search_endpoint_rejects_limit_above_maximum_via_query_validation():
    response = client.get(
        "/api/stations",
        params={
            "latitude": 49.4521,
            "longitude": 11.0767,
            "radius_km": 60,
            "limit": 21,
            "start_year": 1985,
            "end_year": 2025,
        },
    )

    assert response.status_code == 422


@pytest.mark.unit
def test_meta_endpoint_returns_500_when_service_fails(monkeypatch):
    monkeypatch.setattr(
        main_module.service,
        "get_meta",
        lambda: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    response = client.get("/api/meta")

    assert response.status_code == 500
    assert response.json()["detail"] == "boom"


@pytest.mark.unit
def test_search_endpoint_returns_500_when_service_fails(monkeypatch):
    monkeypatch.setattr(
        main_module.service,
        "search_stations",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("search failed")),
    )

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

    assert response.status_code == 500
    assert response.json()["detail"] == "search failed"


@pytest.mark.unit
def test_climate_endpoint_does_not_adjust_period_when_disabled(monkeypatch):
    station = Station(
        station_id="GME00102380",
        name="NUERNBERG",
        latitude=49.4521,
        longitude=11.0767,
        elevation_m=314.0,
    )
    recorded = {}

    monkeypatch.setattr(
        main_module.service,
        "get_station_years_range",
        lambda station_id: {"first_year": 1940, "last_year": 2020},
    )

    def fake_summary(station_id, start_year, end_year):
        recorded["start_year"] = start_year
        recorded["end_year"] = end_year
        return {
            "station": station,
            "data_gap_warning": False,
            "missing_years": [],
            "expected_years": end_year - start_year + 1,
            "annual_series": [],
            "seasonal_series": [],
            "table": [{"year": year} for year in range(start_year, end_year + 1)],
        }

    monkeypatch.setattr(main_module.service, "get_climate_summary", fake_summary)

    response = client.get(
        "/api/stations/GME00102380/climate",
        params={"start_year": 1930, "end_year": 2025, "adjust_to_available": "false"},
    )

    assert response.status_code == 200
    assert recorded == {"start_year": 1930, "end_year": 2025}
    payload = response.json()
    assert payload["requested_period"]["adjusted"] is False
    assert payload["actual_period"] == {"start_year": 1930, "end_year": 2025}
