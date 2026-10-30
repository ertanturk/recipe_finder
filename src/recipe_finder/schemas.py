"""Data models shared by the CLI and the API."""

from datetime import datetime
from typing import Any, Literal, Self

from pydantic import BaseModel, Field, NonNegativeFloat, PositiveInt, model_validator

MAX_APP_VERSION_LENGTH = 20
DEFAULT_LANGUAGE_CODE = "en"
MAX_LANGUAGE_CODE_LENGTH = 10
MAX_INGREDIENT_IDS = 50

EventType = Literal[
    "db_connection_opened",
    "db_connection_failed",
    "db_query_completed",
    "db_query_failed",
    "search_executed",
    "no_results",
    "recipe_clicked",
    "recipe_skipped",
    "invalid_input",
    "language_changed",
    "error",
]


class LanguageResponse(BaseModel):
    """One language in the language list."""

    language_code: str
    language_name: str


class CategoryResponse(BaseModel):
    """One category, named in the requested language."""

    category_id: int
    name: str


class IngredientSuggestionResponse(BaseModel):
    """One ingredient suggestion, named in the requested language."""

    ingredient_id: int
    name: str


class SearchRequest(BaseModel):
    """Body of POST /search. A field that is None is not used as a filter."""

    lang: str = Field(
        default=DEFAULT_LANGUAGE_CODE, min_length=1, max_length=MAX_LANGUAGE_CODE_LENGTH
    )
    ingredient_ids: list[PositiveInt] = Field(default_factory=list, max_length=MAX_INGREDIENT_IDS)
    max_calorie: NonNegativeFloat | None = None
    min_protein: NonNegativeFloat | None = None
    min_carbohydrate: NonNegativeFloat | None = None
    min_fat: NonNegativeFloat | None = None
    min_fiber: NonNegativeFloat | None = None
    min_sugar: NonNegativeFloat | None = None
    min_sodium: NonNegativeFloat | None = None
    category_id: PositiveInt | None = None


class SearchResponse(BaseModel):
    """Answer of POST /search."""

    recipe_ids: list[int]
    total: int


class NutritionResponse(BaseModel):
    """Nutrition totals of the whole recipe."""

    calorie: float
    protein: float
    carbohydrate: float
    fat: float
    fiber: float
    sugar: float
    sodium: float


class RecipeIngredientResponse(BaseModel):
    """One ingredient of a recipe, with its quantity in grams."""

    ingredient_id: int
    name: str
    quantity_grams: float


class RecipeResponse(BaseModel):
    """Answer of GET /recipes/{id}."""

    recipe_id: int
    name: str
    instructions: str
    prep_time_minutes: int
    categories: list[CategoryResponse]
    nutrition: NutritionResponse
    ingredients: list[RecipeIngredientResponse]


class SessionStartRequest(BaseModel):
    """Body of POST /sessions."""

    app_version: str = Field(min_length=1, max_length=MAX_APP_VERSION_LENGTH)
    language_code: str = Field(min_length=1, max_length=MAX_LANGUAGE_CODE_LENGTH)


class SessionStartResponse(BaseModel):
    """Answer of POST /sessions."""

    session_id: int


class SessionUpdateRequest(BaseModel):
    """Body of PATCH /sessions/{id}. At least one field is required."""

    language_code: str | None = Field(
        default=None, min_length=1, max_length=MAX_LANGUAGE_CODE_LENGTH
    )
    ended_at: datetime | None = None

    @model_validator(mode="after")
    def require_one_field(self) -> Self:
        """Reject a body that changes nothing."""
        if self.language_code is None and self.ended_at is None:
            raise ValueError("language_code or ended_at is required")
        return self


class EventRequest(BaseModel):
    """Body of POST /events."""

    session_id: PositiveInt
    event_type: EventType
    event_data: dict[str, Any]
    event_time: datetime
