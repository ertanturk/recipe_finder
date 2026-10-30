"""Database engines and session dependencies for the Recipe DB and the Telemetry DB."""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from .settings import get_settings


@lru_cache
def get_recipe_engine() -> Engine:
    """Return the Recipe DB engine, created once on first use."""
    return create_engine(get_settings().RECIPE_DB_URL.get_secret_value())


@lru_cache
def get_telemetry_engine() -> Engine:
    """Return the Telemetry DB engine, created once on first use."""
    return create_engine(get_settings().TELEMETRY_DB_URL.get_secret_value())


def get_recipe_session() -> Iterator[Session]:
    """Yield a Recipe DB session and close it after the request."""
    with Session(get_recipe_engine(), autoflush=False) as session:
        yield session


def get_telemetry_session() -> Iterator[Session]:
    """Yield a Telemetry DB session and close it after the request."""
    with Session(get_telemetry_engine(), autoflush=False) as session:
        yield session
