"""Tests for recipe_finder.cache: HashTable, Trie, IngredientCache, and disk loading."""

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from recipe_finder.api_client import ApiClient, ApiClientError
from recipe_finder.cache import (
    HashTable,
    IngredientCache,
    Trie,
    load_ingredient_cache,
)
from recipe_finder.schemas import IngredientSuggestionResponse


def test_hash_table_basic_operations() -> None:
    ht = HashTable(size=8)
    assert len(ht) == 0

    ht.insert("apple", 1)
    ht.insert("banana", 2)
    assert len(ht) == 2
    assert ht.get("apple") == 1
    assert ht.get("banana") == 2
    assert ht.get("cherry") is None

    # Overwrite
    ht.insert("apple", 10)
    assert len(ht) == 2
    assert ht.get("apple") == 10

    # Delete
    assert ht.delete("banana") is True
    assert len(ht) == 1
    assert ht.get("banana") is None
    assert ht.delete("banana") is False


def test_trie_basic_operations() -> None:
    trie = Trie()
    assert len(trie) == 0

    trie.insert("Chicken Breast")
    trie.insert("Chicken Thigh")
    trie.insert("Beef")

    assert len(trie) == 3
    assert trie.search("chicken breast") is True
    assert trie.search("chicken") is False
    assert trie.starts_with("chick") is True
    assert trie.starts_with("pork") is False

    completions = trie.complete("chick", limit=5)
    assert completions == ["Chicken Breast", "Chicken Thigh"]

    assert trie.delete("chicken thigh") is True
    assert len(trie) == 2
    assert trie.search("chicken thigh") is False
    assert trie.delete("non_existent") is False


def test_ingredient_cache_suggest_and_lookup() -> None:
    items = [
        IngredientSuggestionResponse(ingredient_id=1, name="Chicken Breast"),
        IngredientSuggestionResponse(ingredient_id=2, name="Chicken Thigh"),
        IngredientSuggestionResponse(ingredient_id=3, name="Fried Chicken"),
        IngredientSuggestionResponse(ingredient_id=4, name="Rice"),
    ]
    cache = IngredientCache(items)
    assert len(cache) == 4
    assert cache.get_id("chicken breast") == 1
    assert cache.get_id("CHICKEN BREAST") == 1
    assert cache.get_id("unknown") is None

    # Starts-with matches come first ("Chicken Breast", "Chicken Thigh"),
    # followed by substring match ("Fried Chicken")
    suggestions = cache.suggest("chick", limit=5)
    assert len(suggestions) == 3
    assert suggestions[0] == "Chicken Breast"
    assert suggestions[1] == "Chicken Thigh"
    assert suggestions[2] == "Fried Chicken"

    assert cache.suggest("", limit=5) == []


def test_load_ingredient_cache_from_fresh_disk_file(tmp_path: Path) -> None:
    client = MagicMock(spec=ApiClient)
    cache_file = tmp_path / "ingredients_en.json"

    # Pre-populate fresh cache
    items = [IngredientSuggestionResponse(ingredient_id=10, name="Onion")]
    from recipe_finder.cache import _write_file

    _write_file(cache_file, items)

    with patch("recipe_finder.cache._cache_path", return_value=cache_file):
        cache = load_ingredient_cache(client, "en")

    assert len(cache) == 1
    assert cache.get_id("onion") == 10
    client.get_ingredients.assert_not_called()


def test_load_ingredient_cache_fetches_when_expired(tmp_path: Path) -> None:
    client = MagicMock(spec=ApiClient)
    client.get_ingredients.return_value = [
        IngredientSuggestionResponse(ingredient_id=20, name="Garlic")
    ]
    cache_file = tmp_path / "ingredients_en.json"

    # Write expired cache (older than 2 days)
    import json

    cache_file.write_text(
        json.dumps(
            {
                "fetched_at": time.time() - 300_000,
                "items": [{"ingredient_id": 1, "name": "Old Item"}],
            }
        ),
        encoding="utf-8",
    )

    with patch("recipe_finder.cache._cache_path", return_value=cache_file):
        cache = load_ingredient_cache(client, "en")

    assert len(cache) == 1
    assert cache.get_id("garlic") == 20
    client.get_ingredients.assert_called_once_with("en")


def test_load_ingredient_cache_fallback_when_api_down(tmp_path: Path) -> None:
    client = MagicMock(spec=ApiClient)
    client.get_ingredients.side_effect = ApiClientError("Server unavailable")
    cache_file = tmp_path / "ingredients_en.json"

    import json

    cache_file.write_text(
        json.dumps(
            {
                "fetched_at": time.time() - 300_000,
                "items": [{"ingredient_id": 99, "name": "Fallback Item"}],
            }
        ),
        encoding="utf-8",
    )

    with patch("recipe_finder.cache._cache_path", return_value=cache_file):
        cache = load_ingredient_cache(client, "en")

    assert len(cache) == 1
    assert cache.get_id("fallback item") == 99


def test_load_ingredient_cache_raises_when_no_cache_and_api_down(tmp_path: Path) -> None:
    client = MagicMock(spec=ApiClient)
    client.get_ingredients.side_effect = ApiClientError("Server unavailable")
    cache_file = tmp_path / "non_existent.json"

    with (
        patch("recipe_finder.cache._cache_path", return_value=cache_file),
        pytest.raises(ApiClientError),
    ):
        load_ingredient_cache(client, "en")
