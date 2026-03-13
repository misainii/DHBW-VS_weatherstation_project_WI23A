from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .logging_config import configure_logging
from .schemas import ClimateResponse, MetaResponse, SearchResponse, StationResponse
from .services import WeatherstationService

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

service = WeatherstationService()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get(f"{settings.api_prefix}/meta", response_model=MetaResponse)
def get_meta() -> MetaResponse:
    try:
        meta = service.get_meta()
        return MetaResponse(
            earliest_start_year=meta["earliest_start_year"],
            latest_end_year=meta["latest_end_year"],
            source_mode=settings.ghcn_source_mode,
        )
    except Exception as e:
        logger.error(f"Fehler in /meta: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(f"{settings.api_prefix}/stations", response_model=SearchResponse)
def search_stations(
    latitude: float = Query(..., description="Breitengrad (-90 bis 90)"),
    longitude: float = Query(..., description="Längengrad (-180 bis 180)"),
    radius_km: float = Query(..., gt=0, description="Suchradius in Kilometern"),
    limit: int = Query(..., ge=1, le=20, description="Maximale Anzahl der Ergebnisse"),
    start_year: int = Query(..., description="Startjahr für die Datenabfrage"),
    end_year: int = Query(..., description="Endjahr für die Datenabfrage"),
) -> SearchResponse:
    """
    Sucht Wetterstationen im angegebenen Umkreis, die für den gesamten
    angeforderten Jahresbereich Daten liefern können.
    """
    # Validierung der Eingaben
    if latitude < -90 or latitude > 90:
        raise HTTPException(status_code=400, detail="latitude muss zwischen -90 und 90 liegen")
    
    if longitude < -180 or longitude > 180:
        raise HTTPException(status_code=400, detail="longitude muss zwischen -180 und 180 liegen")
    
    if start_year > end_year:
        raise HTTPException(
            status_code=400, 
            detail=f"start_year ({start_year}) darf nicht größer als end_year ({end_year}) sein"
        )
    
    try:
        matches = service.search_stations(latitude, longitude, radius_km, limit, start_year, end_year)
        
        # Konvertiere die Stationen in das Response-Format
        stations_response = []
        for station in matches:
            stations_response.append(
                StationResponse(
                    station_id=station.station_id,
                    name=station.name,
                    latitude=station.latitude,
                    longitude=station.longitude,
                    elevation_m=station.elevation_m,
                    distance_km=station.distance_km,
                    first_year=station.first_year,
                    last_year=station.last_year,
                )
            )
        
        return SearchResponse(
            query={
                "latitude": latitude,
                "longitude": longitude,
                "radius_km": radius_km,
                "limit": limit,
                "start_year": start_year,
                "end_year": end_year,
            },
            stations=stations_response,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as e:
        logger.error(f"Fehler in /stations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(f"{settings.api_prefix}/stations/{{station_id}}/climate", response_model=ClimateResponse)
def climate_summary(
    station_id: str,
    start_year: int = Query(..., description="Startjahr für die Analyse"),
    end_year: int = Query(..., description="Endjahr für die Analyse"),
    adjust_to_available: bool = Query(True, description="Jahresbereich automatisch an verfügbare Daten anpassen"),
) -> ClimateResponse:
    """
    Liefert eine Klimazusammenfassung für eine Station.
    """
    if start_year > end_year:
        raise HTTPException(
            status_code=400, 
            detail=f"start_year ({start_year}) darf nicht größer als end_year ({end_year}) sein"
        )
    
    try:
        # Hole verfügbaren Jahresbereich der Station
        available_range = service.get_station_years_range(station_id)
        
        original_start = start_year
        original_end = end_year
        
        if available_range and adjust_to_available:
            if start_year < available_range["first_year"]:
                start_year = available_range["first_year"]
            
            if end_year > available_range["last_year"]:
                end_year = available_range["last_year"]
            
            if start_year > end_year:
                raise HTTPException(
                    status_code=400,
                    detail=f"Keine Daten für Station {station_id} im Bereich "
                           f"{original_start}-{original_end} verfügbar. "
                           f"Verfügbarer Bereich: {available_range['first_year']}-{available_range['last_year']}"
                )
        
        summary = service.get_climate_summary(station_id, start_year, end_year)
        
        # Station konvertieren
        station_data = summary["station"]
        station_response = StationResponse(
            station_id=station_data.station_id,
            name=station_data.name,
            latitude=station_data.latitude,
            longitude=station_data.longitude,
            elevation_m=station_data.elevation_m,
            distance_km=getattr(station_data, 'distance_km', None),
            first_year=getattr(station_data, 'first_year', None),
            last_year=getattr(station_data, 'last_year', None),
        )
        
        return ClimateResponse(
            station=station_response,
            requested_period={
                "start_year": original_start,
                "end_year": original_end,
                "adjusted": (original_start != start_year or original_end != end_year)
            },
            actual_period={
                "start_year": start_year,
                "end_year": end_year,
            },
            data_gap_warning=summary["data_gap_warning"],
            missing_years=summary.get("missing_years", []),
            expected_years=summary.get("expected_years", end_year - start_year + 1),
            annual_series=summary["annual_series"],
            seasonal_series=summary["seasonal_series"],
            table=summary["table"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as e:
        logger.error(f"Fehler in /climate: {e}")
        raise HTTPException(status_code=500, detail=str(e))