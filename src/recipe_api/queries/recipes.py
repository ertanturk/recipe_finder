"""Recipe detail: one full recipe with language fallback."""

import logging

from sqlalchemy import ColumnElement, ScalarSelect, SQLColumnExpression, func, select
from sqlalchemy.orm import Session

from recipe_api.models_recipe import (
    Ingredient,
    Localization,
    Recipe,
    RecipeCategories,
    RecipeCategory,
    RecipeIngredient,
)
from recipe_api.queries.lookup import FALLBACK_LANGUAGE_CODE
from recipe_api.queries.nutrition import NUTRIENT_COLUMNS, nutrition_statement
from recipe_finder.schemas import (
    CategoryResponse,
    NutritionResponse,
    RecipeIngredientResponse,
    RecipeResponse,
)

logger = logging.getLogger(__name__)


class RecipeNotFoundError(Exception):
    """Raised when no recipe has the requested id."""


def localized_text(text_id: SQLColumnExpression[int], language_code: str) -> ColumnElement[str]:
    """Return the text in the language, or in the fallback language when it is missing."""

    def text_in(code: str) -> ScalarSelect[str]:
        return (
            select(Localization.text_value)
            .where(Localization.text_id == text_id, Localization.language_code == code)
            .scalar_subquery()
        )

    return func.coalesce(text_in(language_code), text_in(FALLBACK_LANGUAGE_CODE))


def lookup_recipe(session: Session, recipe_id: int, language_code: str) -> RecipeResponse | None:
    """Return one full recipe, or None on a database error.

    Raises:
        RecipeNotFoundError: If no recipe has this id.
    """
    try:
        recipe_row = session.execute(
            select(
                Recipe.recipe_prep_time_in_minutes.label("prep_time_minutes"),
                localized_text(Recipe.name_text_id, language_code).label("name"),
                localized_text(Recipe.instructions_text_id, language_code).label("instructions"),
            ).where(Recipe.recipe_id == recipe_id)
        ).one_or_none()
        if recipe_row is None:
            raise RecipeNotFoundError(recipe_id)

        nutrition = (
            session.execute(nutrition_statement().where(RecipeIngredient.recipe_id == recipe_id))
            .mappings()
            .one()
        )

        category_rows = session.execute(
            select(
                RecipeCategory.category_id,
                localized_text(RecipeCategory.name_text_id, language_code),
            )
            .select_from(RecipeCategory)
            .join(RecipeCategories, RecipeCategories.category_id == RecipeCategory.category_id)
            .where(RecipeCategories.recipe_id == recipe_id)
            .order_by(RecipeCategory.category_id)
        ).all()

        ingredient_rows = session.execute(
            select(
                Ingredient.ingredient_id,
                localized_text(Ingredient.name_text_id, language_code),
                RecipeIngredient.ingredient_quantity,
            )
            .select_from(RecipeIngredient)
            .join(Ingredient, Ingredient.ingredient_id == RecipeIngredient.ingredient_id)
            .where(RecipeIngredient.recipe_id == recipe_id)
            .order_by(RecipeIngredient.ingredient_quantity.desc(), Ingredient.ingredient_id)
        ).all()

        return RecipeResponse(
            recipe_id=recipe_id,
            name=recipe_row.name,
            instructions=recipe_row.instructions,
            prep_time_minutes=recipe_row.prep_time_minutes,
            categories=[
                CategoryResponse(category_id=category_id, name=name)
                for category_id, name in category_rows
            ],
            nutrition=NutritionResponse(**{name: nutrition[name] for name in NUTRIENT_COLUMNS}),
            ingredients=[
                RecipeIngredientResponse(
                    ingredient_id=ingredient_id, name=name, quantity_grams=quantity
                )
                for ingredient_id, name, quantity in ingredient_rows
            ],
        )
    except RecipeNotFoundError:
        raise
    except Exception as e:
        logger.exception("Failed to look up recipe", exc_info=e)
        return None
