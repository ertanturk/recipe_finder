"""Configuration management for recipe-finder."""

import json
import os
from dataclasses import dataclass
from pathlib import Path

import platformdirs

DEFAULT_API_URL = "http://127.0.0.1:8000"
DEFAULT_LANGUAGE = "en"
CONNECT_TIMEOUT = 3.0
READ_TIMEOUT = 10.0
TELEMETRY_TIMEOUT = 2.0


def get_config_dir() -> Path:
    """Return user configuration directory for recipe-finder."""
    return Path(platformdirs.user_config_dir("recipe-finder", appauthor=False))


def get_config_file() -> Path:
    """Return path to config.json."""
    return get_config_dir() / "config.json"


def load_saved_language() -> str:
    """Read saved language code from config.json, returning 'en' on failure."""
    config_file = get_config_file()
    if not config_file.exists():
        return DEFAULT_LANGUAGE
    try:
        data = json.loads(config_file.read_text(encoding="utf-8"))
        lang = data.get("language")
        if isinstance(lang, str) and lang.strip():
            return lang.strip().lower()
    except Exception:
        pass
    return DEFAULT_LANGUAGE


def save_language(language_code: str) -> None:
    """Save language preference to config.json."""
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = get_config_file()
    current: dict[str, str] = {}
    if config_file.exists():
        try:
            current = json.loads(config_file.read_text(encoding="utf-8"))
        except Exception:
            current = {}
    current["language"] = language_code.strip().lower()
    config_file.write_text(json.dumps(current, indent=2), encoding="utf-8")


@dataclass(frozen=True)
class Config:
    """Runtime configuration for recipe-finder."""

    api_url: str
    language: str
    connect_timeout: float = CONNECT_TIMEOUT
    read_timeout: float = READ_TIMEOUT
    telemetry_timeout: float = TELEMETRY_TIMEOUT


def get_config(lang_override: str | None = None) -> Config:
    """Assemble runtime configuration from environment and saved settings."""
    api_url = os.getenv("RECIPE_FINDER_API_URL", DEFAULT_API_URL).rstrip("/")
    language = (lang_override or load_saved_language()).strip().lower()
    return Config(api_url=api_url, language=language)
