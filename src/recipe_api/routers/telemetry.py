"""Telemetry endpoints: sessions and events."""

from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from recipe_api.database import get_telemetry_session
from recipe_api.queries.telemetry import (
    SessionNotFoundError,
    add_event,
    create_session,
    update_session,
)
from recipe_api.routers.lookup import raise_db_unavailable
from recipe_api.telemetry import register_session
from recipe_finder.schemas import (
    EventRequest,
    SessionStartRequest,
    SessionStartResponse,
    SessionUpdateRequest,
)

SESSION_NOT_FOUND_CODE = "session_not_found"

router = APIRouter()

TelemetrySession = Annotated[Session, Depends(get_telemetry_session)]


def raise_session_not_found() -> NoReturn:
    """Answer 404 with a short code."""
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=SESSION_NOT_FOUND_CODE)


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
def post_session(request: SessionStartRequest, session: TelemetrySession) -> SessionStartResponse:
    """Start a session and return its id."""
    session_id = create_session(session, request.app_version, request.language_code)
    if session_id is None:
        raise_db_unavailable()
    register_session(session_id)
    return SessionStartResponse(session_id=session_id)


@router.patch("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def patch_session(
    session_id: Annotated[int, Path(ge=1)],
    request: SessionUpdateRequest,
    session: TelemetrySession,
) -> None:
    """Set the language or the end time of a session."""
    try:
        updated = update_session(session, session_id, request.language_code, request.ended_at)
    except SessionNotFoundError:
        raise_session_not_found()
    if not updated:
        raise_db_unavailable()


@router.post("/events", status_code=status.HTTP_204_NO_CONTENT)
def post_event(request: EventRequest, session: TelemetrySession) -> None:
    """Save one telemetry event."""
    try:
        saved = add_event(
            session,
            request.session_id,
            request.event_type,
            request.event_data,
            request.event_time,
        )
    except SessionNotFoundError:
        raise_session_not_found()
    if not saved:
        raise_db_unavailable()
