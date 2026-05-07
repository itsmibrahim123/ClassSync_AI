"""
Configuration management for ClassSync AI.
Loads settings from environment variables.
"""

import os
from pydantic_settings import BaseSettings
from functools import lru_cache


def get_database_url() -> str:
    """
    Get DATABASE_URL from environment.
    Raises RuntimeError if not set (required for Railway deployment).
    """
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set. "
            "For local development, create a .env file with DATABASE_URL. "
            "For Railway, ensure PostgreSQL plugin is attached."
        )
    return url


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "ClassSync AI"
    debug: bool = True
    version: str = "0.1.0"

    # API Configuration
    api_prefix: str = "/api/v1"
    allowed_origins: str = "http://localhost:3000,http://localhost:8000"

    # Database - NO DEFAULT, must be set via environment
    database_url: str = ""  # Will be validated below
    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "classsync_db"
    database_user: str = "postgres"
    database_password: str = "password"

    # S3/Cloud Storage
    s3_bucket_name: str = "classsync-uploads"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_region: str = "us-east-1"
    s3_endpoint_url: str = "https://s3.amazonaws.com"

    # AI/LLM
    openai_api_key: str = ""
    gemini_api_key: str = ""
    primary_llm_model: str = "gpt-4-turbo-preview"
    secondary_llm_model: str = "gemini-pro"

    # Security
    secret_key: str = "your-secret-key-change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # File Upload
    max_upload_size_mb: int = 50

    # Scheduler
    max_optimization_time_seconds: int = 60
    default_timeslot_duration_minutes: int = 60

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses lru_cache to avoid reloading settings on every call.
    Validates that DATABASE_URL is set.
    """
    s = Settings()

    # Validate DATABASE_URL - fail fast if not set
    if not s.database_url:
        # Try to get from environment directly (pydantic-settings should have done this)
        s.database_url = get_database_url()

    return s


# Create a global settings instance for easy import
settings = get_settings()