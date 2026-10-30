"""Best-effort API telemetry for recipe database operations."""

from __future__ import annotations

import logging
import time
from collections import OrderedDict
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from recipe_api.database import get_telemetry_engine
from recipe_api.queries.telemetry import add_event
from recipe_finder.schemas import EventType

logger = logging.getLogger(__name__)

MAX_OPEN_SESSIONS = 10_000
_open_sessions: OrderedDict[int, None] = OrderedDict()
_recipe_connections: set[int] = set()


def register_session(session_id: int) -> None:
    """Remember a newly created session for API event validation."""
    _open_sessions[session_id] = None
    _open_sessions.move_to_end(session_id)
    while len(_open_sessions) > MAX_OPEN_SESSIONS:
        _open_sessions.popitem(last=False)


def record_api_event(
    session_id: int | None,
    event_type: EventType,
    event_data: dict[str, Any],
) -> None:
    """Save an API event without affecting the request outcome."""
    if session_id is None or session_id not in _open_sessions:
        return
    try:
        with Session(get_telemetry_engine(), autoflush=False) as session:
            add_event(session, session_id, event_type, event_data, datetime.now(UTC))
    except Exception:
        logger.debug("Could not save API telemetry event", exc_info=True)


def record_query(
    session_id: int | None,
    query_name: str,
    started_at: float,
    rows: int | None,
) -> None:
    """Record a successful API query and its duration."""
    if session_id is not None and session_id not in _recipe_connections:
        _recipe_connections.add(session_id)
        record_api_event(
            session_id,
            "db_connection_opened",
            {"duration_ms": 0},
        )
    record_api_event(
        session_id,
        "db_query_completed",
        {
            "query": query_name,
            "duration_ms": round((time.perf_counter() - started_at) * 1000),
            "rows": rows or 0,
        },
    )


def record_query_failure(session_id: int | None, query_name: str) -> None:
    """Record a failed database query and connection failure."""
    record_api_event(session_id, "db_connection_failed", {"error": "db_unavailable"})
    record_api_event(
        session_id,
        "db_query_failed",
        {"query": query_name, "error": "db_unavailable"},
    )
