from __future__ import annotations

import csv
import logging
from pathlib import Path

from .models import DailyObservation, Element, InventoryRecord, Station

logger = logging.getLogger(__name__)


def parse_stations_file(path: Path) -> list[Station]:
    stations = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    station_id = line[0:11].strip()
                    latitude = float(line[12:20].strip())
                    longitude = float(line[21:30].strip())
                    elevation_raw = line[31:37].strip()
                    elevation = None if not elevation_raw or elevation_raw == "-999.9" else float(elevation_raw)
                    state = line[38:40].strip() or None
                    name = line[41:71].strip()
                    
                    stations.append(Station(
                        station_id=station_id,
                        name=name,
                        latitude=latitude,
                        longitude=longitude,
                        elevation_m=elevation,
                        state=state,
                    ))
                except:
                    continue
    except Exception as e:
        logger.error(f"Fehler beim Lesen der Stationsdatei: {e}")
    return stations


def parse_inventory_file(path: Path) -> list[InventoryRecord]:
    records = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    element_name = line[31:35].strip()
                    if element_name not in {"TMIN", "TMAX"}:
                        continue
                    
                    records.append(InventoryRecord(
                        station_id=line[0:11].strip(),
                        latitude=float(line[12:20].strip()),
                        longitude=float(line[21:30].strip()),
                        element=Element(element_name),
                        first_year=int(line[36:40].strip()),
                        last_year=int(line[41:45].strip()),
                    ))
                except:
                    continue
    except Exception as e:
        logger.error(f"Fehler beim Lesen der Inventory-Datei: {e}")
    return records


def parse_by_station_csv(path: Path) -> list[DailyObservation]:
    observations = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            for row in reader:
                if not row or len(row) < 7:
                    continue
                try:
                    station_id, date_str, element_name, raw_value, _mflag, qflag, _sflag, *_ = row
                    
                    if element_name not in {"TMIN", "TMAX"}:
                        continue
                    if raw_value in {"", "-9999"}:
                        continue
                    if qflag and qflag.strip():
                        continue
                    
                    year = int(date_str[0:4])
                    month = int(date_str[4:6])
                    day = int(date_str[6:8])
                    
                    observations.append(DailyObservation(
                        station_id=station_id,
                        date=f"{year:04d}-{month:02d}-{day:02d}",
                        year=year,
                        month=month,
                        day=day,
                        element=Element(element_name),
                        value_c=int(raw_value) / 10.0,
                        qflag=qflag or None,
                    ))
                except:
                    continue
    except Exception as e:
        logger.error(f"Fehler beim Lesen der CSV-Datei: {e}")
    return observations