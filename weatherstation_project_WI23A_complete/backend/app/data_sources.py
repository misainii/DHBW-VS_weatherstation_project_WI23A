from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional, Tuple

from .aws_client import AWSGHCNClient
from .models import DailyObservation, Element, Station

logger = logging.getLogger(__name__)


class GHCNRepository:
    def __init__(self, use_aws_metadata: bool = True) -> None:
        self.sample_data_dir = Path("/app/data/sample")
        self._stations: List[Station] = []
        self._inventory = []
        self._aws_client = AWSGHCNClient()
        self.use_aws_metadata = use_aws_metadata
        self._load_metadata()

    def _load_metadata(self) -> None:
        stations_loaded = False
        inventory_loaded = False

        if self.use_aws_metadata:
            logger.info("Loading stations and inventory from AWS")
            stations_text = self._aws_client.fetch_stations_file()
            if stations_text:
                self._stations = self._parse_stations_text(stations_text)
                stations_loaded = True
                logger.info(f"Loaded {len(self._stations)} stations from AWS")
            else:
                logger.warning("Could not load stations from AWS, falling back to local files")

            inventory_text = self._aws_client.fetch_inventory_file()
            if inventory_text:
                self._inventory = self._parse_inventory_text(inventory_text)
                inventory_loaded = True
                logger.info(f"Loaded {len(self._inventory)} inventory records from AWS")
            else:
                logger.warning("Could not load inventory from AWS, falling back to local files")

        if not stations_loaded:
            stations_file = self.sample_data_dir / "ghcnd-stations.txt"
            if stations_file.exists():
                from .parsers import parse_stations_file
                self._stations = parse_stations_file(stations_file)
                logger.info(f"Loaded {len(self._stations)} stations from local file")
            else:
                logger.error("No local stations file found, station list will be empty")

        if not inventory_loaded:
            inventory_file = self.sample_data_dir / "ghcnd-inventory.txt"
            if inventory_file.exists():
                from .parsers import parse_inventory_file
                self._inventory = parse_inventory_file(inventory_file)
                logger.info(f"Loaded {len(self._inventory)} inventory records from local file")
            else:
                logger.error("No local inventory file found, inventory will be empty")

    def _parse_stations_text(self, text: str) -> List[Station]:
        stations = []
        for line in text.splitlines():
            line = line.rstrip("\n")
            if not line or len(line) < 41:
                continue
            try:
                station_id = line[0:11].strip()
                if not station_id:
                    continue
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
            except (ValueError, IndexError) as e:
                logger.debug(f"Skipping malformed station line: {e}")
                continue
        return stations

    def _parse_inventory_text(self, text: str) -> List:
        from .models import InventoryRecord, Element
        records = []
        for line in text.splitlines():
            line = line.rstrip("\n")
            if not line or len(line) < 45:
                continue
            try:
                station_id = line[0:11].strip()
                if not station_id:
                    continue
                element_name = line[31:35].strip()
                if element_name not in {"TMIN", "TMAX"}:
                    continue
                records.append(InventoryRecord(
                    station_id=station_id,
                    latitude=float(line[12:20].strip()),
                    longitude=float(line[21:30].strip()),
                    element=Element(element_name),
                    first_year=int(line[36:40].strip()),
                    last_year=int(line[41:45].strip()),
                ))
            except (ValueError, IndexError) as e:
                logger.debug(f"Skipping malformed inventory line: {e}")
                continue
        return records

    def load_stations(self) -> List[Station]:
        return self._stations

    def load_inventory(self) -> List:
        return self._inventory

    def load_station_observations(self, station_id: str, start: int, end: int) -> List[DailyObservation]:
        effective_start, effective_end = self._intersect_with_inventory(station_id, start, end)
        if effective_start is None or effective_end is None or effective_start > effective_end:
            logger.info(f"No overlapping inventory range for {station_id} in {start}-{end}")
            return []

        raw_rows = self._aws_client.get_station_period_data(station_id)
        if raw_rows:
            filtered = [row for row in raw_rows if effective_start <= row["year"] <= effective_end]
            logger.info(f"Found {len(filtered)} observations for {station_id} in {effective_start}-{effective_end}")
        else:
            logger.warning(f"Falling back to yearly files for {station_id}")
            filtered = []
            for year in range(effective_start, effective_end + 1):
                yearly_rows = self._aws_client.get_yearly_data(year)
                for row in yearly_rows:
                    if row["station_id"] == station_id:
                        filtered.append(row)

        observations = []
        for row in filtered:
            observations.append(
                DailyObservation(
                    station_id=row["station_id"],
                    date=row["date"],
                    year=row["year"],
                    month=row["month"],
                    day=row["day"],
                    element=Element(row["element"]),
                    value_c=row["value"],
                    qflag=row.get("qflag"),
                )
            )
        logger.info(f"Returning {len(observations)} observations for {station_id}")
        return observations

    def _intersect_with_inventory(self, station_id: str, start: int, end: int) -> Tuple[Optional[int], Optional[int]]:
        station_inventory = [inv for inv in self._inventory if inv.station_id == station_id]
        if not station_inventory:
            return start, end

        tmin_records = [inv for inv in station_inventory if inv.element == Element.TMIN]
        tmax_records = [inv for inv in station_inventory if inv.element == Element.TMAX]
        if not tmin_records or not tmax_records:
            return None, None

        first_year = max(
            min(rec.first_year for rec in tmin_records),
            min(rec.first_year for rec in tmax_records),
        )
        last_year = min(
            max(rec.last_year for rec in tmin_records),
            max(rec.last_year for rec in tmax_records),
        )

        return max(start, first_year), min(end, last_year)