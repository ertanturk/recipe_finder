"""Tests for language selection."""

from recipe_finder.schemas import LanguageResponse
from recipe_finder.screens.language import render_language_select


def test_render_language_select_marks_current_language() -> None:
    output = render_language_select(
        [
            LanguageResponse(language_code="en", language_name="English"),
            LanguageResponse(language_code="tr", language_name="Türkçe"),
        ],
        selected_index=1,
        current_language="en",
        no_color=True,
    )

    assert "Change language" in output
    assert "* English (en)" in output
    assert ">   Türkçe (tr)" in output
