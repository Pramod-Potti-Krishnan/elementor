"""
Configuration settings for Visual Elements Orchestrator

Uses pydantic-settings for environment variable management with .env file support.
"""

from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Service URLs
    CHART_SERVICE_URL: str = "https://analytics-v30-production.up.railway.app"
    DIAGRAM_SERVICE_URL: str = "http://localhost:8080"
    TEXT_TABLE_SERVICE_URL: str = "http://localhost:8000"
    IMAGE_SERVICE_URL: str = "http://localhost:8000"
    INFOGRAPHIC_SERVICE_URL: str = "http://localhost:8000"
    LAYOUT_SERVICE_URL: str = "http://localhost:8504"

    # Timeouts (in seconds)
    SERVICE_TIMEOUT: float = 30.0
    DIAGRAM_POLL_TIMEOUT: float = 60.0  # Diagram uses async polling
    IMAGE_TIMEOUT: float = 60.0  # Image generation can take longer

    # Server config
    HOST: str = "0.0.0.0"
    PORT: int = 8090

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
