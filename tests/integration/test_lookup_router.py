import pytest
from fastapi import status
from fastapi.testclient import TestClient

from recipe_api.main import app

pytestmark = pytest.mark.integration

client = TestClient(app)


def test_get_languages_returns_seeded_languages() -> None:
    response = client.get("/languages")

    assert response.status_code == status.HTTP_200_OK
    assert [language["language_code"] for language in response.json()] == ["en", "tr"]


def test_suggest_returns_matching_ingredient() -> None:
    response = client.get("/ingredients/suggest", params={"q": "chick", "lang": "en"})

    assert response.status_code == status.HTTP_200_OK
    assert "chicken breast" in [item["name"] for item in response.json()]


def test_suggest_without_text_is_rejected() -> None:
    response = client.get("/ingredients/suggest")

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
