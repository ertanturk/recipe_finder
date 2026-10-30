"""Tests for recipe_finder.theme."""

from recipe_finder.theme import (
    BOX_ASCII,
    BOX_UTF8,
    PALETTE_256,
    PALETTE_NONE,
    PALETTE_TRUECOLOR,
    NutritionColors,
    create_console,
    get_box_characters,
    get_palette,
)


def test_palette_selection(monkeypatch) -> None:
    monkeypatch.setenv("NO_COLOR", "1")
    assert get_palette() == PALETTE_NONE

    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("COLORTERM", "truecolor")
    assert get_palette() == PALETTE_TRUECOLOR

    monkeypatch.delenv("COLORTERM", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")
    assert get_palette() == PALETTE_256


def test_box_characters() -> None:
    box = get_box_characters()
    assert box in (BOX_UTF8, BOX_ASCII)
    assert box.pointer == ">"


def test_nutrition_colors() -> None:
    nc = NutritionColors()
    assert nc.calories == "#F2EFE9"
    assert nc.protein == "#6CB6FF"
    assert nc.carbohydrate == "#F2C14E"


def test_create_console() -> None:
    console = create_console(width=70, no_color=True)
    assert console.width == 70
    assert console.no_color is True
