import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from recipe_api.models_recipe import Localization, Recipe, RecipeIngredient
from recipe_api.queries.nutrition import nutrition_statement

pytestmark = pytest.mark.integration

SCRAMBLED_EGGS_NAME = "Scrambled Eggs"
SCRAMBLED_EGGS_INGREDIENT_COUNT = 2
SCRAMBLED_EGGS_NUTRITION = {
    "calorie": 302.9,
    "protein": 18.9,
    "fat": 24.25,
    "carbohydrate": 1.05,
    "sugar": 0.6,
    "fiber": 0.0,
    "sodium": 213.2,
}


def test_nutrition_sums_quantity_times_value_per_100g(recipe_session: Session) -> None:
    recipe_id = recipe_session.scalar(
        select(Recipe.recipe_id)
        .join(Localization, Localization.text_id == Recipe.name_text_id)
        .where(
            Localization.language_code == "en",
            Localization.text_value == SCRAMBLED_EGGS_NAME,
        )
    )
    assert recipe_id is not None

    statement = nutrition_statement().where(RecipeIngredient.recipe_id == recipe_id)
    row = recipe_session.execute(statement).one()._mapping

    for nutrient, expected_value in SCRAMBLED_EGGS_NUTRITION.items():
        assert row[nutrient] == pytest.approx(expected_value)
    assert row["ingredient_count"] == SCRAMBLED_EGGS_INGREDIENT_COUNT


def test_nutrition_returns_one_row_per_recipe(recipe_session: Session) -> None:
    recipe_count = recipe_session.scalar(select(func.count()).select_from(Recipe))

    rows = recipe_session.execute(nutrition_statement()).all()

    assert len(rows) == recipe_count
