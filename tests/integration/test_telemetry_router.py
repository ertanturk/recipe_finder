import pytest
from fastapi import status
from fastapi.testclient import TestClient

from recipe_api.main import app

pytestmark = pytest.mark.integration

client = TestClient(app)

TEST_APP_VERSION = "test"
MISSING_SESSION_ID = 999_999_999
EVENT_TIME = "2026-01-01T12:00:00Z"
ENDED_AT = "2026-01-01T12:05:00Z"


def start_test_session() -> int:
    response = client.post(
        "/sessions", json={"app_version": TEST_APP_VERSION, "language_code": "en"}
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()["session_id"]


def build_event(session_id: int, /, **changes: object) -> dict[str, object]:
    event: dict[str, object] = {
        "session_id": session_id,
        "event_type": "search_executed",
        "event_data": {"ingredient_count": 2},
        "event_time": EVENT_TIME,
    }
    return event | changes


def test_start_session_returns_session_id() -> None:
    session_id = start_test_session()

    assert session_id >= 1


def test_patch_session_sets_language_and_end_time() -> None:
    session_id = start_test_session()

    response = client.patch(
        f"/sessions/{session_id}", json={"language_code": "tr", "ended_at": ENDED_AT}
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT


def test_patch_session_without_fields_is_rejected() -> None:
    session_id = start_test_session()

    response = client.patch(f"/sessions/{session_id}", json={})

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_patch_unknown_session_answers_404() -> None:
    response = client.patch(f"/sessions/{MISSING_SESSION_ID}", json={"ended_at": ENDED_AT})

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "session_not_found"}


def test_post_event_saves_event() -> None:
    session_id = start_test_session()

    response = client.post("/events", json=build_event(session_id))

    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.parametrize(
    "changes",
    [
        {"event_type": "not_an_event"},
        {"event_data": ["not", "an", "object"]},
        {"session_id": 0},
        {"event_time": "not a time"},
    ],
)
def test_post_event_rejects_invalid_input(changes: dict[str, object]) -> None:
    response = client.post("/events", json=build_event(1, **changes))

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_post_event_for_unknown_session_answers_404() -> None:
    response = client.post("/events", json=build_event(MISSING_SESSION_ID))

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "session_not_found"}


def test_start_session_answers_short_code_when_database_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("recipe_api.routers.telemetry.create_session", lambda *_: None)

    response = client.post(
        "/sessions", json={"app_version": TEST_APP_VERSION, "language_code": "en"}
    )

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json() == {"detail": "db_unavailable"}
