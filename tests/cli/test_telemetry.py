"""Tests for asynchronous CLI telemetry."""

from threading import Event

from recipe_finder.api_client import ApiClientError
from recipe_finder.schemas import SessionStartResponse
from recipe_finder.telemetry import TelemetryManager


class FakeTelemetryClient:
    """Minimal client used to observe telemetry worker calls."""

    base_url = "http://test"

    def __init__(self) -> None:
        self.started = Event()
        self.events: list[object] = []
        self.closed: object | None = None

    def start_session(self, app_version: str, language_code: str) -> SessionStartResponse:
        self.started.set()
        return SessionStartResponse(session_id=42)

    def send_event(self, event: object) -> None:
        self.events.append(event)

    def update_session(self, session_id: int, update: object) -> None:
        self.closed = update


def test_telemetry_worker_creates_session_sends_events_and_closes() -> None:
    client = FakeTelemetryClient()
    manager = TelemetryManager(client=client, app_version="test", language_code="en")

    manager.submit("search_executed", {"ingredient_count": 1})
    manager.close()

    assert client.started.is_set()
    assert len(client.events) == 1
    assert client.closed is not None


def test_telemetry_event_data_contains_no_typed_text() -> None:
    from recipe_finder.telemetry import clear_tracked_events, get_tracked_events, track

    clear_tracked_events()
    track("invalid_input", {"step": "nutrition", "field": "protein_min"})

    event = get_tracked_events()[-1]
    assert "value" not in event["data"]


def test_telemetry_disables_after_three_consecutive_failures() -> None:
    class FailingClient(FakeTelemetryClient):
        def send_event(self, event: object) -> None:
            self.events.append(event)
            raise ApiClientError("offline")

    client = FailingClient()
    manager = TelemetryManager(client=client, app_version="test", language_code="en")
    for _ in range(3):
        manager.submit("error", {"where": "test"})

    manager.close()

    assert len(client.events) == 3
