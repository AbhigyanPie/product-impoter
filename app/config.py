"""
Application Configuration
-------------------------
Centralized settings using Pydantic for validation.
All sensitive values come from environment variables.

For local development: Uses SQLite (no installation needed)
For production: Uses PostgreSQL (configured via DATABASE_URL)
"""

import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    app_name: str = "Product Importer"
    debug: bool = True
    
    # Database - defaults to SQLite for easy local development
    # Set DATABASE_URL env var for PostgreSQL in production
    database_url: str = "sqlite:///./products.db"
    
    # Redis URL - for Celery (optional for local dev)
    # If not available, we'll use sync processing
    redis_url: str = "redis://localhost:6379/0"
    
    # Flag to check if we're using SQLite
    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")
    
    # Upload settings
    max_file_size_mb: int = 100  # Maximum CSV file size
    chunk_size: int = 1000       # Rows per batch insert
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Cache and return settings instance."""
    return Settings()