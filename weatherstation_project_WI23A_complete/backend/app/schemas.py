from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Union


class StationResponse(BaseModel):
    station_id: str
    name: str
    latitude: float
    longitude: float
    elevation_m: Optional[float] = None
    distance_km: Optional[float] = None
    first_year: Optional[int] = None
    last_year: Optional[int] = None
    
    class Config:
        from_attributes = True
        extra = "ignore"


class SearchResponse(BaseModel):
    query: Dict[str, Union[float, int, str]]
    stations: List[StationResponse]
    
    class Config:
        extra = "ignore"


class MetaResponse(BaseModel):
    earliest_start_year: int
    latest_end_year: int
    source_mode: str
    available_years: Optional[List[int]] = None
    
    class Config:
        extra = "ignore"


class ClimateResponse(BaseModel):
    station: StationResponse
    requested_period: Dict[str, Union[int, bool, str]]
    actual_period: Optional[Dict[str, int]] = None
    data_gap_warning: bool
    missing_years: List[int]
    expected_years: int
    annual_series: List[Dict[str, Any]]
    seasonal_series: List[Dict[str, Any]]
    table: List[Dict[str, Any]]
    
    class Config:
        extra = "ignore"