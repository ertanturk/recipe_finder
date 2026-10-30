"""Tests for screen rendering functions."""

from recipe_finder.schemas import (
    CategoryResponse,
    NutritionResponse,
    RecipeResponse,
)
from recipe_finder.screens.main_menu import render_main_menu
from recipe_finder.screens.notices import (
    render_end_of_results_screen,
    render_error_screen,
    render_no_results_screen,
)
from recipe_finder.screens.recipe_view import render_recipe_view


def test_render_main_menu() -> None:
    output = render_main_menu(selected_index=0, lang="en", no_color=True)
    assert "Recipe Finder" in output
    assert "Search" in output
    assert "> Search" in output or ">" in output
    assert "Change language" in output
    assert "Exit" in output


def test_render_error_screen() -> None:
    output = render_error_screen(
        message="Cannot reach server",
        selected_index=0,
        lang="en",
        allow_retry=True,
        no_color=True,
    )
    assert "Something went wrong" in output
    assert "Cannot reach server" in output
    assert "Retry" in output
    assert "Main menu" in output


def test_render_no_results_screen() -> None:
    output = render_no_results_screen(
        selected_index=0,
        hint="Try fewer ingredients",
        lang="en",
        no_color=True,
    )
    assert "No recipes found" in output
    assert "Try fewer ingredients" in output
    assert "Edit search" in output


def test_render_end_of_results_screen() -> None:
    output = render_end_of_results_screen(selected_index=0, lang="en", no_color=True)
    assert "End of results" in output
    assert "New search" in output


def test_render_recipe_view_wraps_numbered_instructions() -> None:
    recipe = RecipeResponse(
        recipe_id=1,
        name="Rice",
        instructions=(
            "1. Wash the raw rice thoroughly with warm water until the water runs clear.\n"
            "2. Heat olive oil in a pan, add the rice and sauté for 3-4 minutes until translucent."
        ),
        prep_time_minutes=10,
        categories=[CategoryResponse(category_id=1, name="Dinner")],
        nutrition=NutritionResponse(
            calorie=100,
            protein=5,
            carbohydrate=20,
            fat=2,
            fiber=1,
            sugar=1,
            sodium=10,
        ),
        ingredients=[],
    )

    output = render_recipe_view(recipe, position=1, total=1, width=60, no_color=True)

    assert "until\n" not in output
    assert "\n       for 3-4 minutes until translucent." in output


def test_render_recipe_view_keeps_chosen_recipe_open() -> None:
    recipe = RecipeResponse(
        recipe_id=1,
        name="Rice",
        instructions="1. Cook the rice.",
        prep_time_minutes=10,
        categories=[],
        nutrition=NutritionResponse(
            calorie=100,
            protein=5,
            carbohydrate=20,
            fat=2,
            fiber=1,
            sugar=1,
            sodium=10,
        ),
        ingredients=[],
    )

    output = render_recipe_view(recipe, position=1, total=1, chosen=True, no_color=True)

    assert "Recipe chosen. Enjoy your meal!" in output
    assert "Main menu: Esc" in output
    assert "Enter Choose" not in output
