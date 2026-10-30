import sys
from pathlib import Path

import pytest

from recipe_finder.schemas import (
    CategoryResponse,
    NutritionResponse,
    RecipeResponse,
)

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


@pytest.fixture(autouse=True)
def isolate_user_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure tests never read from or corrupt the user's real cache directory."""
    monkeypatch.setattr("recipe_finder.cache.user_cache_dir", lambda *args, **kwargs: str(tmp_path))


@pytest.fixture
def sample_recipe() -> RecipeResponse:
    """Return a small recipe response for CLI screen tests."""
    return RecipeResponse(
        recipe_id=1,
        name="Sample recipe",
        instructions="1. Cook the ingredients.",
        prep_time_minutes=15,
        categories=[CategoryResponse(category_id=1, name="Dinner")],
        nutrition=NutritionResponse(
            calorie=400,
            protein=25,
            carbohydrate=45,
            fat=12,
            fiber=5,
            sugar=4,
            sodium=300,
        ),
        ingredients=[],
    )
