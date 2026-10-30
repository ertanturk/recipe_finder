"""Unit tests for import_data tool (no database required)."""

from pathlib import Path

from typer.testing import CliRunner

from tools.import_data import (
    ExistingIds,
    app,
    find_problems,
    load_cookbook,
)
from tools.model_data import (
    Cookbook,
    IngredientDefinition,
    LocalizedString,
    NutritionalValues,
    Recipe,
    RecipeIngredient,
)


def _make_nutrition() -> NutritionalValues:
    return NutritionalValues(
        calorie=100.0,
        protein=10.0,
        fat=2.0,
        carbohydrate=10.0,
        sugar=1.0,
        fiber=1.0,
        sodium=20.0,
    )


def test_load_cookbook(tmp_path: Path) -> None:
    sample_json = """{
        "ingredients": [
            {
                "name": {"en": "Tomato", "tr": "Domates"},
                "per_100g": {
                    "calorie": 18,
                    "protein": 0.9,
                    "fat": 0.2,
                    "carbohydrate": 3.9,
                    "sugar": 2.6,
                    "fiber": 1.2,
                    "sodium": 5
                }
            }
        ],
        "recipes": []
    }"""
    file_path = tmp_path / "cookbook.json"
    file_path.write_text(sample_json, encoding="utf-8")

    cookbook = load_cookbook(file_path)
    assert len(cookbook.ingredients) == 1
    assert cookbook.ingredients[0].name.en == "Tomato"
    assert cookbook.ingredients[0].name.tr == "Domates"


def test_find_problems_all_present() -> None:
    cookbook = Cookbook(
        ingredients=[],
        recipes=[
            Recipe(
                name=LocalizedString(en="Salad", tr="Salata"),
                instructions=LocalizedString(en="Mix it", tr="Karıştır"),
                prep_time_minutes=10,
                categories=["lunch"],
                ingredients=[RecipeIngredient(name="Tomato", grams=100.0)],
            )
        ],
    )
    existing = ExistingIds(
        ingredients={"tomato": 1},
        recipes={},
        categories={"lunch": 1},
    )

    problems = find_problems(cookbook, existing)
    assert problems == []


def test_find_problems_ingredient_defined_in_file() -> None:
    cookbook = Cookbook(
        ingredients=[
            IngredientDefinition(
                name=LocalizedString(en="Cucumber", tr="Salatalık"),
                per_100g=_make_nutrition(),
            )
        ],
        recipes=[
            Recipe(
                name=LocalizedString(en="Salad", tr="Salata"),
                instructions=LocalizedString(en="Mix", tr="Karıştır"),
                prep_time_minutes=5,
                categories=["lunch"],
                ingredients=[RecipeIngredient(name="cucumber", grams=50.0)],
            )
        ],
    )
    existing = ExistingIds(
        ingredients={},
        recipes={},
        categories={"lunch": 1},
    )

    problems = find_problems(cookbook, existing)
    assert problems == []


def test_find_problems_missing_ingredient_and_category() -> None:
    cookbook = Cookbook(
        ingredients=[],
        recipes=[
            Recipe(
                name=LocalizedString(en="Mystery Dish", tr="Gizemli Yemek"),
                instructions=LocalizedString(en="Cook", tr="Pişir"),
                prep_time_minutes=20,
                categories=["dinner"],
                ingredients=[RecipeIngredient(name="dragon fruit", grams=100.0)],
            )
        ],
    )
    existing = ExistingIds(
        ingredients={"apple": 1},
        recipes={},
        categories={"breakfast": 1},  # "dinner" is missing
    )

    problems = find_problems(cookbook, existing)
    assert len(problems) == 2
    assert any("unknown ingredient: 'dragon fruit'" in p for p in problems)
    assert any("unknown category: 'dinner'" in p for p in problems)


def test_cli_help() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Import ingredients and recipes from a JSON file into RecipeDB" in result.output
    assert "--dry-run" in result.output


def test_cli_missing_file() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["nonexistent_file_path.json"])
    assert result.exit_code != 0
    assert "does not exist" in result.output


def test_cli_invalid_json(tmp_path: Path) -> None:
    runner = CliRunner()
    invalid_file = tmp_path / "broken.json"
    invalid_file.write_text("{broken json", encoding="utf-8")

    result = runner.invoke(app, [str(invalid_file)])
    assert result.exit_code == 1
    assert "Failed to load cookbook file" in result.output
