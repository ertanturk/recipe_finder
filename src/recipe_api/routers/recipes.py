"""Recipe endpoints: search."""

import time
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Path, status

from recipe_api.queries.recipes import RecipeNotFoundError, lookup_recipe
from recipe_api.queries.search import search_recipes
from recipe_api.routers.lookup import (
    DEFAULT_LANGUAGE_CODE,
    LanguageCodeQuery,
    RecipeSession,
    raise_db_unavailable,
)
from recipe_api.settings import get_settings
from recipe_api.telemetry import record_query, record_query_failure
from recipe_finder.schemas import RecipeResponse, SearchRequest, SearchResponse

router = APIRouter()
RECIPE_NOT_FOUND_CODE = "recipe_not_found"


@router.post("/search")
def search(
    request: SearchRequest,
    session: RecipeSession,
    api_session_id: Annotated[int | None, Header(alias="X-Session-Id")] = None,
) -> SearchResponse:
    """Return the ordered recipe ids that match the search, with the real total."""
    started_at = time.perf_counter()
    result = search_recipes(session, request, get_settings().SEARCH_LIMIT)
    if result is None:
        record_query_failure(api_session_id, "search")
        raise_db_unavailable()
    recipe_ids, total = result
    record_query(api_session_id, "search", started_at, total)
    return SearchResponse(recipe_ids=recipe_ids, total=total)


@router.get("/recipes/{recipe_id}")
def get_recipe(
    recipe_id: Annotated[int, Path(ge=1)],
    session: RecipeSession,
    lang: LanguageCodeQuery = DEFAULT_LANGUAGE_CODE,
    api_session_id: Annotated[int | None, Header(alias="X-Session-Id")] = None,
) -> RecipeResponse:
    """Return one full recipe in the given language."""
    started_at = time.perf_counter()
    try:
        recipe = lookup_recipe(session, recipe_id, lang)
    except RecipeNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=RECIPE_NOT_FOUND_CODE
        ) from None
    if recipe is None:
        record_query_failure(api_session_id, "recipe")
        raise_db_unavailable()
    record_query(api_session_id, "recipe", started_at, 1)
    return recipe
