"""Tests for recipe_finder.config."""

from pathlib import Path
from unittest.mock import patch

from recipe_finder.config import (
    DEFAULT_API_URL,
    DEFAULT_LANGUAGE,
    get_config,
    load_saved_language,
    save_language,
)


def test_default_config(monkeypatch) -> None:
    monkeypatch.delenv("RECIPE_FINDER_API_URL", raising=False)
    cfg = get_config()
    assert cfg.api_url == DEFAULT_API_URL
    assert cfg.language == DEFAULT_LANGUAGE


def test_env_override(monkeypatch) -> None:
    monkeypatch.setenv("RECIPE_FINDER_API_URL", "http://custom-api:9000/")
    cfg = get_config(lang_override="tr")
    assert cfg.api_url == "http://custom-api:9000"
    assert cfg.language == "tr"


def test_save_and_load_language(tmp_path: Path) -> None:
    fake_config = tmp_path / "config.json"
    with (
        patch("recipe_finder.config.get_config_file", return_value=fake_config),
        patch("recipe_finder.config.get_config_dir", return_value=tmp_path),
    ):
        assert load_saved_language() == "en"
        save_language("tr")
        assert load_saved_language() == "tr"
