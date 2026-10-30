"""The one nutrition formula, shared by search and recipe detail."""

from typing import Any

from sqlalchemy import ColumnElement, Select, func, select

from recipe_api.models_recipe import Ingredient, RecipeIngredient

# Ingredient nutrient values are stored per 100 g.
GRAMS_PER_NUTRIENT_BASE = 100.0

NUTRIENT_COLUMNS = {
    "calorie": Ingredient.ingredient_calorie,
    "protein": Ingredient.ingredient_protein,
    "fat": Ingredient.ingredient_fat,
    "carbohydrate": Ingredient.ingredient_carbohydrate,
    "sugar": Ingredient.ingredient_sugar,
    "fiber": Ingredient.ingredient_fiber,
    "sodium": Ingredient.ingredient_sodium,
}


def nutrient_totals() -> dict[str, ColumnElement[float]]:
    """Return one SUM expression per nutrient, to use inside GROUP BY recipe_id."""
    return {
        name: func.sum(RecipeIngredient.ingredient_quantity / GRAMS_PER_NUTRIENT_BASE * column)
        for name, column in NUTRIENT_COLUMNS.items()
    }


def nutrition_statement() -> Select[Any]:
    """Return a SELECT with recipe_id, every nutrient total, and ingredient_count per recipe."""
    totals = nutrient_totals()
    return (
        select(
            RecipeIngredient.recipe_id,
            *[total.label(name) for name, total in totals.items()],
            func.count().label("ingredient_count"),
        )
        .select_from(RecipeIngredient)
        .join(Ingredient, Ingredient.ingredient_id == RecipeIngredient.ingredient_id)
        .group_by(RecipeIngredient.recipe_id)
    )
