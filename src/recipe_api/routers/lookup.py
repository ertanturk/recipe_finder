"""Lookup endpoints: languages, categories, and ingredient suggestions."""

import time
from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from recipe_api.database import get_recipe_session
from recipe_api.queries.lookup import (
    get_all_ingredients_for_language,
    lookup_categories,
    lookup_ingredients_suggestions,
    lookup_languages,
)
from recipe_api.telemetry import record_query, record_query_failure
from recipe_finder.schemas import (
    CategoryResponse,
    IngredientSuggestionResponse,
    LanguageResponse,
)

DEFAULT_LANGUAGE_CODE = "en"
MAX_LANGUAGE_CODE_LENGTH = 10
MAX_SUGGEST_TEXT_LENGTH = 100
DEFAULT_SUGGEST_LIMIT = 8
MAX_SUGGEST_LIMIT = 20
DB_UNAVAILABLE_CODE = "db_unavailable"

router = APIRouter()

RecipeSession = Annotated[Session, Depends(get_recipe_session)]
LanguageCodeQuery = Annotated[str, Query(min_length=1, max_length=MAX_LANGUAGE_CODE_LENGTH)]
ApiSessionId = Annotated[int | None, Header(alias="X-Session-Id")]
SuggestTextQuery = Annotated[str, Query(min_length=1, max_length=MAX_SUGGEST_TEXT_LENGTH)]
SuggestLimitQuery = Annotated[int, Query(ge=1, le=MAX_SUGGEST_LIMIT)]


def raise_db_unavailable() -> NoReturn:
    """Answer 503 with a short code, never with technical error text."""
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=DB_UNAVAILABLE_CODE)


@router.get("/languages")
def get_languages(
    session: RecipeSession, api_session_id: ApiSessionId = None
) -> list[LanguageResponse]:
    """List all languages."""
    started_at = time.perf_counter()
    languages = lookup_languages(session)
    if languages is None:
        record_query_failure(api_session_id, "languages")
        raise_db_unavailable()
    record_query(api_session_id, "languages", started_at, len(languages))
    return [
        LanguageResponse(language_code=language.language_code, language_name=language.language_name)
        for language in languages
    ]


@router.get("/categories")
def get_categories(
    session: RecipeSession,
    lang: LanguageCodeQuery = DEFAULT_LANGUAGE_CODE,
    api_session_id: ApiSessionId = None,
) -> list[CategoryResponse]:
    """List all categories, named in the given language."""
    started_at = time.perf_counter()
    categories = lookup_categories(session, lang)
    if categories is None:
        record_query_failure(api_session_id, "categories")
        raise_db_unavailable()
    record_query(api_session_id, "categories", started_at, len(categories))
    return [
        CategoryResponse(category_id=category_id, name=name) for category_id, name in categories
    ]


@router.get("/ingredients/suggest")
def suggest_ingredients(
    session: RecipeSession,
    q: SuggestTextQuery,
    lang: LanguageCodeQuery = DEFAULT_LANGUAGE_CODE,
    limit: SuggestLimitQuery = DEFAULT_SUGGEST_LIMIT,
    api_session_id: ApiSessionId = None,
) -> list[IngredientSuggestionResponse]:
    """Suggest ingredients whose name contains the text."""
    started_at = time.perf_counter()
    suggestions = lookup_ingredients_suggestions(session, q, lang, limit)
    if suggestions is None:
        record_query_failure(api_session_id, "ingredient_suggest")
        raise_db_unavailable()
    record_query(api_session_id, "ingredient_suggest", started_at, len(suggestions))
    return [
        IngredientSuggestionResponse(ingredient_id=ingredient_id, name=name)
        for ingredient_id, name in suggestions
    ]


@router.get("/ingredients")
def get_all_ingredients(
    session: RecipeSession,
    lang: LanguageCodeQuery = DEFAULT_LANGUAGE_CODE,
    api_session_id: ApiSessionId = None,
) -> list[IngredientSuggestionResponse]:
    """List all ingredients, named in the given language."""
    started_at = time.perf_counter()
    ingredients = get_all_ingredients_for_language(session, lang)
    if ingredients is None:
        record_query_failure(api_session_id, "ingredients")
        raise_db_unavailable()
    record_query(api_session_id, "ingredients", started_at, len(ingredients))
    return [
        IngredientSuggestionResponse(ingredient_id=ingredient_id, name=name)
        for ingredient_id, name in ingredients
    ]
