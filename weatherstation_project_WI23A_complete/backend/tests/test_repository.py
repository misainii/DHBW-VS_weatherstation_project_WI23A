from types import SimpleNamespace
from pathlib import Path

from app.data_sources import GHCNRepository
from app.models import Element, InventoryRecord


def _repo_with_inventory(inventory):
    repo = GHCNRepository.__new__(GHCNRepository)
    repo._inventory = inventory
    return repo


def test_intersect_with_inventory_returns_requested_range_without_metadata():
    repo = _repo_with_inventory([])

    assert repo._intersect_with_inventory("GME00102380", 1990, 2000) == (1990, 2000)


def test_intersect_with_inventory_returns_none_when_one_temperature_series_is_missing():
    repo = _repo_with_inventory(
        [
            InventoryRecord(
                station_id="GME00102380",
                latitude=49.45,
                longitude=11.07,
                element=Element.TMIN,
                first_year=1940,
                last_year=2025,
            )
        ]
    )

    assert repo._intersect_with_inventory("GME00102380", 1990, 2000) == (None, None)


def test_intersect_with_inventory_uses_common_tmin_tmax_range():
    repo = _repo_with_inventory(
        [
            InventoryRecord(
                station_id="GME00102380",
                latitude=49.45,
                longitude=11.07,
                element=Element.TMIN,
                first_year=1940,
                last_year=2025,
            ),
            InventoryRecord(
                station_id="GME00102380",
                latitude=49.45,
                longitude=11.07,
                element=Element.TMAX,
                first_year=1950,
                last_year=2020,
            ),
        ]
    )

    assert repo._intersect_with_inventory("GME00102380", 1945, 2022) == (1950, 2020)


def test_load_station_observations_filters_by_effective_range():
    repo = _repo_with_inventory(
        [
            InventoryRecord(
                station_id="GME00102380",
                latitude=49.45,
                longitude=11.07,
                element=Element.TMIN,
                first_year=1940,
                last_year=2025,
            ),
            InventoryRecord(
                station_id="GME00102380",
                latitude=49.45,
                longitude=11.07,
                element=Element.TMAX,
                first_year=1940,
                last_year=2025,
            ),
        ]
    )
    repo._aws_client = SimpleNamespace(
        get_station_period_data=lambda _station_id: [
            {"station_id": "GME00102380", "date": "1999-01-01", "year": 1999, "month": 1, "day": 1, "element": "TMIN", "value": 1.0},
            {"station_id": "GME00102380", "date": "2000-01-01", "year": 2000, "month": 1, "day": 1, "element": "TMIN", "value": 2.0},
            {"station_id": "GME00102380", "date": "2001-01-01", "year": 2001, "month": 1, "day": 1, "element": "TMAX", "value": 3.0},
        ],
        get_yearly_data=lambda _year: [],
    )

    observations = repo.load_station_observations("GME00102380", 2000, 2000)

    assert len(observations) == 1
    assert observations[0].year == 2000
    assert observations[0].value_c == 2.0


def test_load_station_observations_uses_yearly_fallback_when_station_file_is_missing():
    repo = _repo_with_inventory(
        [
            InventoryRecord(
                station_id="GME00102380",
                latitude=49.45,
                longitude=11.07,
                element=Element.TMIN,
                first_year=1940,
                last_year=2025,
            ),
            InventoryRecord(
                station_id="GME00102380",
                latitude=49.45,
                longitude=11.07,
                element=Element.TMAX,
                first_year=1940,
                last_year=2025,
            ),
        ]
    )
    repo._aws_client = SimpleNamespace(
        get_station_period_data=lambda _station_id: [],
        get_yearly_data=lambda year: [
            {"station_id": "OTHER", "date": f"{year}-01-01", "year": year, "month": 1, "day": 1, "element": "TMIN", "value": 1.0},
            {"station_id": "GME00102380", "date": f"{year}-02-01", "year": year, "month": 2, "day": 1, "element": "TMAX", "value": 4.0},
        ],
    )

    observations = repo.load_station_observations("GME00102380", 2001, 2002)

    assert [obs.year for obs in observations] == [2001, 2002]
    assert all(obs.station_id == "GME00102380" for obs in observations)


def test_parse_stations_text_skips_malformed_rows():
    repo = GHCNRepository.__new__(GHCNRepository)
    text = "\n".join(
        [
            "GME00102380  49.4521   11.0767  314.0 BY NUERNBERG                    ",
            "broken",
            "           49.4521   11.0767  314.0 BY MISSING_ID                    ",
        ]
    )

    stations = repo._parse_stations_text(text)

    assert len(stations) == 1
    assert stations[0].station_id == "GME00102380"


def test_parse_inventory_text_skips_non_temperature_and_malformed_rows():
    repo = GHCNRepository.__new__(GHCNRepository)
    text = "\n".join(
        [
            "GME00102380  49.4521   11.0767 TMIN 1940 2025",
            "GME00102380  49.4521   11.0767 PRCP 1940 2025",
            "broken",
        ]
    )

    records = repo._parse_inventory_text(text)

    assert len(records) == 1
    assert records[0].element == Element.TMIN


def test_load_metadata_falls_back_to_local_files(monkeypatch, tmp_path: Path):
    stations_file = tmp_path / "ghcnd-stations.txt"
    inventory_file = tmp_path / "ghcnd-inventory.txt"
    stations_file.write_text("station-data", encoding="utf-8")
    inventory_file.write_text("inventory-data", encoding="utf-8")

    repo = GHCNRepository.__new__(GHCNRepository)
    repo.sample_data_dir = tmp_path
    repo._stations = []
    repo._inventory = []
    repo.use_aws_metadata = True
    repo._aws_client = SimpleNamespace(
        fetch_stations_file=lambda: None,
        fetch_inventory_file=lambda: None,
    )

    monkeypatch.setattr(
        "app.parsers.parse_stations_file",
        lambda path: ["local-stations"] if path == stations_file else [],
    )
    monkeypatch.setattr(
        "app.parsers.parse_inventory_file",
        lambda path: ["local-inventory"] if path == inventory_file else [],
    )

    repo._load_metadata()

    assert repo._stations == ["local-stations"]
    assert repo._inventory == ["local-inventory"]


def test_load_metadata_uses_aws_metadata_when_available(tmp_path: Path):
    repo = GHCNRepository.__new__(GHCNRepository)
    repo.sample_data_dir = tmp_path
    repo._stations = []
    repo._inventory = []
    repo.use_aws_metadata = True
    repo._aws_client = SimpleNamespace(
        fetch_stations_file=lambda: "stations-text",
        fetch_inventory_file=lambda: "inventory-text",
    )
    repo._parse_stations_text = lambda text: ["aws-stations"] if text == "stations-text" else []
    repo._parse_inventory_text = lambda text: ["aws-inventory"] if text == "inventory-text" else []

    repo._load_metadata()

    assert repo._stations == ["aws-stations"]
    assert repo._inventory == ["aws-inventory"]
