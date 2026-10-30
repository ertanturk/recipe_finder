import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from recipe_api.models_recipe import Localization, Recipe
from recipe_api.queries.lookup import lookup_categories, lookup_ingredients_suggestions
from recipe_api.queries.search import search_recipes
from recipe_finder.schemas import SearchRequest

pytestmark = pytest.mark.integration

SEARCH_LIMIT = 100
LANGUAGE_CODE = "en"
SUGGESTION_LIMIT = 8
GRILLED_CHICKEN = "Grilled Chicken with Rice"
OATMEAL = "Protein Oatmeal Bowl"
SCRAMBLED_EGGS = "Scrambled Eggs"


def get_recipe_ids_by_name(session: Session) -> dict[str, int]:
    statement = (
        select(Localization.text_value, Recipe.recipe_id)
        .join(Recipe, Recipe.name_text_id == Localization.text_id)
        .where(Localization.language_code == LANGUAGE_CODE)
    )
    return {name: recipe_id for name, recipe_id in session.execute(statement)}


def get_ingredient_id(session: Session, name: str) -> int:
    suggestions = lookup_ingredients_suggestions(session, name, LANGUAGE_CODE, SUGGESTION_LIMIT)
    assert suggestions is not None
    return next(ingredient_id for ingredient_id, found_name in suggestions if found_name == name)


def get_category_id(session: Session, name: str) -> int:
    categories = lookup_categories(session, LANGUAGE_CODE)
    assert categories is not None
    return next(category_id for category_id, found_name in categories if found_name == name)


def test_no_filters_returns_all_recipes_fewest_ingredients_first(recipe_session: Session) -> None:
    ids = get_recipe_ids_by_name(recipe_session)

    result = search_recipes(recipe_session, SearchRequest(), SEARCH_LIMIT)

    assert result == ([ids[SCRAMBLED_EGGS], ids[GRILLED_CHICKEN], ids[OATMEAL]], 3)


def test_max_calorie_keeps_only_light_recipes(recipe_session: Session) -> None:
    ids = get_recipe_ids_by_name(recipe_session)

    result = search_recipes(recipe_session, SearchRequest(max_calorie=500), SEARCH_LIMIT)

    assert result == ([ids[SCRAMBLED_EGGS], ids[OATMEAL]], 2)


def test_max_calorie_zero_is_a_real_filter(recipe_session: Session) -> None:
    result = search_recipes(recipe_session, SearchRequest(max_calorie=0), SEARCH_LIMIT)

    assert result == ([], 0)


def test_min_protein_keeps_only_high_protein_recipes(recipe_session: Session) -> None:
    ids = get_recipe_ids_by_name(recipe_session)

    result = search_recipes(recipe_session, SearchRequest(min_protein=30), SEARCH_LIMIT)

    assert result == ([ids[GRILLED_CHICKEN]], 1)


def test_category_filter_keeps_only_recipes_in_category(recipe_session: Session) -> None:
    ids = get_recipe_ids_by_name(recipe_session)
    dinner_id = get_category_id(recipe_session, "Dinner")

    result = search_recipes(recipe_session, SearchRequest(category_id=dinner_id), SEARCH_LIMIT)

    assert result == ([ids[GRILLED_CHICKEN]], 1)


def test_ingredients_filter_and_sort_by_most_matches(recipe_session: Session) -> None:
    ids = get_recipe_ids_by_name(recipe_session)
    ingredient_ids = [
        get_ingredient_id(recipe_session, "chicken breast"),
        get_ingredient_id(recipe_session, "olive oil"),
    ]

    result = search_recipes(
        recipe_session, SearchRequest(ingredient_ids=ingredient_ids), SEARCH_LIMIT
    )

    assert result == ([ids[GRILLED_CHICKEN], ids[SCRAMBLED_EGGS]], 2)


def test_limit_cuts_the_list_but_total_stays_real(recipe_session: Session) -> None:
    limit = 2

    result = search_recipes(recipe_session, SearchRequest(), limit)

    assert result is not None
    recipe_ids, total = result
    assert len(recipe_ids) == limit
    assert total == 3
