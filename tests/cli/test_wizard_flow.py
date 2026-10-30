"""Tests for search wizard interactive flow and event tracking."""

from unittest.mock import MagicMock, patch

from recipe_finder.api_client import ApiClient, ApiClientError
from recipe_finder.cache import IngredientCache
from recipe_finder.schemas import (
    CategoryResponse,
    IngredientSuggestionResponse,
    SearchResponse,
)
from recipe_finder.screens.wizard import (
    NUTRIENT_METRICS,
    _WizardSession,
    show_search_wizard,
)
from recipe_finder.state import SearchCriteria
from recipe_finder.telemetry import clear_tracked_events, get_tracked_events


def _create_mock_cache() -> IngredientCache:
    items = [
        IngredientSuggestionResponse(ingredient_id=1, name="Chicken Breast"),
        IngredientSuggestionResponse(ingredient_id=2, name="Chicken Thigh"),
        IngredientSuggestionResponse(ingredient_id=3, name="Rice"),
        IngredientSuggestionResponse(ingredient_id=4, name="Olive Oil"),
    ]
    return IngredientCache(items)


def test_wizard_session_step1_navigation_and_tab() -> None:
    cache = _create_mock_cache()
    categories = [CategoryResponse(category_id=1, name="Dinner")]
    criteria = SearchCriteria()
    session = _WizardSession(cache, categories, criteria, lang="en")

    mock_app = MagicMock()

    # User types 'chick'
    for ch in "chick":
        session.on_char(ch, mock_app)

    assert session.step1_query == "chick"
    assert len(session.step1_suggestions) == 2
    assert session.step1_suggestions[0] == "Chicken Breast"

    # User presses Tab to accept suggestion
    session.on_tab(mock_app)
    assert criteria.ingredient_names == ["Chicken Breast"]
    assert criteria.ingredient_ids == [1]
    assert session.step1_query == ""

    # Backspace removes chip when query is empty
    session.on_backspace(mock_app)
    assert criteria.ingredient_names == []
    assert criteria.ingredient_ids == []


def test_wizard_session_step1_no_match_emits_telemetry() -> None:
    clear_tracked_events()
    cache = _create_mock_cache()
    categories = []
    criteria = SearchCriteria()
    session = _WizardSession(cache, categories, criteria, lang="en")
    mock_app = MagicMock()

    for ch in "xyz123":
        session.on_char(ch, mock_app)

    assert session.step1_no_match is True
    events = get_tracked_events()
    assert any(
        e["event_type"] == "invalid_input" and e["data"]["field"] == "ingredients" for e in events
    )


def test_wizard_session_step2_nutrition_toggle_and_validation() -> None:
    clear_tracked_events()
    cache = _create_mock_cache()
    categories = []
    criteria = SearchCriteria()
    session = _WizardSession(cache, categories, criteria, lang="en")
    mock_app = MagicMock()

    # Move from step 1 to step 2 by pressing Enter on empty query
    session.on_enter(mock_app)
    assert session.current_step == "nutrition_select"

    # Toggle Calories with Space
    session.on_space(mock_app)
    assert "calories" in session.step2_checked_metrics

    # Enter moves to numeric input for selected metric
    session.on_enter(mock_app)
    assert session.current_step == "nutrition_input"
    assert session.step2_input_metrics[0] == NUTRIENT_METRICS[0]

    # Type a negative number and press Enter -> validation failure
    session.step2_input_str = "-50"
    session.on_enter(mock_app)
    assert session.step2_error_msg != ""
    assert criteria.max_calorie is None
    events = get_tracked_events()
    assert any(
        e["event_type"] == "invalid_input" and e["data"]["field"] == "calories" for e in events
    )

    # Correct number to 600 and press Enter
    session.step2_input_str = "600"
    session.on_enter(mock_app)
    assert criteria.max_calorie == 600.0
    # Moves to step 3 (category)
    assert session.current_step == "category"


def test_wizard_session_step3_category_selection() -> None:
    cache = _create_mock_cache()
    categories = [
        CategoryResponse(category_id=1, name="Breakfast"),
        CategoryResponse(category_id=2, name="Dinner"),
    ]
    criteria = SearchCriteria()
    session = _WizardSession(cache, categories, criteria, lang="en")
    mock_app = MagicMock()

    session.current_step = "category"
    # Down moves to Breakfast (index 1)
    session.on_down(mock_app)
    assert session.step3_selected_idx == 1

    # Down moves to Dinner (index 2)
    session.on_down(mock_app)
    assert session.step3_selected_idx == 2

    session.on_enter(mock_app)
    assert criteria.category_id == 2
    assert criteria.category_name == "Dinner"
    assert session.current_step == "review"


def test_wizard_session_review_at_least_one_filter_rule() -> None:
    cache = _create_mock_cache()
    categories = []
    criteria = SearchCriteria()  # Empty!
    session = _WizardSession(cache, categories, criteria, lang="en")
    mock_app = MagicMock()

    session.current_step = "review"
    session.review_selected_idx = 0  # "search"
    session.on_enter(mock_app)

    # Blocked by validation
    assert session.review_validation_error != ""
    assert session.finished_action != "search"
    mock_app.exit.assert_not_called()


def test_wizard_session_esc_navigation() -> None:
    cache = _create_mock_cache()
    categories = []
    criteria = SearchCriteria()
    session = _WizardSession(cache, categories, criteria, lang="en")
    mock_app = MagicMock()

    session.current_step = "review"
    session.on_escape(mock_app)
    assert session.current_step == "category"

    session.on_escape(mock_app)
    assert session.current_step == "nutrition_select"

    session.on_escape(mock_app)
    assert session.current_step == "ingredients"

    session.on_escape(mock_app)
    assert session.finished_action == "cancel"
    mock_app.exit.assert_called_once()


def test_show_search_wizard_non_interactive() -> None:
    client = MagicMock(spec=ApiClient)
    with patch("recipe_finder.screens.wizard.is_interactive", return_value=False):
        action, _crit, recipe_ids = show_search_wizard(client)
        assert action == "cancel"
        assert recipe_ids == []


def test_show_search_wizard_success_flow() -> None:
    clear_tracked_events()
    client = MagicMock(spec=ApiClient)
    client.search.return_value = SearchResponse(recipe_ids=[1, 2, 3], total=3)
    client.get_categories.return_value = []

    criteria = SearchCriteria(ingredient_ids=[1], ingredient_names=["Chicken Breast"])

    with (
        patch("recipe_finder.screens.wizard.is_interactive", return_value=True),
        patch.object(_WizardSession, "run", return_value="search"),
    ):
        action, res_criteria, recipe_ids = show_search_wizard(client, criteria=criteria)

    assert action == "results"
    assert recipe_ids == [1, 2, 3]
    assert res_criteria.ingredient_ids == [1]

    events = get_tracked_events()
    assert any(e["event_type"] == "search_executed" for e in events)


def test_show_search_wizard_no_results_flow() -> None:
    clear_tracked_events()
    client = MagicMock(spec=ApiClient)
    client.search.return_value = SearchResponse(recipe_ids=[], total=0)
    client.get_categories.return_value = []

    criteria = SearchCriteria(ingredient_ids=[1], ingredient_names=["Chicken Breast"])

    with (
        patch("recipe_finder.screens.wizard.is_interactive", return_value=True),
        patch.object(_WizardSession, "run", return_value="search"),
        patch("recipe_finder.screens.notices.show_no_results_screen", return_value="main_menu"),
    ):
        action, _crit, recipe_ids = show_search_wizard(client, criteria=criteria)

    assert action == "main_menu"
    assert recipe_ids == []

    events = get_tracked_events()
    assert any(e["event_type"] == "no_results" for e in events)


def test_show_search_wizard_api_error_flow() -> None:
    clear_tracked_events()
    client = MagicMock(spec=ApiClient)
    client.search.side_effect = ApiClientError("Server error", error_code="server_unavailable")
    client.get_categories.return_value = []

    criteria = SearchCriteria(ingredient_ids=[1], ingredient_names=["Chicken"])

    with (
        patch("recipe_finder.screens.wizard.is_interactive", return_value=True),
        patch.object(_WizardSession, "run", return_value="search"),
        patch("recipe_finder.screens.notices.show_error_screen", return_value="main_menu"),
    ):
        action, _crit, recipe_ids = show_search_wizard(client, criteria=criteria)

    assert action == "main_menu"
    assert recipe_ids == []

    events = get_tracked_events()
    assert any(e["event_type"] == "error" for e in events)
