"""Local ingredient cache for autocomplete: prefix suggestions and name to id."""

import json
import logging
import time
from pathlib import Path

from platformdirs import user_cache_dir

from recipe_finder.api_client import ApiClient, ApiClientError
from recipe_finder.schemas import IngredientSuggestionResponse

logger = logging.getLogger(__name__)

APP_NAME = "recipe-finder"
MAX_AGE_SECONDS = 172_800  # The saved list is used for 2 days.
HASH_TABLE_SIZE = 1024


class HashTable:
    """A hash table with separate chaining. Maps a name to an ingredient id."""

    def __init__(self, size: int = HASH_TABLE_SIZE) -> None:
        self.size = size
        self.table: list[list[tuple[str, int]]] = [[] for _ in range(size)]
        self.count = 0

    def _bucket(self, key: str) -> list[tuple[str, int]]:
        """Return the bucket that holds the key."""
        return self.table[hash(key) % self.size]

    def insert(self, key: str, value: int) -> None:
        """Add a key-value pair, or replace the value if the key exists."""
        bucket = self._bucket(key)
        for position, (stored_key, _) in enumerate(bucket):
            if stored_key == key:
                bucket[position] = (key, value)
                return
        bucket.append((key, value))
        self.count += 1

    def get(self, key: str) -> int | None:
        """Return the value for the key, or None if the key is missing."""
        for stored_key, value in self._bucket(key):
            if stored_key == key:
                return value
        return None

    def delete(self, key: str) -> bool:
        """Remove the key. Return True if it existed."""
        bucket = self._bucket(key)
        for position, (stored_key, _) in enumerate(bucket):
            if stored_key == key:
                del bucket[position]
                self.count -= 1
                return True
        return False

    def __len__(self) -> int:
        """Return the number of key-value pairs."""
        return self.count

    def __str__(self) -> str:
        """Return a short description of the table."""
        return f"HashTable(size={self.size}, items={self.count})"


class TrieNode:
    """A node in the trie."""

    def __init__(self) -> None:
        self.children: dict[str, TrieNode] = {}
        # The original word. It is set only when a word ends at this node.
        self.word: str | None = None


class Trie:
    """A trie (prefix tree) for storing words and completing prefixes.

    Matching ignores upper and lower case. Words keep their original spelling.
    """

    def __init__(self) -> None:
        self.root = TrieNode()
        self.count = 0

    def insert(self, word: str) -> None:
        """Add a word to the trie."""
        node = self.root
        for char in word.casefold():
            node = node.children.setdefault(char, TrieNode())
        if node.word is None:
            self.count += 1
        node.word = word

    def _find(self, prefix: str) -> TrieNode | None:
        """Return the node at the end of the prefix, or None if there is none."""
        node = self.root
        for char in prefix.casefold():
            child = node.children.get(char)
            if child is None:
                return None
            node = child
        return node

    def search(self, word: str) -> bool:
        """Return True if the exact word is in the trie."""
        node = self._find(word)
        return node is not None and node.word is not None

    def starts_with(self, prefix: str) -> bool:
        """Return True if any word in the trie starts with the prefix."""
        return self._find(prefix) is not None

    def complete(self, prefix: str, limit: int) -> list[str]:
        """Return up to `limit` words that start with the prefix, A to Z."""
        start = self._find(prefix)
        if start is None:
            return []

        results: list[str] = []
        stack = [start]
        # Depth-first with smaller characters first gives alphabetical order.
        while stack and len(results) < limit:
            node = stack.pop()
            if node.word is not None:
                results.append(node.word)
            for char in sorted(node.children, reverse=True):
                stack.append(node.children[char])
        return results

    def delete(self, word: str) -> bool:
        """Remove the word. Return True if it existed."""
        path: list[tuple[TrieNode, str]] = []
        node = self.root
        for char in word.casefold():
            child = node.children.get(char)
            if child is None:
                return False
            path.append((node, char))
            node = child
        if node.word is None:
            return False

        node.word = None
        self.count -= 1
        # Remove nodes that are no longer needed, from the word end upward.
        for parent, char in reversed(path):
            child = parent.children[char]
            if child.word is not None or child.children:
                break
            del parent.children[char]
        return True

    def __len__(self) -> int:
        """Return the number of words."""
        return self.count

    def __str__(self) -> str:
        """Return a short description of the trie."""
        return f"Trie(words={self.count})"


class IngredientCache:
    """Ingredient names of one language: suggestions and name to id."""

    def __init__(self, items: list[IngredientSuggestionResponse]) -> None:
        self.ids = HashTable()
        self.trie = Trie()
        self.names: list[str] = []
        for item in items:
            self.ids.insert(item.name.casefold(), item.ingredient_id)
            self.trie.insert(item.name)
            self.names.append(item.name)
        self.names.sort(key=str.casefold)

    def get_id(self, name: str) -> int | None:
        """Return the ingredient id for a name, or None if it is unknown."""
        return self.ids.get(name.casefold())

    def suggest(self, query: str, limit: int = 8) -> list[str]:
        """Return up to `limit` names for what the user typed.

        Names that start with the query come first. Names that only
        contain it come after.

        Args:
            query: The text typed by the user. It can be incomplete.
            limit: Maximum number of names to return.
        """
        query = query.strip()
        if not query:
            return []

        matches = self.trie.complete(query, limit)
        needle = query.casefold()
        for name in self.names:
            if len(matches) >= limit:
                break
            if needle in name.casefold() and name not in matches:
                matches.append(name)
        return matches

    def __len__(self) -> int:
        """Return the number of ingredients."""
        return len(self.names)


def _cache_path(language_code: str) -> Path:
    """Return the file that holds the saved list for a language."""
    return Path(user_cache_dir(APP_NAME)) / f"ingredients_{language_code}.json"


def _read_file(path: Path) -> tuple[float, list[IngredientSuggestionResponse]] | None:
    """Read the saved list. Return None if the file is missing or broken."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        items = [IngredientSuggestionResponse.model_validate(entry) for entry in raw["items"]]
        return float(raw["fetched_at"]), items
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _write_file(path: Path, items: list[IngredientSuggestionResponse]) -> None:
    """Save the list with the current time. A write error is only logged."""
    if not items:
        return
    data = {
        "fetched_at": time.time(),
        "items": [item.model_dump() for item in items],
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except OSError:
        logger.warning("Could not save the ingredient cache to %s", path)


def load_ingredient_cache(client: ApiClient, language_code: str) -> IngredientCache:
    """Return the ingredient cache for a language.

    The saved file is used while it is fresh. Otherwise the list is
    downloaded and saved. If the download fails, an old file is used.

    Args:
        client: API client used to download the list.
        language_code: Language of the ingredient names, for example "en".

    Raises:
        ApiClientError: If the download fails and there is no saved file.
    """
    path = _cache_path(language_code)
    saved = _read_file(path)
    if saved is not None:
        fetched_at, saved_items = saved
        if saved_items and time.time() - fetched_at <= MAX_AGE_SECONDS:
            return IngredientCache(saved_items)

    try:
        items = client.get_ingredients(language_code)
    except ApiClientError:
        if saved is None or not saved[1]:
            raise
        logger.warning("API is not reachable. Using the old ingredient cache.")
        return IngredientCache(saved[1])

    if items:
        _write_file(path, items)
    elif saved is not None and saved[1]:
        return IngredientCache(saved[1])
    return IngredientCache(items)
