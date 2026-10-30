import pytest
from sqlalchemy.orm import Session

from recipe_api.queries.recipes import RecipeNotFoundError, lookup_recipe

pytestmark = pytest.mark.integration

SCRAMBLED_EGGS = "Scrambled Eggs"
MISSING_RECIPE_ID = 999_999
UNKNOWN_LANGUAGE_CODE = "xx"


def test_recipe_detail_in_english(
    recipe_session: Session, recipe_ids_by_name: dict[str, int]
) -> None:
    recipe = lookup_recipe(recipe_session, recipe_ids_by_name[SCRAMBLED_EGGS], "en")

    assert recipe is not None
    assert recipe.name == SCRAMBLED_EGGS
    assert recipe.prep_time_minutes == 5
    assert recipe.instructions.startswith("1. Crack the eggs")
    assert {category.name for category in recipe.categories} == {"Breakfast", "Snack"}
    assert [(item.name, item.quantity_grams) for item in recipe.ingredients] == [
        ("egg", 150.0),
        ("olive oil", 10.0),
    ]
    assert recipe.nutrition.calorie == pytest.approx(302.9)
    assert recipe.nutrition.sodium == pytest.approx(213.2)


def test_recipe_detail_in_turkish(
    recipe_session: Session, recipe_ids_by_name: dict[str, int]
) -> None:
    recipe = lookup_recipe(recipe_session, recipe_ids_by_name[SCRAMBLED_EGGS], "tr")

    assert recipe is not None
    assert recipe.name == "Çırpılmış Yumurta"
    assert {category.name for category in recipe.categories} == {"Kahvaltı", "Atıştırmalık"}
    assert [item.name for item in recipe.ingredients] == ["yumurta", "zeytinyağı"]


def test_recipe_detail_falls_back_to_english(
    recipe_session: Session, recipe_ids_by_name: dict[str, int]
) -> None:
    recipe = lookup_recipe(
        recipe_session, recipe_ids_by_name[SCRAMBLED_EGGS], UNKNOWN_LANGUAGE_CODE
    )

    assert recipe is not None
    assert recipe.name == SCRAMBLED_EGGS


def test_recipe_detail_raises_for_missing_recipe(recipe_session: Session) -> None:
    with pytest.raises(RecipeNotFoundError):
        lookup_recipe(recipe_session, MISSING_RECIPE_ID, "en")
