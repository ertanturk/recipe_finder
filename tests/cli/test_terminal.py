"""Tests for recipe_finder.terminal."""

from unittest.mock import patch

from recipe_finder.terminal import (
    DEFAULT_CONTENT_WIDTH,
    MIN_TERMINAL_WIDTH,
    alternate_screen,
    get_color_depth,
    get_content_width,
    is_interactive,
    is_utf8,
)


def test_interactive_detection() -> None:
    # During pytest run without TTY, is_interactive is False
    assert isinstance(is_interactive(), bool)


def test_utf8_detection() -> None:
    assert isinstance(is_utf8(), bool)


def test_color_depth_detection(monkeypatch) -> None:
    monkeypatch.setenv("NO_COLOR", "1")
    assert get_color_depth() == "none"

    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("COLORTERM", "truecolor")
    assert get_color_depth() == "truecolor"

    monkeypatch.delenv("COLORTERM", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")
    assert get_color_depth() == "256"


def test_content_width_bounds() -> None:
    assert get_content_width(50) == MIN_TERMINAL_WIDTH
    assert get_content_width(70) == 70
    assert get_content_width(120) == DEFAULT_CONTENT_WIDTH


def test_alternate_screen_interactive(monkeypatch) -> None:
    monkeypatch.setattr("recipe_finder.terminal.is_interactive", lambda: True)
    with patch("sys.stdout.write") as mock_write, patch("sys.stdout.flush"):
        with alternate_screen():
            pass
        assert mock_write.call_count == 2
