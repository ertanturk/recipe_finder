"""Theme colors and styling for recipe-finder ('Tomato & Slate' palette)."""

from dataclasses import dataclass

from rich.console import Console
from rich.theme import Theme as RichTheme

from recipe_finder.terminal import get_color_depth, is_utf8


@dataclass(frozen=True)
class Palette:
    """Resolved color definitions for UI elements."""

    accent: str
    success: str
    info: str
    warning: str
    error: str
    text: str
    muted: str
    border: str
    highlight_bg: str


# Truecolor (Hex)
PALETTE_TRUECOLOR = Palette(
    accent="#FF6B5A",
    success="#6FCF97",
    info="#6CB6FF",
    warning="#F2C14E",
    error="#E5484D",
    text="#F2EFE9",
    muted="#8B93A7",
    border="#3A3F4B",
    highlight_bg="#2A2F3A",
)

# ANSI-256
PALETTE_256 = Palette(
    accent="color(203)",
    success="color(78)",
    info="color(75)",
    warning="color(221)",
    error="color(167)",
    text="color(255)",
    muted="color(103)",
    border="color(238)",
    highlight_bg="color(236)",
)

# 16-color
PALETTE_16 = Palette(
    accent="bright_red",
    success="green",
    info="bright_blue",
    warning="yellow",
    error="red",
    text="white",
    muted="bright_black",
    border="bright_black",
    highlight_bg="reverse",
)

# No color
PALETTE_NONE = Palette(
    accent="default",
    success="default",
    info="default",
    warning="default",
    error="default",
    text="default",
    muted="default",
    border="default",
    highlight_bg="reverse",
)


@dataclass(frozen=True)
class NutritionColors:
    """Colors assigned to nutritional metrics."""

    calories: str = "#F2EFE9"
    protein: str = "#6CB6FF"
    carbohydrate: str = "#F2C14E"
    fat: str = "#FF8FA3"
    fiber: str = "#6FCF97"
    sugar: str = "#B79CED"
    sodium: str = "#8B93A7"


@dataclass(frozen=True)
class BoxCharacters:
    """Box drawing characters for terminal frames."""

    top_left: str
    top_right: str
    bottom_left: str
    bottom_right: str
    horizontal: str
    vertical: str
    pointer: str


BOX_UTF8 = BoxCharacters(
    top_left="╭",
    top_right="╮",
    bottom_left="╰",
    bottom_right="╯",
    horizontal="─",
    vertical="│",
    pointer=">",
)

BOX_ASCII = BoxCharacters(
    top_left="+",
    top_right="+",
    bottom_left="+",
    bottom_right="+",
    horizontal="-",
    vertical="|",
    pointer=">",
)


def get_palette(no_color: bool = False) -> Palette:
    """Return Palette matching current terminal capability."""
    level = get_color_depth(no_color)
    if level == "truecolor":
        return PALETTE_TRUECOLOR
    if level == "256":
        return PALETTE_256
    if level == "16":
        return PALETTE_16
    return PALETTE_NONE


def get_box_characters() -> BoxCharacters:
    """Return UTF-8 or ASCII box characters based on terminal encoding."""
    return BOX_UTF8 if is_utf8() else BOX_ASCII


def create_console(width: int = 80, no_color: bool = False) -> Console:
    """Create a Rich Console configured with the Tomato & Slate theme."""
    palette = get_palette(no_color)
    rich_theme = RichTheme(
        {
            "accent": palette.accent,
            "success": palette.success,
            "info": palette.info,
            "warning": palette.warning,
            "error": palette.error,
            "text": palette.text,
            "muted": palette.muted,
            "border": palette.border,
            "highlight_bg": palette.highlight_bg,
        }
    )
    return Console(
        theme=rich_theme,
        width=width,
        no_color=no_color or get_color_depth(no_color) == "none",
        highlight=False,
    )
