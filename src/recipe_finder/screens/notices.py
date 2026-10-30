"""Notice screens: error screen, no-results screen, end-of-results screen."""

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


def render_error_screen(
    message: str,
    selected_index: int,
    lang: str = "en",
    allow_retry: bool = True,
    width: int = 80,
    no_color: bool = False,
) -> str:
    """Render the error notice screen to an ANSI formatted string."""
    console = create_console(width=width, no_color=no_color)
    box = get_box_characters()
    palette = get_palette(no_color)

    title = t("notice_error_title", lang)
    options = (
        [t("action_retry", lang), t("action_main_menu", lang)]
        if allow_retry
        else [t("action_main_menu", lang)]
    )
    nav_hint = t("nav_notice", lang)

    box_width = min(width - 4, 50)
    inner_width = box_width - 2

    top_border = f"{box.top_left}{box.horizontal * inner_width}{box.top_right}"
    bottom_border = f"{box.bottom_left}{box.horizontal * inner_width}{box.bottom_right}"

    with console.capture() as capture:
        console.print()
        console.print(f"  [{palette.error}]{top_border}[/{palette.error}]")
        console.print(
            f"  [{palette.error}]{box.vertical}[/{palette.error}]  [{palette.error} bold]{title:<{inner_width - 2}}[/{palette.error} bold][{palette.error}]{box.vertical}[/{palette.error}]"
        )
        console.print(
            f"  [{palette.error}]{box.vertical}[/{palette.error}]  [{palette.text}]{message:<{inner_width - 2}}[/{palette.text}][{palette.error}]{box.vertical}[/{palette.error}]"
        )
        console.print(f"  [{palette.error}]{bottom_border}[/{palette.error}]")
        console.print()

        for idx, label in enumerate(options):
            if idx == selected_index:
                console.print(
                    f"    [{palette.accent} bold]{box.pointer} {label}[/{palette.accent} bold]"
                )
            else:
                console.print(f"      [{palette.text}]{label}[/{palette.text}]")

        console.print()
        console.print(f"  [{palette.muted}]{nav_hint}[/{palette.muted}]")

    return capture.get()


def show_error_screen(
    message: str,
    lang: str = "en",
    allow_retry: bool = True,
    width: int | None = None,
) -> str:
    """Display the interactive error notice screen. Returns 'retry' or 'main_menu'."""
    if not is_interactive():
        return "main_menu"

    actions = ["retry", "main_menu"] if allow_retry else ["main_menu"]
    selected = 0
    chosen_action = "main_menu"

    kb = KeyBindings()

    @kb.add("up")
    @kb.add("k")
    def _(event):
        nonlocal selected
        selected = (selected - 1) % len(actions)
        event.app.invalidate()

    @kb.add("down")
    @kb.add("j")
    def _(event):
        nonlocal selected
        selected = (selected + 1) % len(actions)
        event.app.invalidate()

    @kb.add("enter")
    def _(event):
        nonlocal chosen_action
        chosen_action = actions[selected]
        event.app.exit()

    @kb.add("c-c")
    def _(event):
        event.app.exit(exception=KeyboardInterrupt())

    def get_text():
        cw = width or get_content_width()
        return ANSI(
            render_error_screen(
                message=message,
                selected_index=selected,
                lang=lang,
                allow_retry=allow_retry,
                width=cw,
            )
        )

    app: Application[None] = Application(
        layout=Layout(Window(FormattedTextControl(get_text))),
        key_bindings=kb,
        full_screen=False,
        output=get_pt_output(),
        input=get_pt_input(),
    )
    app.run()
    return chosen_action


def render_no_results_screen(
    selected_index: int,
    hint: str = "",
    lang: str = "en",
    width: int = 80,
    no_color: bool = False,
) -> str:
    """Render the no-results notice screen to an ANSI formatted string."""
    console = create_console(width=width, no_color=no_color)
    box = get_box_characters()
    palette = get_palette(no_color)

    title = t("notice_no_results_title", lang)
    body = hint or t("notice_no_results_body", lang)
    options = [t("action_edit_search", lang), t("action_main_menu", lang)]
    nav_hint = t("nav_notice", lang)

    with console.capture() as capture:
        console.print()
        console.print(f"  [{palette.warning} bold]{title}[/{palette.warning} bold]")
        console.print(f"  [{palette.text}]{body}[/{palette.text}]")
        console.print()

        for idx, label in enumerate(options):
            if idx == selected_index:
                console.print(
                    f"    [{palette.accent} bold]{box.pointer} {label}[/{palette.accent} bold]"
                )
            else:
                console.print(f"      [{palette.text}]{label}[/{palette.text}]")

        console.print()
        console.print(f"  [{palette.muted}]{nav_hint}[/{palette.muted}]")

    return capture.get()


def show_no_results_screen(
    hint: str = "",
    lang: str = "en",
    width: int | None = None,
) -> str:
    """Display the interactive no-results screen. Returns 'wizard' or 'main_menu'."""
    if not is_interactive():
        return "main_menu"

    actions = ["wizard", "main_menu"]
    selected = 0
    chosen_action = "main_menu"

    kb = KeyBindings()

    @kb.add("up")
    @kb.add("k")
    def _(event):
        nonlocal selected
        selected = (selected - 1) % len(actions)
        event.app.invalidate()

    @kb.add("down")
    @kb.add("j")
    def _(event):
        nonlocal selected
        selected = (selected + 1) % len(actions)
        event.app.invalidate()

    @kb.add("enter")
    def _(event):
        nonlocal chosen_action
        chosen_action = actions[selected]
        event.app.exit()

    @kb.add("c-c")
    def _(event):
        event.app.exit(exception=KeyboardInterrupt())

    def get_text():
        cw = width or get_content_width()
        return ANSI(
            render_no_results_screen(
                selected_index=selected,
                hint=hint,
                lang=lang,
                width=cw,
            )
        )

    app: Application[None] = Application(
        layout=Layout(Window(FormattedTextControl(get_text))),
        key_bindings=kb,
        full_screen=False,
        output=get_pt_output(),
        input=get_pt_input(),
    )
    app.run()
    return chosen_action


def render_end_of_results_screen(
    selected_index: int,
    lang: str = "en",
    width: int = 80,
    no_color: bool = False,
) -> str:
    """Render the end-of-results notice screen to an ANSI formatted string."""
    console = create_console(width=width, no_color=no_color)
    box = get_box_characters()
    palette = get_palette(no_color)

    title = t("notice_end_of_results_title", lang)
    body = t("notice_end_of_results_body", lang)
    options = [t("action_new_search", lang), t("action_main_menu", lang)]
    nav_hint = t("nav_notice", lang)

    with console.capture() as capture:
        console.print()
        console.print(f"  [{palette.info} bold]{title}[/{palette.info} bold]")
        console.print(f"  [{palette.text}]{body}[/{palette.text}]")
        console.print()

        for idx, label in enumerate(options):
            if idx == selected_index:
                console.print(
                    f"    [{palette.accent} bold]{box.pointer} {label}[/{palette.accent} bold]"
                )
            else:
                console.print(f"      [{palette.text}]{label}[/{palette.text}]")

        console.print()
        console.print(f"  [{palette.muted}]{nav_hint}[/{palette.muted}]")

    return capture.get()


def show_end_of_results_screen(lang: str = "en", width: int | None = None) -> str:
    """Display the interactive end-of-results screen. Returns 'wizard' or 'main_menu'."""
    if not is_interactive():
        return "main_menu"

    actions = ["wizard", "main_menu"]
    selected = 0
    chosen_action = "main_menu"

    kb = KeyBindings()

    @kb.add("up")
    @kb.add("k")
    def _(event):
        nonlocal selected
        selected = (selected - 1) % len(actions)
        event.app.invalidate()

    @kb.add("down")
    @kb.add("j")
    def _(event):
        nonlocal selected
        selected = (selected + 1) % len(actions)
        event.app.invalidate()

    @kb.add("enter")
    def _(event):
        nonlocal chosen_action
        chosen_action = actions[selected]
        event.app.exit()

    @kb.add("c-c")
    def _(event):
        event.app.exit(exception=KeyboardInterrupt())

    def get_text():
        cw = width or get_content_width()
        return ANSI(
            render_end_of_results_screen(
                selected_index=selected,
                lang=lang,
                width=cw,
            )
        )

    app: Application[None] = Application(
        layout=Layout(Window(FormattedTextControl(get_text))),
        key_bindings=kb,
        full_screen=False,
        output=get_pt_output(),
        input=get_pt_input(),
    )
    app.run()
    return chosen_action
