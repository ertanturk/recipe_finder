"""Command line entry point of `recipe-finder`."""

import os
import sys
from typing import Annotated

import typer

from recipe_finder import __version__
from recipe_finder.app import run as run_app
from recipe_finder.terminal import is_interactive

app = typer.Typer(add_completion=False, help="Find a recipe with what you have.")


def _show_version(value: bool) -> None:
    """Print the app version and exit when `--version` is given."""
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.command()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_show_version,
            is_eager=True,
            help="Show the app version and exit.",
        ),
    ] = False,
    lang: Annotated[
        str | None,
        typer.Option(
            "--lang",
            "-l",
            help="Start in a language (en, tr, ...).",
        ),
    ] = None,
    no_color: Annotated[
        bool,
        typer.Option(
            "--no-color",
            help="Do not use colors in output.",
        ),
    ] = False,
) -> None:
    """Start recipe-finder."""
    if not is_interactive():
        sys.stderr.write("recipe-finder needs an interactive terminal.\n")
        raise typer.Exit(code=1)

    if no_color:
        os.environ["NO_COLOR"] = "1"

    try:
        code = run_app(lang=lang)
        raise typer.Exit(code=code)
    except KeyboardInterrupt:
        raise typer.Exit(code=130) from None
