"""Settings for the recipe API."""

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """API settings, read from environment variables or the .env file."""

    RECIPE_DB_URL: SecretStr
    TELEMETRY_DB_URL: SecretStr
    SEARCH_LIMIT: int = Field(default=100, ge=1)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Silently skip unexpected variables in the file
    )


@lru_cache
def get_settings() -> Settings:
    """Return the settings, created once on first use."""
    return Settings()
