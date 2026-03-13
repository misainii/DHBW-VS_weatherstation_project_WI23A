from __future__ import annotations

import math


EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1_r = math.radians(lat1)
    lon1_r = math.radians(lon1)
    lat2_r = math.radians(lat2)
    lon2_r = math.radians(lon2)

    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_KM * c


def validate_latitude(latitude: float) -> None:
    if latitude < -90 or latitude > 90:
        raise ValueError("Latitude must be between -90 and 90.")


def validate_longitude(longitude: float) -> None:
    if longitude < -180 or longitude > 180:
        raise ValueError("Longitude must be between -180 and 180.")


def round1(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 1)
