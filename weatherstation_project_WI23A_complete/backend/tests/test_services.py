from app.services import WeatherstationService


def test_meta_range():
    service = WeatherstationService()
    meta = service.get_meta()
    assert meta["earliest_start_year"] <= 1920
    assert meta["latest_end_year"] == 2025


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
    assert [row.station_id for row in result][:2] == ["GME00120003", "GME00120004"]


def test_climate_summary_contains_table_and_gap_information():
    service = WeatherstationService()
    summary = service.get_climate_summary("GME00102380", 1940, 1942)
    assert len(summary["table"]) == 3
    assert summary["data_gap_warning"] is True
    assert summary["missing_months"] > 0
    first_row = summary["table"][0]
    assert first_row.annual_tmin is not None
    assert first_row.spring_tmax is not None
