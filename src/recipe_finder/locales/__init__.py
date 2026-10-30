"""Localization helper for UI texts."""

import json
from functools import lru_cache
from pathlib import Path

_LOCALES_DIR = Path(__file__).resolve().parent


@lru_cache
def _load_locale(lang: str) -> dict[str, str]:
    file_path = _LOCALES_DIR / f"{lang}.json"
    if not file_path.exists():
        file_path = _LOCALES_DIR / "en.json"
    if not file_path.exists():
        return {}
    return json.loads(file_path.read_text(encoding="utf-8"))


def t(key: str, lang: str = "en") -> str:
    """Return the localized string for key in lang, falling back to en, then key."""
    text = _load_locale(lang).get(key)
    if text is not None:
        return text
    if lang != "en":
        text = _load_locale("en").get(key)
        if text is not None:
            return text
    return key
