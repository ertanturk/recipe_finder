import pytest
from sqlalchemy.orm import Session

from recipe_api.queries.lookup import (
    lookup_categories,
    lookup_ingredients_suggestions,
    lookup_languages,
)

pytestmark = pytest.mark.integration

SUGGESTION_LIMIT = 8
UNKNOWN_LANGUAGE_CODE = "xx"
ENGLISH_CATEGORY_NAMES = {"Breakfast", "Lunch", "Dinner", "Snack"}
TURKISH_CATEGORY_NAMES = {"Kahvaltı", "Öğle Yemeği", "Akşam Yemeği", "Atıştırmalık"}


def test_lookup_languages_returns_seeded_languages_ordered_by_name(
    recipe_session: Session,
) -> None:
    languages = lookup_languages(recipe_session)

    assert languages is not None
    assert [(language.language_code, language.language_name) for language in languages] == [
        ("en", "English"),
        ("tr", "Turkish"),
    ]


@pytest.mark.parametrize(
    ("language_code", "expected_names"),
    [
        ("en", ENGLISH_CATEGORY_NAMES),
        ("tr", TURKISH_CATEGORY_NAMES),
        (UNKNOWN_LANGUAGE_CODE, ENGLISH_CATEGORY_NAMES),
    ],
)
def test_lookup_categories_returns_names_in_language_with_en_fallback(
    recipe_session: Session, language_code: str, expected_names: set[str]
) -> None:
    categories = lookup_categories(recipe_session, language_code)

    assert categories is not None
    assert {name for _, name in categories} == expected_names


def test_lookup_categories_returns_each_category_once(recipe_session: Session) -> None:
    categories = lookup_categories(recipe_session, "en")

    assert categories is not None
    category_ids = [category_id for category_id, _ in categories]
    assert len(category_ids) == len(set(category_ids))


@pytest.mark.parametrize(
    ("language_code", "text", "expected_name"),
    [
        ("en", "chick", "chicken breast"),
        ("en", "CHICK", "chicken breast"),
        ("en", "breast", "chicken breast"),
        ("tr", "tavuk", "tavuk göğsü"),
    ],
)
def test_suggestions_match_text_inside_name_ignoring_case(
    recipe_session: Session, language_code: str, text: str, expected_name: str
) -> None:
    suggestions = lookup_ingredients_suggestions(
        recipe_session, text, language_code, SUGGESTION_LIMIT
    )

    assert suggestions is not None
    assert expected_name in [name for _, name in suggestions]


def test_suggestions_return_empty_list_for_unknown_language(recipe_session: Session) -> None:
    suggestions = lookup_ingredients_suggestions(
        recipe_session, "chick", UNKNOWN_LANGUAGE_CODE, SUGGESTION_LIMIT
    )

    assert suggestions == []


def test_suggestions_treat_percent_sign_as_plain_text(recipe_session: Session) -> None:
    suggestions = lookup_ingredients_suggestions(recipe_session, "%", "en", SUGGESTION_LIMIT)

    assert suggestions == []


def test_suggestions_respect_limit(recipe_session: Session) -> None:
    limit = 2

    suggestions = lookup_ingredients_suggestions(recipe_session, "e", "en", limit)

    assert suggestions is not None
    assert len(suggestions) == limit


def test_suggestions_put_names_starting_with_text_first(recipe_session: Session) -> None:
    text = "e"

    suggestions = lookup_ingredients_suggestions(recipe_session, text, "en", SUGGESTION_LIMIT)

    assert suggestions is not None
    starts_with_flags = [name.lower().startswith(text) for _, name in suggestions]
    assert len(suggestions) > 1
    assert starts_with_flags == sorted(starts_with_flags, reverse=True)
