from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # App configuration
    app_name: str = "Weatherstation Explorer API"
    api_prefix: str = "/api"
    log_level: str = Field("INFO", env="LOG_LEVEL")
    
    # Data source configuration - IMMER AWS
    ghcn_source_mode: str = Field("remote_aws_yearly", env="GHCN_SOURCE_MODE")
    sample_data_dir: Path = Field(Path("/app/data/sample"), env="SAMPLE_DATA_DIR")
    
    # NOAA remote URLs (Fallback)
    remote_noaa_by_station_base_url: str = Field(
        "https://www.ncei.noaa.gov/pub/data/ghcn/daily/by_station",
        env="REMOTE_NOAA_BY_STATION_BASE_URL"
    )
    
    # AWS S3 configuration (ohne Account erforderlich)
    remote_aws_yearly_base_url: str = Field(
        "https://noaa-ghcn-pds.s3.amazonaws.com/csv",
        env="REMOTE_AWS_YEARLY_BASE_URL"
    )
    aws_s3_bucket: str = "noaa-ghcn-pds"
    aws_s3_region: str = "us-east-1"
    aws_s3_prefix: str = "csv/"
    aws_no_sign_request: bool = True  # Für anonymen Zugriff
    
    # Request settings
    request_timeout_seconds: int = 30
    max_retries: int = 3
    retry_backoff_factor: float = 1.0
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()