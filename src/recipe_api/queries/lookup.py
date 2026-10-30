import logging

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session, aliased

from recipe_api.models_recipe import Ingredient, Language, Localization, RecipeCategory

FALLBACK_LANGUAGE_CODE = "en"
NAME_STARTS_WITH_TEXT_RANK = 0
NAME_CONTAINS_TEXT_RANK = 1

logger = logging.getLogger(__name__)


def lookup_languages(session: Session) -> list[Language] | None:
    """Return all languages ordered by name."""
    try:
        statement = select(Language).order_by(Language.language_name)
        return list(session.scalars(statement))
    except Exception as e:
        logger.exception("Failed to lookup languages", exc_info=e)
        return None


def lookup_categories(session: Session, language_code: str) -> list[tuple[int, str]] | None:
    """Return (category_id, name) for the given language code, if the category is not available in the requested language, fall back to the fallback language."""
    try:
        requested = aliased(Localization)
        fallback = aliased(Localization)
        statement = (
            select(
                RecipeCategory.category_id, func.coalesce(requested.text_value, fallback.text_value)
            )
            .outerjoin(
                requested,
                and_(
                    requested.text_id == RecipeCategory.name_text_id,
                    requested.language_code == language_code,
                ),
            )
            .join(
                fallback,
                and_(
                    fallback.text_id == RecipeCategory.name_text_id,
                    fallback.language_code == FALLBACK_LANGUAGE_CODE,
                ),
            )
            .order_by(RecipeCategory.category_id)
        )
        return [(row_id, name) for row_id, name in session.execute(statement)]

    except Exception as e:
        logger.exception("Failed to lookup categories", exc_info=e)
        return None


def lookup_ingredients_suggestions(
    session: Session, text: str, language_code: str, limit: int
) -> list[tuple[int, str]] | None:
    """Return (ingredient_id, name) pairs whose name contains the text."""
    try:
        if session.get(Language, language_code) is None:
            return []

        requested_name = aliased(Localization)
        fallback_name = aliased(Localization)
        name = func.coalesce(requested_name.text_value, fallback_name.text_value)

        statement = (
            select(Ingredient.ingredient_id, name)
            .outerjoin(
                requested_name,
                and_(
                    requested_name.text_id == Ingredient.name_text_id,
                    requested_name.language_code == language_code,
                ),
            )
            .join(
                fallback_name,
                and_(
                    fallback_name.text_id == Ingredient.name_text_id,
                    fallback_name.language_code == FALLBACK_LANGUAGE_CODE,
                ),
            )
            .where(name.icontains(text, autoescape=True))
            .order_by(
                case(
                    (name.istartswith(text, autoescape=True), NAME_STARTS_WITH_TEXT_RANK),
                    else_=NAME_CONTAINS_TEXT_RANK,
                ),
                name,
            )
            .limit(limit)
        )
        return [(row_id, name) for row_id, name in session.execute(statement)]

    except Exception as e:
        logger.exception("Failed to lookup ingredients suggestions", exc_info=e)
        return None


def get_all_ingredients_for_language(
    session: Session, language_code: str
) -> list[tuple[int, str]] | None:
    try:
        statement = select(Ingredient.ingredient_id, Localization.text_value)
        statement = statement.join(Localization, Ingredient.name_text_id == Localization.text_id)
        statement = statement.where(Localization.language_code == language_code)

        result = session.execute(statement).tuples().all()

        return [(ingredient_id, text_value) for ingredient_id, text_value in result]

    except Exception as e:
        logger.exception("Failed to get all ingredients for language", exc_info=e)
        return None
