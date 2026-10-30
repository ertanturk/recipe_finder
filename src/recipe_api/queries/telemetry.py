"""Telemetry data: sessions and events."""

import json
import logging
from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import insert, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from recipe_api.models_telemetry import Session as SessionRecord
from recipe_api.models_telemetry import TelemetryEvent, TelemetryEventsTable

logger = logging.getLogger(__name__)


class SessionNotFoundError(Exception):
    """Raised when no session has the requested id."""


def to_naive_utc(value: datetime) -> datetime:
    """Convert to UTC and drop the zone, because the columns are DATETIME2 without a zone."""
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def create_session(session: Session, app_version: str, language_code: str) -> int | None:
    """Insert a session and return its id, or None on a database error."""
    try:
        statement = (
            insert(SessionRecord)
            .values(
                started_at=to_naive_utc(datetime.now(UTC)),
                app_version=app_version,
                language_code=language_code,
            )
            .returning(SessionRecord.session_id)
        )
        session_id = session.execute(statement).scalar_one()
        session.commit()
        return session_id
    except Exception as e:
        logger.exception("Failed to create session", exc_info=e)
        return None


def update_session(
    session: Session,
    session_id: int,
    language_code: str | None,
    ended_at: datetime | None,
) -> bool:
    """Set the given fields on a session. Return False on a database error.

    Raises:
        SessionNotFoundError: If no session has this id.
    """
    values: dict[str, Any] = {}
    if language_code is not None:
        values["language_code"] = language_code
    if ended_at is not None:
        values["ended_at"] = to_naive_utc(ended_at)

    try:
        result = session.execute(
            update(SessionRecord)
            .where(SessionRecord.session_id == session_id)
            .values(**values)
            .execution_options(synchronize_session=False)
        )

        cursor_result = cast(CursorResult, result)

        if cursor_result.rowcount == 0:
            raise SessionNotFoundError(session_id)
        session.commit()
        return True
    except SessionNotFoundError:
        raise
    except Exception as e:
        logger.exception("Failed to update session", exc_info=e)
        return False


def add_event(
    session: Session,
    session_id: int,
    event_type: str,
    event_data: dict[str, Any],
    event_time: datetime,
) -> bool:
    """Save one event. Return False on a database error.

    Raises:
        SessionNotFoundError: If no session has this id.
    """
    try:
        event_type_id = session.execute(
            select(TelemetryEventsTable.event_type_id).where(
                TelemetryEventsTable.event_type == event_type
            )
        ).scalar_one()
        session.execute(
            insert(TelemetryEvent).values(
                session_id=session_id,
                event_type_id=event_type_id,
                event_data=json.dumps(event_data),
                event_time=to_naive_utc(event_time),
            )
        )
        session.commit()
        return True
    except IntegrityError as e:
        # The only constraint a valid request can break is the foreign key to Sessions.
        raise SessionNotFoundError(session_id) from e
    except Exception as e:
        logger.exception("Failed to add event", exc_info=e)
        return False
