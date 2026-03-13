from pydantic import BaseModel
from typing import Optional
from enum import Enum


class Element(str, Enum):
    TMIN = "TMIN"
    TMAX = "TMAX"


class Station(BaseModel):
    station_id: str
    name: str
    latitude: float
    longitude: float
    elevation_m: Optional[float] = None
    state: Optional[str] = None
    
    # Diese Felder werden dynamisch hinzugefügt
    distance_km: Optional[float] = None
    first_year: Optional[int] = None
    last_year: Optional[int] = None
    
    class Config:
        extra = "ignore"


class InventoryRecord(BaseModel):
    station_id: str
    latitude: float
    longitude: float
    element: Element
    first_year: int
    last_year: int


class DailyObservation(BaseModel):
    station_id: str
    date: str
    year: int
    month: int
    day: int
    element: Element
    value_c: float
    qflag: Optional[str] = None