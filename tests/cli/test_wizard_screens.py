"""Tests for search wizard rendering functions."""

from recipe_finder.schemas import CategoryResponse
from recipe_finder.screens.recipe_view import render_recipe_results_summary
from recipe_finder.screens.wizard import (
    NUTRIENT_METRICS,
    render_wizard_review,
    render_wizard_step1,
    render_wizard_step2_input,
    render_wizard_step2_select,
    render_wizard_step3_category,
)
from recipe_finder.state import SearchCriteria


def test_render_wizard_step1_with_chips_and_suggestions() -> None:
    output = render_wizard_step1(
        chips=["chicken breast", "rice"],
        query="on",
        suggestions=["onion", "green onion"],
        selected_suggestion_index=0,
        no_match=False,
        lang="en",
        no_color=True,
    )
    assert "Step 1/3: What do you have?" in output
    assert "[chicken breast]" in output
    assert "[rice]" in output
    assert "> on" in output or "on" in output
    assert "onion" in output
    assert "> onion" in output


def test_render_wizard_step1_no_match() -> None:
    output = render_wizard_step1(
        chips=[],
        query="xyz",
        suggestions=[],
        selected_suggestion_index=0,
        no_match=True,
        lang="en",
        no_color=True,
    )
    assert "No ingredient found" in output


def test_render_wizard_step2_select() -> None:
    output = render_wizard_step2_select(
        selected_index=0,
        checked_keys={"calories", "protein"},
        lang="en",
        no_color=True,
    )
    assert "Step 2/3: Nutrition" in output
    assert "[x] Calories (max kcal)" in output
    assert "[x] Protein (min g)" in output
    assert "[ ] Carbohydrate (min g)" in output


def test_render_wizard_step2_input() -> None:
    metric = NUTRIENT_METRICS[0]  # Calories
    output = render_wizard_step2_input(
        metric=metric,
        input_value="600",
        error_message="Must be 0 or more",
        lang="en",
        no_color=True,
    )
    assert "Step 2/3: Nutrition" in output
    assert "Enter value for Calories (max kcal)" in output
    assert "600" in output
    assert "Must be 0 or more" in output


def test_render_wizard_step3_category() -> None:
    categories = [
        CategoryResponse(category_id=1, name="Breakfast"),
        CategoryResponse(category_id=2, name="Dinner"),
    ]
    output = render_wizard_step3_category(
        categories=categories,
        selected_index=1,
        lang="en",
        no_color=True,
    )
    assert "Step 3/3: Category" in output
    assert "Any" in output
    assert "> Breakfast" in output
    assert "Dinner" in output


def test_render_wizard_review() -> None:
    criteria = SearchCriteria(
        ingredient_names=["chicken breast", "rice"],
        ingredient_ids=[1, 2],
        max_calorie=600.0,
        min_protein=30.0,
        category_name="Dinner",
    )
    output = render_wizard_review(
        criteria=criteria,
        selected_option_index=0,
        validation_error="",
        lang="en",
        no_color=True,
    )
    assert "Your search" in output
    assert "chicken breast, rice" in output
    assert "max 600 kcal" in output
    assert "min 30 g" in output
    assert "Dinner" in output
    assert "> Search" in output
    assert "Edit" in output
    assert "Cancel" in output


def test_render_wizard_review_validation_error() -> None:
    criteria = SearchCriteria()
    output = render_wizard_review(
        criteria=criteria,
        selected_option_index=0,
        validation_error="Please set at least one filter before searching.",
        lang="en",
        no_color=True,
    )
    assert "Please set at least one filter before searching." in output


def test_render_recipe_results_summary() -> None:
    output = render_recipe_results_summary(total_found=5, lang="en", no_color=True)
    assert "Found 5 matching recipe(s)." in output
