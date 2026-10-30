"""Recipe search: nutrition filters, category filter, ingredient matching, and sort order."""

import logging

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from recipe_api.models_recipe import RecipeCategories, RecipeIngredient
from recipe_api.queries.nutrition import nutrient_totals, nutrition_statement
from recipe_finder.schemas import SearchRequest

logger = logging.getLogger(__name__)

MATCHED_INGREDIENT_VALUE = 1
UNMATCHED_INGREDIENT_VALUE = 0
MIN_MATCHED_COUNT = 1


MAX_FILTER_NUTRIENTS = {"max_calorie": "calorie"}
MIN_FILTER_NUTRIENTS = {
    "min_protein": "protein",
    "min_carbohydrate": "carbohydrate",
    "min_fat": "fat",
    "min_fiber": "fiber",
    "min_sugar": "sugar",
    "min_sodium": "sodium",
}


def search_recipes(
    session: Session, request: SearchRequest, limit: int
) -> tuple[list[int], int] | None:
    """Return (ordered recipe ids, real total) for the request, or None on a database error."""
    try:
        totals = nutrient_totals()
        ingredient_count = func.count()
        matched_count = func.sum(
            case(
                (
                    RecipeIngredient.ingredient_id.in_(request.ingredient_ids),
                    MATCHED_INGREDIENT_VALUE,
                ),
                else_=UNMATCHED_INGREDIENT_VALUE,
            )
        )

        statement = nutrition_statement().add_columns(matched_count.label("matched_count"))

        for field_name, nutrient in MAX_FILTER_NUTRIENTS.items():
            value = getattr(request, field_name)
            if value is not None:
                statement = statement.having(totals[nutrient] <= value)

        for field_name, nutrient in MIN_FILTER_NUTRIENTS.items():
            value = getattr(request, field_name)
            if value is not None:
                statement = statement.having(totals[nutrient] >= value)

        if request.category_id is not None:
            recipes_in_category = select(RecipeCategories.recipe_id).where(
                RecipeCategories.category_id == request.category_id
            )
            statement = statement.where(RecipeIngredient.recipe_id.in_(recipes_in_category))

        if request.ingredient_ids:
            statement = statement.having(matched_count >= MIN_MATCHED_COUNT)

        total = session.execute(select(func.count()).select_from(statement.subquery())).scalar_one()

        ordered_statement = statement.order_by(
            matched_count.desc(),
            (ingredient_count - matched_count).asc(),
            RecipeIngredient.recipe_id.asc(),
        ).limit(limit)
        recipe_ids = [row.recipe_id for row in session.execute(ordered_statement)]
        return recipe_ids, total
    except Exception as e:
        logger.exception("Failed to search recipes", exc_info=e)
        return None
