from __future__ import annotations

import math
import logging
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict

from .data_sources import GHCNRepository
from .models import DailyObservation, Element, Station
from .config import get_settings

logger = logging.getLogger(__name__)


class WeatherstationService:
    def __init__(self) -> None:
        self.repo = GHCNRepository()
        self.settings = get_settings()

    def get_meta(self) -> Dict[str, Any]:
        inventory = self.repo.load_inventory()
        if not inventory:
            return {"earliest_start_year": 1980, "latest_end_year": 2025}

        earliest = min(rec.first_year for rec in inventory)
        latest = max(rec.last_year for rec in inventory)
        return {"earliest_start_year": earliest, "latest_end_year": latest}

    def get_station_years_range(self, station_id: str) -> Optional[Dict[str, int]]:
        inventory = self.repo.load_inventory()
        station_inventory = [inv for inv in inventory if inv.station_id == station_id]
        
        if not station_inventory:
            return None
        
        tmin_records = [inv for inv in station_inventory if inv.element == Element.TMIN]
        tmax_records = [inv for inv in station_inventory if inv.element == Element.TMAX]
        
        if not tmin_records or not tmax_records:
            return None
        
        first_year = max(
            min(rec.first_year for rec in tmin_records),
            min(rec.first_year for rec in tmax_records)
        )
        last_year = min(
            max(rec.last_year for rec in tmin_records),
            max(rec.last_year for rec in tmax_records)
        )
        
        return {"first_year": first_year, "last_year": last_year}

    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371.0
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
        return round(R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))), 1)

    def search_stations(self, latitude: float, longitude: float, radius_km: float, limit: int, start_year: int, end_year: int) -> List[Station]:
        logger.info(f"Suche Stationen bei ({latitude}, {longitude}) im Umkreis von {radius_km}km")
        
        stations = self.repo.load_stations()
        inventory = self.repo.load_inventory()
        
        inventory_by_station = {}
        for inv in inventory:
            if inv.station_id not in inventory_by_station:
                inventory_by_station[inv.station_id] = []
            inventory_by_station[inv.station_id].append(inv)
        
        valid_stations = []
        
        for station in stations:
            station_inventory = inventory_by_station.get(station.station_id, [])
            if not station_inventory:
                continue
            
            tmin_records = [inv for inv in station_inventory if inv.element == Element.TMIN]
            tmax_records = [inv for inv in station_inventory if inv.element == Element.TMAX]
            
            if not tmin_records or not tmax_records:
                continue
            
            distance = self.calculate_distance(latitude, longitude, station.latitude, station.longitude)
            
            if distance <= radius_km:
                station_first = max(
                    min(r.first_year for r in tmin_records),
                    min(r.first_year for r in tmax_records)
                )
                station_last = min(
                    max(r.last_year for r in tmin_records),
                    max(r.last_year for r in tmax_records)
                )
                
                if station_last >= start_year and station_first <= end_year:
                    station_copy = Station(
                        station_id=station.station_id,
                        name=station.name,
                        latitude=station.latitude,
                        longitude=station.longitude,
                        elevation_m=station.elevation_m,
                        state=station.state,
                    )
                    station_copy.distance_km = distance
                    station_copy.first_year = station_first
                    station_copy.last_year = station_last
                    
                    valid_stations.append(station_copy)
        
        valid_stations.sort(key=lambda s: s.distance_km)
        return valid_stations[:limit]

    def _is_leap_year(self, year: int) -> bool:
        return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)

    def _get_days_in_month(self, year: int, month: int) -> int:
        if month in [1, 3, 5, 7, 8, 10, 12]:
            return 31
        elif month in [4, 6, 9, 11]:
            return 30
        else:
            return 29 if self._is_leap_year(year) else 28

    def _calculate_monthly_averages(self, observations: List[DailyObservation]) -> Dict[Tuple[int, int], Dict[str, float]]:
        monthly_values = defaultdict(lambda: {'TMIN': [], 'TMAX': []})
        for obs in observations:
            key = (obs.year, obs.month)
            monthly_values[key][obs.element.value].append(obs.value_c)

        monthly_averages = {}
        for (year, month), values in monthly_values.items():
            expected_days = self._get_days_in_month(year, month)
            
            if len(values['TMIN']) == expected_days:
                tmin_avg = sum(values['TMIN']) / expected_days
                if (year, month) not in monthly_averages:
                    monthly_averages[(year, month)] = {}
                monthly_averages[(year, month)]['TMIN'] = round(tmin_avg, 1)
            
            if len(values['TMAX']) == expected_days:
                tmax_avg = sum(values['TMAX']) / expected_days
                if (year, month) not in monthly_averages:
                    monthly_averages[(year, month)] = {}
                monthly_averages[(year, month)]['TMAX'] = round(tmax_avg, 1)
        
        return monthly_averages

    def _calculate_yearly_averages(self, monthly_averages: Dict[Tuple[int, int], Dict[str, float]], start_year: int, end_year: int) -> List[Dict[str, Any]]:
        yearly = defaultdict(lambda: {'TMIN': [], 'TMAX': []})
        
        for (year, month), values in monthly_averages.items():
            if 'TMIN' in values:
                yearly[year]['TMIN'].append(values['TMIN'])
            if 'TMAX' in values:
                yearly[year]['TMAX'].append(values['TMAX'])
        
        results = []
        for year in range(start_year, end_year + 1):
            row = {'year': year}
            if year in yearly:
                tmin_vals = yearly[year]['TMIN']
                tmax_vals = yearly[year]['TMAX']
                
                if len(tmin_vals) == 12:
                    row['annual_tmin'] = round(sum(tmin_vals) / 12, 1)
                if len(tmax_vals) == 12:
                    row['annual_tmax'] = round(sum(tmax_vals) / 12, 1)
            results.append(row)
        return results

    def _calculate_seasonal_averages(self, monthly_averages: Dict[Tuple[int, int], Dict[str, float]],
                                     start_year: int, end_year: int, latitude: float) -> List[Dict[str, Any]]:
        """
        calculating seasonal mean.
        northern hemisphere:
          - winter (Dec, Jan, Feb) contains data of dec (year that is given) and jan, feb (following year).
          - other seasons remain within the same year.
        southern hemisphere:
          - summer (Dec, Jan, Feb) contains data of dec (year that is given) and jan, feb (following year).
           - other seasons remain within the same year.
        all available months are calculated (even if only  1 or 2 are available).
        """
        is_northern = latitude >= 0

        if is_northern:
            # northern hemisphere
            seasons = {
                'spring': [(3, 0), (4, 0), (5, 0)],          # Mär, Apr, Mai
                'summer': [(6, 0), (7, 0), (8, 0)],          # Jun, Jul, Aug
                'autumn': [(9, 0), (10, 0), (11, 0)],        # Sep, Okt, Nov
                'winter': [(12, 0), (1, 1), (2, 1)],         # Dez (Jahr+0), Jan (Jahr+1), Feb (Jahr+1)
            }
        else:
            # southern hemisphere
            seasons = {
                'spring': [(9, 0), (10, 0), (11, 0)],        # Sep, Okt, Nov
                'summer': [(12, 0), (1, 1), (2, 1)],         # Dez (Jahr+0), Jan (Jahr+1), Feb (Jahr+1)
                'autumn': [(3, 0), (4, 0), (5, 0)],          # Mär, Apr, Mai
                'winter': [(6, 0), (7, 0), (8, 0)],          # Jun, Jul, Aug
            }

        seasonal_results = []

        # iterate over whole year
        for target_year in range(start_year, end_year + 1):
            for season_name, month_offsets in seasons.items():
                tmin_vals = []
                tmax_vals = []

                for month, offset in month_offsets:
                    actual_year = target_year + offset
                    key = (actual_year, month)
                    if key in monthly_averages:
                        if 'TMIN' in monthly_averages[key]:
                            tmin_vals.append(monthly_averages[key]['TMIN'])
                        if 'TMAX' in monthly_averages[key]:
                            tmax_vals.append(monthly_averages[key]['TMAX'])

                # calculate mean, if at least one month available
                if tmin_vals:
                    seasonal_results.append({
                        'year': target_year,
                        'season': season_name,
                        f'{season_name}_tmin': round(sum(tmin_vals) / len(tmin_vals), 1)
                    })
                if tmax_vals:
                    seasonal_results.append({
                        'year': target_year,
                        'season': season_name,
                        f'{season_name}_tmax': round(sum(tmax_vals) / len(tmax_vals), 1)
                    })

        return seasonal_results

    def get_climate_summary(self, station_id: str, start_year: int, end_year: int) -> Dict[str, Any]:
        logger.info(f"climate summary for {station_id} ({start_year}-{end_year})")
        
        stations = self.repo.load_stations()
        station = next((s for s in stations if s.station_id == station_id), None)
        if not station:
            raise ValueError(f"Station {station_id} not found")
        
        observations = self.repo.load_station_observations(station_id, start_year, end_year)
        
        if not observations:
            table_data = [{'year': year} for year in range(start_year, end_year + 1)]
            return {
                "station": station,
                "data_gap_warning": True,
                "missing_years": list(range(start_year, end_year + 1)),
                "expected_years": end_year - start_year + 1,
                "annual_series": [],
                "seasonal_series": [],
                "table": table_data,
            }
        
        monthly = self._calculate_monthly_averages(observations)
        annual = self._calculate_yearly_averages(monthly, start_year, end_year)
        seasonal = self._calculate_seasonal_averages(monthly, start_year, end_year, station.latitude)
        
        # create table
        table_dict = {year: {'year': year} for year in range(start_year, end_year + 1)}
        
        # annual data
        for a in annual:
            year = a['year']
            if year in table_dict:
                if 'annual_tmin' in a:
                    table_dict[year]['annual_tmin'] = a['annual_tmin']
                if 'annual_tmax' in a:
                    table_dict[year]['annual_tmax'] = a['annual_tmax']
        
        # seasonal data
        for s in seasonal:
            year = s['year']
            season = s['season']
            if year in table_dict:
                if f'{season}_tmin' in s:
                    table_dict[year][f'{season}_tmin'] = s[f'{season}_tmin']
                if f'{season}_tmax' in s:
                    table_dict[year][f'{season}_tmax'] = s[f'{season}_tmax']
        
        table_data = [table_dict[year] for year in sorted(table_dict.keys())]
        
        # series for frontend
        annual_series = []
        tmin_points = [{'year': row['year'], 'value': row['annual_tmin']} for row in table_data if 'annual_tmin' in row and row['annual_tmin'] is not None]
        tmax_points = [{'year': row['year'], 'value': row['annual_tmax']} for row in table_data if 'annual_tmax' in row and row['annual_tmax'] is not None]
        
        if tmin_points:
            annual_series.append({"name": "annual_tmin", "label_de": "Jährliches TMIN", "label_en": "Annual TMIN", "points": tmin_points})
        if tmax_points:
            annual_series.append({"name": "annual_tmax", "label_de": "Jährliches TMAX", "label_en": "Annual TMAX", "points": tmax_points})
        
        seasonal_series = []
        for season in ['spring', 'summer', 'autumn', 'winter']:
            tmin_points = [{'year': row['year'], 'value': row[f'{season}_tmin']} for row in table_data if f'{season}_tmin' in row and row[f'{season}_tmin'] is not None]
            tmax_points = [{'year': row['year'], 'value': row[f'{season}_tmax']} for row in table_data if f'{season}_tmax' in row and row[f'{season}_tmax'] is not None]
            
            if tmin_points:
                seasonal_series.append({"name": f"{season}_tmin", "label_de": f"{season.capitalize()} TMIN", "label_en": f"{season.capitalize()} TMIN", "points": tmin_points})
            if tmax_points:
                seasonal_series.append({"name": f"{season}_tmax", "label_de": f"{season.capitalize()} TMAX", "label_en": f"{season.capitalize()} TMAX", "points": tmax_points})
        
        years_with_data = {row["year"] for row in table_data if 'annual_tmin' in row or 'annual_tmax' in row}
        missing_years = [y for y in range(start_year, end_year + 1) if y not in years_with_data]
        
        return {
            "station": station,
            "data_gap_warning": len(missing_years) > 0,
            "missing_years": missing_years,
            "expected_years": end_year - start_year + 1,
            "annual_series": annual_series,
            "seasonal_series": seasonal_series,
            "table": table_data,
        }
