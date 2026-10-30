"""Tests for recipe_finder.app."""

from unittest.mock import MagicMock, patch

from recipe_finder.api_client import ApiClient, ApiClientError
from recipe_finder.app import RecipeFinderApp


def test_app_check_api_connection_success() -> None:
    client = MagicMock(spec=ApiClient)
    client.get_languages.return_value = []

    app = RecipeFinderApp(client=client)
    assert app.check_api_connection() is True


def test_app_check_api_connection_failure() -> None:
    client = MagicMock(spec=ApiClient)
    client.get_languages.side_effect = ApiClientError("Failed", error_code="server_unavailable")

    with patch("recipe_finder.app.show_error_screen", return_value="main_menu"):
        app = RecipeFinderApp(client=client)
        assert app.check_api_connection() is False


def test_app_run_loop() -> None:
    client = MagicMock(spec=ApiClient)
    client.get_languages.return_value = []

    with patch("recipe_finder.app.show_main_menu", return_value="exit"):
        app = RecipeFinderApp(client=client)
        code = app.run()
        assert code == 0
    client.close.assert_called_once()


def test_app_close_session() -> None:
    client = MagicMock(spec=ApiClient)
    app = RecipeFinderApp(client=client)
    app.session_id = 42

    app.close_session()

    assert client.update_session.called
    assert app.session_id is None


def test_app_run_search_wizard() -> None:
    client = MagicMock(spec=ApiClient)
    client.get_languages.return_value = []

    menu_actions = ["search", "exit"]

    def fake_main_menu(*args: object, **kwargs: object) -> str:
        return menu_actions.pop(0)

    with (
        patch("recipe_finder.app.show_main_menu", side_effect=fake_main_menu),
        patch(
            "recipe_finder.app.show_search_wizard", return_value=("results", MagicMock(), [1, 2])
        ) as mock_wiz,
        patch("recipe_finder.app.show_recipe_view", return_value="main_menu") as mock_view,
    ):
        app = RecipeFinderApp(client=client)
        code = app.run()
        assert code == 0
        mock_wiz.assert_called_once()
        mock_view.assert_called_once_with(
            queue=[1, 2],
            client=client,
            criteria=mock_wiz.return_value[1],
            lang="en",
        )


def test_app_changes_language_and_clears_ingredient_cache() -> None:
    client = MagicMock(spec=ApiClient)
    client.get_languages.return_value = []
    menu_actions = ["language", "exit"]

    with (
        patch("recipe_finder.app.show_main_menu", side_effect=lambda **_: menu_actions.pop(0)),
        patch(
            "recipe_finder.app.show_language_select",
            return_value="tr",
        ),
        patch("recipe_finder.app.save_language") as save_language,
        patch("recipe_finder.app.update_telemetry_language") as update_language,
        patch("recipe_finder.app.start_telemetry"),
        patch("recipe_finder.app.stop_telemetry"),
    ):
        app = RecipeFinderApp(client=client, ingredient_cache=MagicMock())
        assert app.run() == 0

    assert app.current_lang == "tr"
    assert app.ingredient_cache is None
    save_language.assert_called_once_with("tr")
    update_language.assert_called_once_with("en", "tr")
