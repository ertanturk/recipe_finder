from collections.abc import Iterator

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from recipe_api.database import get_recipe_engine
from recipe_api.models_recipe import Localization, Recipe


@pytest.fixture
def recipe_session() -> Iterator[Session]:
    """Give a read-only session on the seeded Recipe DB of the local SQL Server."""
    with Session(get_recipe_engine()) as session:
        yield session


@pytest.fixture
def recipe_ids_by_name(recipe_session: Session) -> dict[str, int]:
    """Map each English recipe name to its id in the seeded Recipe DB."""
    statement = (
        select(Localization.text_value, Recipe.recipe_id)
        .join(Recipe, Recipe.name_text_id == Localization.text_id)
        .where(Localization.language_code == "en")
    )
    return {name: recipe_id for name, recipe_id in recipe_session.execute(statement)}
