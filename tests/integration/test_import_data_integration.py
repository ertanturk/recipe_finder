"""Integration tests for import_data tool against real SQL Server."""

from collections.abc import Iterator

import pytest
from sqlalchemy.orm import Session

from tools.import_data import (
    create_text,
    execute_import,
    get_admin_engine,
    import_ingredients,
    import_recipes,
    load_existing,
)
from tools.model_data import (
    Cookbook,
    IngredientDefinition,
    LocalizedString,
    NutritionalValues,
    Recipe,
    RecipeIngredient,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def admin_session() -> Iterator[Session]:
    """Yield an admin session and roll back changes on teardown."""
    engine = get_admin_engine()
    with Session(engine) as session:
        try:
            yield session
        finally:
            session.rollback()


def _make_nutrition() -> NutritionalValues:
    return NutritionalValues(
        calorie=150.0,
        protein=5.0,
        fat=10.0,
        carbohydrate=10.0,
        sugar=2.0,
        fiber=3.0,
        sodium=30.0,
    )


def test_load_existing_loads_seeded_data(admin_session: Session) -> None:
    existing = load_existing(admin_session)

    assert "breakfast" in existing.categories
    assert "lunch" in existing.categories
    assert "chicken breast" in existing.ingredients
    assert "scrambled eggs" in existing.recipes


def test_create_text(admin_session: Session) -> None:
    text_id = create_text(
        admin_session,
        LocalizedString(en="Unique Test Item", tr="Benzersiz Test Öğesi"),
    )
    assert text_id > 0


def test_import_ingredients_skips_and_adds(admin_session: Session) -> None:
    existing = load_existing(admin_session)
    assert "chicken breast" in existing.ingredients
    initial_count = len(existing.ingredients)

    cookbook = Cookbook(
        ingredients=[
            IngredientDefinition(
                name=LocalizedString(en="chicken breast", tr="tavuk göğsü"),
                per_100g=_make_nutrition(),
            ),
            IngredientDefinition(
                name=LocalizedString(en="almond flour", tr="badem unu"),
                per_100g=_make_nutrition(),
            ),
        ],
        recipes=[],
    )

    stats = import_ingredients(admin_session, cookbook, existing)
    assert stats.skipped == 1
    assert stats.added == 1
    assert "almond flour" in existing.ingredients
    assert len(existing.ingredients) == initial_count + 1


def test_import_recipes_skips_and_adds(admin_session: Session) -> None:
    existing = load_existing(admin_session)
    initial_recipe_count = len(existing.recipes)

    cookbook = Cookbook(
        ingredients=[],
        recipes=[
            Recipe(
                name=LocalizedString(en="Scrambled Eggs", tr="Çırpılmış Yumurta"),
                instructions=LocalizedString(en="Cook eggs", tr="Yumurtaları pişir"),
                prep_time_minutes=5,
                categories=["breakfast"],
                ingredients=[RecipeIngredient(name="egg", grams=100.0)],
            ),
            Recipe(
                name=LocalizedString(en="Oatmeal Snack", tr="Yulaf Atıştırmalığı"),
                instructions=LocalizedString(en="Mix oats", tr="Yulafları karıştır"),
                prep_time_minutes=5,
                categories=["snack"],
                ingredients=[RecipeIngredient(name="rolled oats", grams=50.0)],
            ),
        ],
    )

    stats = import_recipes(admin_session, cookbook, existing)
    assert stats.skipped == 1
    assert stats.added == 1
    assert "oatmeal snack" in existing.recipes
    assert len(existing.recipes) == initial_recipe_count + 1


def test_execute_import_dry_run_leaves_database_clean(
    admin_session: Session, capsys: pytest.CaptureFixture[str]
) -> None:
    cookbook = Cookbook(
        ingredients=[
            IngredientDefinition(
                name=LocalizedString(en="DryRun Ingredient", tr="Deneme Malzemesi"),
                per_100g=_make_nutrition(),
            )
        ],
        recipes=[
            Recipe(
                name=LocalizedString(en="DryRun Recipe", tr="Deneme Tarifi"),
                instructions=LocalizedString(en="Mix and serve", tr="Karıştır ve servis et"),
                prep_time_minutes=15,
                categories=["lunch"],
                ingredients=[RecipeIngredient(name="DryRun Ingredient", grams=80.0)],
            )
        ],
    )

    ing_stats, rec_stats = execute_import(admin_session, cookbook, dry_run=True)
    assert ing_stats.added == 1
    assert ing_stats.skipped == 0
    assert rec_stats.added == 1
    assert rec_stats.skipped == 0

    output = capsys.readouterr().out
    assert "1 ingredients added, 0 skipped, 1 recipes added, 0 skipped" in output
    assert "All database changes have been rolled back" in output
    assert "Remember to run db/check_rules.sql" in output

    fresh_existing = load_existing(admin_session)
    assert "dryrun ingredient" not in fresh_existing.ingredients
    assert "dryrun recipe" not in fresh_existing.recipes


def test_execute_import_exits_on_problem(admin_session: Session) -> None:
    cookbook = Cookbook(
        ingredients=[],
        recipes=[
            Recipe(
                name=LocalizedString(en="Faulty Recipe", tr="Hatalı Tarif"),
                instructions=LocalizedString(en="Fail", tr="Başarısız"),
                prep_time_minutes=10,
                categories=["dinner"],
                ingredients=[RecipeIngredient(name="nonexistent item", grams=100.0)],
            )
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        execute_import(admin_session, cookbook, dry_run=True)

    assert exc_info.value.code == 1
