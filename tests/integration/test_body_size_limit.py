from collections.abc import Iterator

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from recipe_api.main import MAX_BODY_BYTES, app

pytestmark = pytest.mark.integration

client = TestClient(app)

CHUNK_BYTES = 1024
OVERSIZED_BODY = b" " * (MAX_BODY_BYTES + 1)


def oversized_chunks() -> Iterator[bytes]:
    for _ in range(MAX_BODY_BYTES // CHUNK_BYTES + 1):
        yield b" " * CHUNK_BYTES


def test_body_over_limit_is_rejected_by_content_length() -> None:
    response = client.post(
        "/search", content=OVERSIZED_BODY, headers={"Content-Type": "application/json"}
    )

    assert response.status_code == status.HTTP_413_CONTENT_TOO_LARGE
    assert response.json() == {"detail": "payload_too_large"}


def test_chunked_body_over_limit_is_rejected_while_reading() -> None:
    response = client.post(
        "/search", content=oversized_chunks(), headers={"Content-Type": "application/json"}
    )

    assert response.status_code == status.HTTP_413_CONTENT_TOO_LARGE
    assert response.json() == {"detail": "payload_too_large"}


def test_body_under_limit_is_accepted() -> None:
    response = client.post("/search", json={})

    assert response.status_code == status.HTTP_200_OK
