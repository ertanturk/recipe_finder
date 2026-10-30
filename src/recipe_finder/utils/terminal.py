"""Alias module pointing to recipe_finder.terminal."""

from recipe_finder.terminal import (
    DEFAULT_CONTENT_WIDTH,
    LEFT_MARGIN,
    MIN_TERMINAL_WIDTH,
    alternate_screen,
    get_color_depth,
    get_content_width,
    get_pt_input,
    get_pt_output,
    get_terminal_size,
    is_interactive,
    is_utf8,
)

__all__ = [
    "DEFAULT_CONTENT_WIDTH",
    "LEFT_MARGIN",
    "MIN_TERMINAL_WIDTH",
    "alternate_screen",
    "get_color_depth",
    "get_content_width",
    "get_pt_input",
    "get_pt_output",
    "get_terminal_size",
    "is_interactive",
    "is_utf8",
]
