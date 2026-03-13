import pytest

from app.services import WeatherstationService
from app.models import DailyObservation, Element


@pytest.mark.integration
def test_meta_range():
    service = WeatherstationService()
    meta = service.get_meta()
    assert meta["earliest_start_year"] <= 1920
    assert meta["latest_end_year"] >= 2025


@pytest.mark.integration
@pytest.mark.slow
def test_station_search_returns_nearest_nuremberg_matches():
    service = WeatherstationService()
    result = service.search_stations(
        latitude=49.4521,
        longitude=11.0767,
        radius_km=60,
        limit=3,
        start_year=1985,
        end_year=2025,
    )
    assert result
    assert result[0].station_id == "GME00102380"
    assert len(result) == 3


@pytest.mark.integration
@pytest.mark.slow
def test_station_search_filters_year_range():
    service = WeatherstationService()
    result = service.search_stations(
        latitude=53.5511,
        longitude=9.9937,
        radius_km=120,
        limit=5,
        start_year=1995,
        end_year=2025,
    )
    assert result
    assert all(row.distance_km <= 120 for row in result)
    assert all(row.last_year >= 1995 for row in result)
    assert all(row.first_year <= 2025 for row in result)


@pytest.mark.integration
@pytest.mark.slow
def test_climate_summary_contains_table_and_gap_information():
    service = WeatherstationService()
    summary = service.get_climate_summary("GME00102380", 1940, 1942)
    assert len(summary["table"]) == 3
    assert summary["data_gap_warning"] is True
    assert summary["missing_years"]
    first_row = summary["table"][0]
    assert isinstance(first_row["year"], int)
    assert "station" in summary


@pytest.mark.unit
def test_get_days_in_month_handles_leap_years():
    service = WeatherstationService()

    assert service._get_days_in_month(2024, 2) == 29
    assert service._get_days_in_month(2023, 2) == 28
    assert service._get_days_in_month(2023, 4) == 30
    assert service._get_days_in_month(2023, 1) == 31


@pytest.mark.unit
def test_calculate_monthly_averages_requires_complete_month():
    service = WeatherstationService()
    observations = [
        DailyObservation(
            station_id="GME00102380",
            date=f"2020-01-{day:02d}",
            year=2020,
            month=1,
            day=day,
            element=Element.TMIN,
            value_c=1.0,
        )
        for day in range(1, 32)
    ]
    observations.extend(
        DailyObservation(
            station_id="GME00102380",
            date=f"2020-02-{day:02d}",
            year=2020,
            month=2,
            day=day,
            element=Element.TMAX,
            value_c=5.0,
        )
        for day in range(1, 28)
    )

    monthly = service._calculate_monthly_averages(observations)

    assert monthly[(2020, 1)]["TMIN"] == 1.0
    assert (2020, 2) not in monthly


@pytest.mark.unit
def test_calculate_seasonal_averages_handles_northern_winter_across_year_boundary():
    service = WeatherstationService()
    monthly = {
        (2020, 12): {"TMIN": 1.0, "TMAX": 5.0},
        (2021, 1): {"TMIN": 2.0, "TMAX": 6.0},
        (2021, 2): {"TMIN": 3.0, "TMAX": 7.0},
    }

    seasonal = service._calculate_seasonal_averages(monthly, 2020, 2020, 49.0)

    winter_rows = [row for row in seasonal if row["season"] == "winter"]
    assert {"year": 2020, "season": "winter", "winter_tmin": 2.0} in winter_rows
    assert {"year": 2020, "season": "winter", "winter_tmax": 6.0} in winter_rows


@pytest.mark.unit
def test_calculate_seasonal_averages_uses_southern_hemisphere_seasons():
    service = WeatherstationService()
    monthly = {
        (2020, 12): {"TMIN": 10.0},
        (2021, 1): {"TMIN": 11.0},
        (2021, 2): {"TMIN": 12.0},
        (2020, 6): {"TMAX": 4.0},
        (2020, 7): {"TMAX": 5.0},
        (2020, 8): {"TMAX": 6.0},
    }

    seasonal = service._calculate_seasonal_averages(monthly, 2020, 2020, -33.0)

    assert {"year": 2020, "season": "summer", "summer_tmin": 11.0} in seasonal
    assert {"year": 2020, "season": "winter", "winter_tmax": 5.0} in seasonal


@pytest.mark.integration
def test_get_station_years_range_returns_none_for_unknown_station():
    service = WeatherstationService()

    assert service.get_station_years_range("UNKNOWN") is None


@pytest.mark.unit
def test_get_station_years_range_returns_none_without_both_temperature_series(monkeypatch):
    service = WeatherstationService()
    monkeypatch.setattr(
        service.repo,
        "load_inventory",
        lambda: [
            type("Rec", (), {
                "station_id": "GME00102380",
                "element": Element.TMIN,
                "first_year": 1940,
                "last_year": 2025,
            })()
        ],
    )

    assert service.get_station_years_range("GME00102380") is None


@pytest.mark.unit
def test_get_station_years_range_returns_common_range(monkeypatch):
    service = WeatherstationService()
    monkeypatch.setattr(
        service.repo,
        "load_inventory",
        lambda: [
            type("Rec", (), {
                "station_id": "GME00102380",
                "element": Element.TMIN,
                "first_year": 1940,
                "last_year": 2025,
            })(),
            type("Rec", (), {
                "station_id": "GME00102380",
                "element": Element.TMAX,
                "first_year": 1950,
                "last_year": 2020,
            })(),
        ],
    )

    years = service.get_station_years_range("GME00102380")

    assert years == {"first_year": 1950, "last_year": 2020}


@pytest.mark.unit
def test_get_climate_summary_returns_empty_series_when_no_observations(monkeypatch):
    service = WeatherstationService()
    station = type("StationObj", (), {
        "station_id": "GME00102380",
        "name": "NUERNBERG",
        "latitude": 49.4521,
        "longitude": 11.0767,
        "elevation_m": 314.0,
    })()
    monkeypatch.setattr(service.repo, "load_stations", lambda: [station])
    monkeypatch.setattr(service.repo, "load_station_observations", lambda station_id, start, end: [])

    summary = service.get_climate_summary("GME00102380", 2000, 2002)

    assert summary["data_gap_warning"] is True
    assert summary["missing_years"] == [2000, 2001, 2002]
    assert summary["annual_series"] == []
    assert summary["seasonal_series"] == []
    assert summary["table"] == [{"year": 2000}, {"year": 2001}, {"year": 2002}]


@pytest.mark.unit
def test_get_climate_summary_raises_for_unknown_station(monkeypatch):
    service = WeatherstationService()
    monkeypatch.setattr(service.repo, "load_stations", lambda: [])

    try:
        service.get_climate_summary("UNKNOWN", 2000, 2002)
    except ValueError as exc:
        assert "not found" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unknown station")
