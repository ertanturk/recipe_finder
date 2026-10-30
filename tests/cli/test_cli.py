"""Tests for the CLI entry point."""

import tomllib
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from recipe_finder import __version__
from recipe_finder.cli import app

runner = CliRunner()


def test_version_flag_prints_version_and_exits_zero() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.stdout.strip() == __version__


def test_version_matches_pyproject() -> None:
    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    expected = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["version"]

    assert __version__ == expected


def test_run_without_flags_exits_with_code_one() -> None:
    result = runner.invoke(app, [])

    assert result.exit_code == 1
    assert "interactive terminal" in result.stderr


def test_interactive_run_passes_lang(monkeypatch) -> None:
    monkeypatch.setattr("recipe_finder.cli.is_interactive", lambda: True)
    with patch("recipe_finder.cli.run_app", return_value=0) as mock_run:
        result = runner.invoke(app, ["--lang", "tr"])
        assert result.exit_code == 0
        mock_run.assert_called_once_with(lang="tr")


def test_interactive_run_no_color(monkeypatch) -> None:
    monkeypatch.setattr("recipe_finder.cli.is_interactive", lambda: True)
    with patch("recipe_finder.cli.run_app", return_value=0):
        result = runner.invoke(app, ["--no-color"])
        assert result.exit_code == 0


def test_keyboard_interrupt_exits_130(monkeypatch) -> None:
    monkeypatch.setattr("recipe_finder.cli.is_interactive", lambda: True)
    with patch("recipe_finder.cli.run_app", side_effect=KeyboardInterrupt):
        result = runner.invoke(app, [])
        assert result.exit_code == 130
