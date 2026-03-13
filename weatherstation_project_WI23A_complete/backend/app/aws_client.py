from __future__ import annotations

import csv
import gzip
import io
import logging
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class AWSGHCNClient:
    """Lädt GHCN-Daten vom öffentlichen NOAA‑AWS‑Bucket."""

    BASE_URL = "https://noaa-ghcn-pds.s3.amazonaws.com"
    STATIONS_PATH = "/ghcnd-stations.txt"
    INVENTORY_PATH = "/ghcnd-inventory.txt"
    BY_STATION_PATH = "/csv/by_station/{station_id}.csv"
    YEARLY_PATH = "/csv/{year}.csv"

    def __init__(self, timeout: int = 60, max_retries: int = 3) -> None:
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "Weatherstation-Explorer/1.0"})
        self.timeout = timeout
        self.max_retries = max_retries
        self._station_cache: Dict[str, List[Dict[str, Any]]] = {}

    def _fetch_bytes(self, url: str) -> Optional[bytes]:
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug(f"Fetching {url} (attempt {attempt})")
                resp = self._session.get(url, timeout=self.timeout)
                if resp.status_code == 404:
                    logger.debug(f"URL not found: {url}")
                    return None
                resp.raise_for_status()
                return resp.content
            except requests.RequestException as e:
                logger.warning(f"Attempt {attempt} failed for {url}: {e}")
                if attempt == self.max_retries:
                    logger.error(f"All attempts failed for {url}")
                    return None
        return None

    def _parse_csv_bytes(self, data: bytes, url: str) -> List[Dict[str, Any]]:
        if data[:2] == b'\x1f\x8b':
            try:
                data = gzip.decompress(data)
            except Exception as e:
                logger.error(f"Failed to decompress gzip from {url}: {e}")
                return []

        text = data.decode("utf-8", errors="ignore")
        reader = csv.reader(io.StringIO(text))
        rows = []
        for line_num, parts in enumerate(reader, start=1):
            if not parts:
                continue
            try:
                station_id = parts[0].strip()
                date_str = parts[1].strip()
                element = parts[2].strip()
                value_str = parts[3].strip()
                qflag = parts[5].strip() if len(parts) > 5 else ""

                if element not in ("TMIN", "TMAX"):
                    continue
                if value_str in ("", "-9999"):
                    continue
                if qflag:
                    continue

                year = int(date_str[0:4])
                month = int(date_str[4:6])
                day = int(date_str[6:8])
                value_c = int(value_str) / 10.0

                rows.append({
                    "station_id": station_id,
                    "date": date_str,
                    "year": year,
                    "month": month,
                    "day": day,
                    "element": element,
                    "value": value_c,
                    "qflag": qflag or None,
                })
            except (ValueError, IndexError) as e:
                logger.debug(f"Skipping malformed line {line_num} in {url}: {e}")
                continue
        return rows

    def fetch_stations_file(self) -> Optional[str]:
        url = self.BASE_URL + self.STATIONS_PATH
        data = self._fetch_bytes(url)
        return data.decode("utf-8", errors="ignore") if data else None

    def fetch_inventory_file(self) -> Optional[str]:
        url = self.BASE_URL + self.INVENTORY_PATH
        data = self._fetch_bytes(url)
        return data.decode("utf-8", errors="ignore") if data else None

    def get_station_period_data(self, station_id: str) -> List[Dict[str, Any]]:
        if station_id in self._station_cache:
            return self._station_cache[station_id]

        url = self.BASE_URL + self.BY_STATION_PATH.format(station_id=station_id)
        data = self._fetch_bytes(url)
        if data is None:
            logger.info(f"No by_station file for {station_id}, will use yearly fallback")
            self._station_cache[station_id] = []
            return []

        rows = self._parse_csv_bytes(data, url)
        self._station_cache[station_id] = rows
        logger.info(f"Loaded {len(rows)} observations for {station_id} from {url}")
        return rows

    def get_yearly_data(self, year: int) -> List[Dict[str, Any]]:
        url = self.BASE_URL + self.YEARLY_PATH.format(year=year)
        data = self._fetch_bytes(url)
        if data is None:
            return []
        return self._parse_csv_bytes(data, url)

    def get_station_data(self, station_id: str, year: int) -> List[Dict[str, Any]]:
        period_data = self.get_station_period_data(station_id)
        if period_data:
            return [row for row in period_data if row["year"] == year]
        yearly_data = self.get_yearly_data(year)
        return [row for row in yearly_data if row["station_id"] == station_id]