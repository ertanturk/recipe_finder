"""Main menu screen implementation."""

from prompt_toolkit import ANSI
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, Window
from prompt_toolkit.layout.controls import FormattedTextControl

from recipe_finder.locales import t
from recipe_finder.terminal import (
    get_content_width,
    get_pt_input,
    get_pt_output,
    is_interactive,
)
from recipe_finder.theme import create_console, get_box_characters, get_palette

MENU_ACTIONS = ["search", "language", "exit"]


def render_main_menu(
    selected_index: int,
    lang: str = "en",
    width: int = 80,
    no_color: bool = False,
) -> str:
    """Render the main menu screen to an ANSI formatted string."""
    console = create_console(width=width, no_color=no_color)
    box = get_box_characters()
    palette = get_palette(no_color)

    title = t("app_title", lang)
    subtitle = t("app_subtitle", lang)
    items = [
        t("menu_search", lang),
        t("menu_language", lang),
        t("menu_exit", lang),
    ]
    nav_hint = t("nav_menu", lang)

    box_width = min(width - 4, 44)
    inner_width = box_width - 2

    top_border = f"{box.top_left}{box.horizontal * inner_width}{box.top_right}"
    bottom_border = f"{box.bottom_left}{box.horizontal * inner_width}{box.bottom_right}"

    with console.capture() as capture:
        console.print()
        console.print(f"  [{palette.border}]{top_border}[/{palette.border}]")
        console.print(
            f"  [{palette.border}]{box.vertical}[/{palette.border}]  [{palette.accent} bold]{title:<{inner_width - 2}}[/{palette.accent} bold][{palette.border}]{box.vertical}[/{palette.border}]"
        )
        console.print(
            f"  [{palette.border}]{box.vertical}[/{palette.border}]  [{palette.text}]{subtitle:<{inner_width - 2}}[/{palette.text}][{palette.border}]{box.vertical}[/{palette.border}]"
        )
        console.print(f"  [{palette.border}]{bottom_border}[/{palette.border}]")
        console.print()

        for idx, label in enumerate(items):
            if idx == selected_index:
                console.print(
                    f"    [{palette.accent} bold]{box.pointer} {label}[/{palette.accent} bold]"
                )
            else:
                console.print(f"      [{palette.text}]{label}[/{palette.text}]")

        console.print()
        console.print(f"  [{palette.muted}]{nav_hint}[/{palette.muted}]")

    return capture.get()


def show_main_menu(lang: str = "en", width: int | None = None) -> str:
    """Show the interactive main menu and return the chosen action name."""
    if not is_interactive():
        return "exit"

    selected = 0
    chosen_action = "exit"

    kb = KeyBindings()

    @kb.add("up")
    @kb.add("k")
    def _(event):
        nonlocal selected
        selected = (selected - 1) % len(MENU_ACTIONS)
        event.app.invalidate()

    @kb.add("down")
    @kb.add("j")
    def _(event):
        nonlocal selected
        selected = (selected + 1) % len(MENU_ACTIONS)
        event.app.invalidate()

    @kb.add("enter")
    def _(event):
        nonlocal chosen_action
        chosen_action = MENU_ACTIONS[selected]
        event.app.exit()

    @kb.add("c-c")
    def _(event):
        event.app.exit(exception=KeyboardInterrupt())

    def get_text():
        cw = width or get_content_width()
        return ANSI(render_main_menu(selected, lang=lang, width=cw))

    app: Application[None] = Application(
        layout=Layout(Window(FormattedTextControl(get_text))),
        key_bindings=kb,
        full_screen=False,
        output=get_pt_output(),
        input=get_pt_input(),
    )
    app.run()
    return chosen_action
