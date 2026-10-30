"""Main application loop managing screen transitions and session state."""

from recipe_finder import __version__
from recipe_finder.api_client import ApiClient, ApiClientError
from recipe_finder.cache import IngredientCache, load_ingredient_cache
from recipe_finder.config import get_config, save_language
from recipe_finder.locales import t
from recipe_finder.screens.language import show_language_select
from recipe_finder.screens.main_menu import show_main_menu
from recipe_finder.screens.notices import show_error_screen
from recipe_finder.screens.recipe_view import show_recipe_view
from recipe_finder.screens.wizard import show_search_wizard
from recipe_finder.telemetry import (
    start_telemetry,
    stop_telemetry,
    update_telemetry_language,
)
from recipe_finder.terminal import alternate_screen


class RecipeFinderApp:
    """Coordinates screen transitions and API communication."""

    def __init__(
        self,
        lang: str | None = None,
        api_url: str | None = None,
        client: ApiClient | None = None,
        ingredient_cache: IngredientCache | None = None,
    ) -> None:
        self.config = get_config(lang_override=lang)
        self.current_lang = self.config.language
        self.client = client or ApiClient(base_url=api_url or self.config.api_url)
        self.ingredient_cache = ingredient_cache
        self.current_screen = "main_menu"
        self.session_id: int | None = None

    def check_api_connection(self) -> bool:
        """Verify API is reachable, showing error screen on failure."""
        while True:
            try:
                self.client.get_languages()
                return True
            except ApiClientError:
                action = show_error_screen(
                    message=t("notice_server_unavailable", self.current_lang),
                    lang=self.current_lang,
                    allow_retry=True,
                )
                if action == "retry":
                    continue
                return False

    def close_session(self) -> None:
        """Close active session if exists."""
        if self.session_id is not None:
            try:
                from datetime import UTC, datetime

                from recipe_finder.schemas import SessionUpdateRequest

                self.client.update_session(
                    self.session_id,
                    SessionUpdateRequest(ended_at=datetime.now(UTC)),
                )
            except Exception:
                pass
            self.session_id = None

    def run(self) -> int:
        """Run the main application loop."""
        try:
            with alternate_screen():
                if not self.check_api_connection():
                    return 1
                start_telemetry(self.client, __version__, self.current_lang)

                while self.current_screen != "exit":
                    if self.current_screen == "main_menu":
                        action = show_main_menu(lang=self.current_lang)
                        if action == "search":
                            if self.ingredient_cache is None:
                                try:
                                    self.ingredient_cache = load_ingredient_cache(
                                        self.client, self.current_lang
                                    )
                                except Exception:
                                    self.ingredient_cache = None

                            wizard_action, _criteria, recipe_ids = show_search_wizard(
                                client=self.client,
                                lang=self.current_lang,
                                cache=self.ingredient_cache,
                            )
                            if wizard_action == "results":
                                show_recipe_view(
                                    queue=recipe_ids,
                                    client=self.client,
                                    criteria=_criteria,
                                    lang=self.current_lang,
                                )
                            self.current_screen = "main_menu"
                        elif action == "language":
                            try:
                                languages = self.client.get_languages()
                            except ApiClientError:
                                languages = []
                            selected_language = show_language_select(
                                languages,
                                self.current_lang,
                                lang=self.current_lang,
                            )
                            if selected_language and selected_language != self.current_lang:
                                previous_language = self.current_lang
                                self.current_lang = selected_language
                                save_language(selected_language)
                                self.ingredient_cache = None
                                update_telemetry_language(previous_language, selected_language)
                            self.current_screen = "main_menu"
                        elif action == "exit":
                            self.current_screen = "exit"
                    else:
                        self.current_screen = "main_menu"

            return 0
        finally:
            stop_telemetry()
            self.close_session()
            self.client.close()


def run(lang: str | None = None, api_url: str | None = None) -> int:
    """Convenience runner function for the application."""
    app = RecipeFinderApp(lang=lang, api_url=api_url)
    return app.run()
