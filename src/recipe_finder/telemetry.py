"""Asynchronous telemetry tracking for CLI operations."""

from __future__ import annotations

import logging
import queue
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from recipe_finder.api_client import ApiClient, ApiClientError
from recipe_finder.config import TELEMETRY_TIMEOUT
from recipe_finder.schemas import (
    EventRequest,
    EventType,
    SessionStartResponse,
    SessionUpdateRequest,
)

logger = logging.getLogger(__name__)

MAX_CONSECUTIVE_FAILURES = 3
TELEMETRY_SHUTDOWN_TIMEOUT_SECONDS = 2.0

_events: list[dict[str, Any]] = []
_manager: TelemetryManager | None = None


class TelemetryClient(Protocol):
    """Client operations required by the telemetry worker."""

    base_url: str

    def start_session(self, app_version: str, language_code: str) -> SessionStartResponse:
        """Start a remote telemetry session."""

    def send_event(self, event: EventRequest) -> None:
        """Send one remote telemetry event."""

    def update_session(self, session_id: int, update: SessionUpdateRequest) -> None:
        """Update a remote telemetry session."""


@dataclass(frozen=True)
class _LanguageUpdate:
    """Worker command for updating the remote session language."""

    language_code: str


class TelemetryManager:
    """Send telemetry events in a background worker without blocking the CLI."""

    def __init__(self, client: TelemetryClient, app_version: str, language_code: str) -> None:
        self.client = client
        self._transport: TelemetryClient = client
        if type(client) is ApiClient:
            self._transport = ApiClient(base_url=client.base_url, timeout=TELEMETRY_TIMEOUT)
        self.app_version = app_version
        self.language_code = language_code
        self._events: queue.Queue[tuple[EventType, dict[str, object]] | _LanguageUpdate | None] = (
            queue.Queue()
        )
        self._ready = threading.Event()
        self._stopped = threading.Event()
        self._thread = threading.Thread(target=self._run, name="recipe-telemetry", daemon=True)
        self._thread.start()
        self._ready.wait(TELEMETRY_SHUTDOWN_TIMEOUT_SECONDS)

    def submit(self, event_type: EventType, data: dict[str, object]) -> None:
        """Queue an event for delivery."""
        if not self._stopped.is_set():
            self._events.put_nowait((event_type, data))

    def update_language(self, language_code: str) -> None:
        """Queue a remote session language update."""
        if not self._stopped.is_set():
            self._events.put_nowait(_LanguageUpdate(language_code))

    def close(self) -> None:
        """Stop the worker and close the remote session within the time limit."""
        if self._stopped.is_set():
            return
        self._events.put_nowait(None)
        self._thread.join(TELEMETRY_SHUTDOWN_TIMEOUT_SECONDS)
        self._stopped.set()

    def _run(self) -> None:
        failures = 0
        session_id: int | None = None
        try:
            try:
                session_id = self._transport.start_session(
                    self.app_version, self.language_code
                ).session_id
                if type(self.client) is ApiClient:
                    self.client.session_id = session_id
            except ApiClientError:
                failures += 1
            finally:
                self._ready.set()

            while failures < MAX_CONSECUTIVE_FAILURES:
                item = self._events.get()
                if item is None:
                    break
                if isinstance(item, _LanguageUpdate):
                    if session_id is not None:
                        try:
                            self._transport.update_session(
                                session_id,
                                SessionUpdateRequest(language_code=item.language_code),
                            )
                            failures = 0
                        except ApiClientError:
                            failures += 1
                    continue
                event_type, data = item
                if session_id is None:
                    continue
                try:
                    self._transport.send_event(
                        EventRequest(
                            session_id=session_id,
                            event_type=event_type,
                            event_data=data,
                            event_time=datetime.now(UTC),
                        )
                    )
                    failures = 0
                except ApiClientError:
                    failures += 1

            if session_id is not None:
                try:
                    self._transport.update_session(
                        session_id,
                        SessionUpdateRequest(ended_at=datetime.now(UTC)),
                    )
                except ApiClientError:
                    logger.debug("Could not close telemetry session", exc_info=True)
        finally:
            if type(self._transport) is ApiClient:
                self._transport.close()
            self._stopped.set()


def start_telemetry(client: TelemetryClient, app_version: str, language_code: str) -> None:
    """Start the background telemetry session."""
    global _manager
    stop_telemetry()
    _manager = TelemetryManager(client, app_version, language_code)


def stop_telemetry() -> None:
    """Stop the background telemetry worker if it is running."""
    global _manager
    if _manager is not None:
        _manager.close()
        _manager = None


def update_telemetry_language(previous: str, language_code: str) -> None:
    """Update the remote session language and record the language change."""
    if _manager is not None:
        _manager.update_language(language_code)
    track("language_changed", {"from": previous, "to": language_code})


def track(event_type: EventType, data: dict[str, object] | None = None) -> None:
    """Record and asynchronously send a telemetry event without raising exceptions."""
    payload = data or {}
    try:
        _events.append({"event_type": event_type, "data": payload})
        if _manager is not None:
            _manager.submit(event_type, payload)
    except Exception:
        logger.debug("Failed to record telemetry event: %s", event_type, exc_info=True)


def get_tracked_events() -> list[dict[str, Any]]:
    """Return recorded telemetry events in memory."""
    return list(_events)


def clear_tracked_events() -> None:
    """Clear recorded telemetry events from memory."""
    _events.clear()
