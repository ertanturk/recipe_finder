"""Language selection screen."""

from prompt_toolkit import ANSI
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, Window
from prompt_toolkit.layout.controls import FormattedTextControl

from recipe_finder.locales import t
from recipe_finder.schemas import LanguageResponse
from recipe_finder.terminal import get_content_width, get_pt_input, get_pt_output, is_interactive
from recipe_finder.theme import create_console, get_box_characters, get_palette


def render_language_select(
    languages: list[LanguageResponse],
    selected_index: int,
    current_language: str,
    lang: str = "en",
    width: int = 80,
    no_color: bool = False,
) -> str:
    """Render the language selection list."""
    console = create_console(width=width, no_color=no_color)
    palette = get_palette(no_color)
    box = get_box_characters()

    with console.capture() as capture:
        console.print()
        console.print(
            f"  [{palette.accent} bold]{t('language_title', lang)}[/{palette.accent} bold]"
        )
        console.print(
            f"  [{palette.border}]{box.horizontal * min(width - 4, 46)}[/{palette.border}]"
        )
        console.print()
        for index, language in enumerate(languages):
            marker = "*" if language.language_code == current_language else " "
            prefix = box.pointer if index == selected_index else " "
            style = f"[{palette.accent} bold]" if index == selected_index else f"[{palette.text}]"
            end_style = (
                f"[/{palette.accent} bold]" if index == selected_index else f"[/{palette.text}]"
            )
            console.print(
                f"    {style}{prefix} {marker} {language.language_name} "
                f"({language.language_code}){end_style}"
            )
        console.print()
        console.print(f"  [{palette.muted}]{t('nav_language', lang)}[/{palette.muted}]")

    return capture.get()


def show_language_select(
    languages: list[LanguageResponse],
    current_language: str,
    lang: str = "en",
    width: int | None = None,
) -> str | None:
    """Display language selection and return the selected code, or None on cancel."""
    if not is_interactive() or not languages:
        return None

    selected = next(
        (index for index, item in enumerate(languages) if item.language_code == current_language),
        0,
    )
    result: str | None = None
    key_bindings = KeyBindings()

    @key_bindings.add("up")
    @key_bindings.add("k")
    def _(event) -> None:
        nonlocal selected
        selected = (selected - 1) % len(languages)
        event.app.invalidate()

    @key_bindings.add("down")
    @key_bindings.add("j")
    def _(event) -> None:
        nonlocal selected
        selected = (selected + 1) % len(languages)
        event.app.invalidate()

    @key_bindings.add("enter")
    def _(event) -> None:
        nonlocal result
        result = languages[selected].language_code
        event.app.exit()

    @key_bindings.add("escape")
    def _(event) -> None:
        event.app.exit()

    @key_bindings.add("c-c")
    def _(event) -> None:
        event.app.exit(exception=KeyboardInterrupt())

    def get_text() -> ANSI:
        return ANSI(
            render_language_select(
                languages,
                selected,
                current_language,
                lang=lang,
                width=width or get_content_width(),
            )
        )

    application: Application[None] = Application(
        layout=Layout(Window(FormattedTextControl(get_text))),
        key_bindings=key_bindings,
        full_screen=False,
        output=get_pt_output(),
        input=get_pt_input(),
    )
    application.run()
    return result
