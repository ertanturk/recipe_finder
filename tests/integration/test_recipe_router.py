import pytest
from fastapi import status
from fastapi.testclient import TestClient

from recipe_api.main import app

pytestmark = pytest.mark.integration

client = TestClient(app)

SCRAMBLED_EGGS = "Scrambled Eggs"
MISSING_RECIPE_ID = 999_999


def test_get_recipe_returns_full_recipe(recipe_ids_by_name: dict[str, int]) -> None:
    recipe_id = recipe_ids_by_name[SCRAMBLED_EGGS]

    response = client.get(f"/recipes/{recipe_id}", params={"lang": "en"})

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["name"] == SCRAMBLED_EGGS
    assert body["nutrition"]["calorie"] == pytest.approx(302.9)
    assert len(body["ingredients"]) == 2


def test_get_recipe_answers_404_with_short_code_for_missing_recipe() -> None:
    response = client.get(f"/recipes/{MISSING_RECIPE_ID}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "recipe_not_found"}


@pytest.mark.parametrize("recipe_id", ["0", "-1", "abc"])
def test_get_recipe_rejects_invalid_id(recipe_id: str) -> None:
    response = client.get(f"/recipes/{recipe_id}")

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_get_recipe_answers_short_code_when_database_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("recipe_api.routers.recipes.lookup_recipe", lambda *_: None)

    response = client.get("/recipes/1")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json() == {"detail": "db_unavailable"}
