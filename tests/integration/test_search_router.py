import pytest
from fastapi import status
from fastapi.testclient import TestClient

from recipe_api.main import app

pytestmark = pytest.mark.integration

client = TestClient(app)

SEEDED_RECIPE_COUNT = 3
HIGH_PROTEIN_MINIMUM = 30
HIGH_PROTEIN_RECIPE_COUNT = 1


def test_search_without_filters_returns_all_recipes() -> None:
    response = client.post("/search", json={})

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["total"] == SEEDED_RECIPE_COUNT
    assert len(body["recipe_ids"]) == SEEDED_RECIPE_COUNT


def test_search_applies_nutrition_filter() -> None:
    response = client.post("/search", json={"min_protein": HIGH_PROTEIN_MINIMUM})

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["total"] == HIGH_PROTEIN_RECIPE_COUNT
    assert len(body["recipe_ids"]) == HIGH_PROTEIN_RECIPE_COUNT


@pytest.mark.parametrize(
    "body",
    [
        {"min_protein": -1},
        {"max_calorie": -0.5},
        {"ingredient_ids": [0]},
        {"category_id": 0},
        {"lang": ""},
    ],
)
def test_search_rejects_invalid_input(body: dict[str, object]) -> None:
    response = client.post("/search", json=body)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_search_answers_short_code_when_database_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("recipe_api.routers.recipes.search_recipes", lambda *_: None)

    response = client.post("/search", json={})

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json() == {"detail": "db_unavailable"}
