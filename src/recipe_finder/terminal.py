"""Terminal capabilities detection and control."""

import os
import shutil
import sys
from contextlib import contextmanager

from prompt_toolkit.input import Input
from prompt_toolkit.output import Output
from prompt_toolkit.output.plain_text import PlainTextOutput

MIN_TERMINAL_WIDTH = 60
DEFAULT_CONTENT_WIDTH = 80
LEFT_MARGIN = 2


def is_interactive() -> bool:
    """Return True if running in an interactive terminal."""
    return sys.stdin.isatty() and sys.stdout.isatty()


def is_utf8() -> bool:
    """Check if stdout encoding supports UTF-8."""
    encoding = (sys.stdout.encoding or "").lower()
    return "utf-8" in encoding or "utf8" in encoding


def get_color_depth(no_color: bool = False) -> str:
    """Detect terminal color support level: 'truecolor', '256', '16', or 'none'."""
    if no_color or "NO_COLOR" in os.environ:
        return "none"
    colorterm = os.getenv("COLORTERM", "").lower()
    if colorterm in ("truecolor", "24bit"):
        return "truecolor"
    term = os.getenv("TERM", "").lower()
    if "256" in term:
        return "256"
    if sys.platform == "win32":
        try:
            if sys.getwindowsversion().major >= 10:
                return "256"
        except Exception:
            pass
    return "16"


def get_terminal_size() -> tuple[int, int]:
    """Return terminal columns and rows."""
    size = shutil.get_terminal_size((DEFAULT_CONTENT_WIDTH, 24))
    return size.columns, size.lines


def get_content_width(columns: int | None = None) -> int:
    """Return bounded content width between MIN_TERMINAL_WIDTH and DEFAULT_CONTENT_WIDTH."""
    cols = columns if columns is not None else get_terminal_size()[0]
    return max(MIN_TERMINAL_WIDTH, min(cols, DEFAULT_CONTENT_WIDTH))


def get_pt_output() -> Output:
    """Return resilient prompt_toolkit Output instance."""
    try:
        from prompt_toolkit.output.defaults import create_output

        return create_output()
    except Exception:
        return PlainTextOutput(sys.stdout)


def get_pt_input() -> Input | None:
    """Return resilient prompt_toolkit Input instance."""
    try:
        from prompt_toolkit.input.defaults import create_input

        return create_input()
    except Exception:
        return None


@contextmanager
def alternate_screen():
    """Context manager to run in alternate screen buffer and restore terminal on exit."""
    if is_interactive():
        sys.stdout.write("\033[?1049h\033[?25l\033[H")
        sys.stdout.flush()
    try:
        yield
    finally:
        if is_interactive():
            sys.stdout.write("\033[?1049l\033[?25h")
            sys.stdout.flush()
