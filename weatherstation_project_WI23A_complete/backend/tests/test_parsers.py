from pathlib import Path

from app.models import Element
from app.parsers import parse_by_station_csv, parse_inventory_file, parse_stations_file


def _station_line(
    station_id: str,
    latitude: float,
    longitude: float,
    elevation: float | None,
    state: str,
    name: str,
) -> str:
    elevation_field = "-999.9" if elevation is None else f"{elevation:6.1f}"
    return (
        f"{station_id:<11} "
        f"{latitude:8.4f} "
        f"{longitude:9.4f} "
        f"{elevation_field:>6} "
        f"{state:<2} "
        f"{name:<30}"
    )


def _inventory_line(
    station_id: str,
    latitude: float,
    longitude: float,
    element: str,
    first_year: int,
    last_year: int,
) -> str:
    return (
        f"{station_id:<11} "
        f"{latitude:8.4f} "
        f"{longitude:9.4f} "
        f"{element:<4} "
        f"{first_year:4d} "
        f"{last_year:4d}"
    )


def test_parse_stations_file_reads_valid_rows_and_normalizes_missing_elevation(tmp_path: Path):
    station_file = tmp_path / "stations.txt"
    station_file.write_text(
        "\n".join(
            [
                _station_line("GME00102380", 49.4521, 11.0767, 314.0, "BY", "NUERNBERG"),
                _station_line("GME00102381", 49.4771, 10.9887, None, "BY", "FUERTH"),
                "broken row",
            ]
        ),
        encoding="utf-8",
    )

    stations = parse_stations_file(station_file)

    assert [station.station_id for station in stations] == ["GME00102380", "GME00102381"]
    assert stations[0].elevation_m == 314.0
    assert stations[0].state == "BY"
    assert stations[1].elevation_m is None


def test_parse_inventory_file_filters_to_temperature_elements(tmp_path: Path):
    inventory_file = tmp_path / "inventory.txt"
    inventory_file.write_text(
        "\n".join(
            [
                _inventory_line("GME00102380", 49.4521, 11.0767, "TMIN", 1940, 2025),
                _inventory_line("GME00102380", 49.4521, 11.0767, "TMAX", 1945, 2024),
                _inventory_line("GME00102380", 49.4521, 11.0767, "PRCP", 1940, 2025),
                "broken row",
            ]
        ),
        encoding="utf-8",
    )

    records = parse_inventory_file(inventory_file)

    assert len(records) == 2
    assert records[0].element == Element.TMIN
    assert records[1].element == Element.TMAX
    assert records[1].first_year == 1945
    assert records[1].last_year == 2024


def test_parse_by_station_csv_skips_flagged_missing_and_non_temperature_rows(tmp_path: Path):
    csv_file = tmp_path / "station.csv"
    csv_file.write_text(
        "\n".join(
            [
                "GME00102380,20200101,TMIN,15,,,",
                "GME00102380,20200101,TMAX,35,,X,",
                "GME00102380,20200102,TMAX,-9999,,,",
                "GME00102380,20200103,PRCP,99,,,",
                "malformed",
            ]
        ),
        encoding="utf-8",
    )

    observations = parse_by_station_csv(csv_file)

    assert len(observations) == 1
    assert observations[0].station_id == "GME00102380"
    assert observations[0].element == Element.TMIN
    assert observations[0].date == "2020-01-01"
    assert observations[0].value_c == 1.5
