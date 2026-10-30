"""State management for user search criteria and result queue."""

from dataclasses import dataclass, field

from recipe_finder.schemas import SearchRequest


@dataclass
class SearchCriteria:
    """Stores user selections across search wizard steps."""

    ingredient_names: list[str] = field(default_factory=list)
    ingredient_ids: list[int] = field(default_factory=list)
    max_calorie: float | None = None
    min_protein: float | None = None
    min_carbohydrate: float | None = None
    min_fat: float | None = None
    min_fiber: float | None = None
    min_sugar: float | None = None
    min_sodium: float | None = None
    category_id: int | None = None
    category_name: str | None = None

    def has_any_filter(self) -> bool:
        """Return True if at least one search filter is configured."""
        return bool(
            self.ingredient_ids
            or self.max_calorie is not None
            or self.min_protein is not None
            or self.min_carbohydrate is not None
            or self.min_fat is not None
            or self.min_fiber is not None
            or self.min_sugar is not None
            or self.min_sodium is not None
            or self.category_id is not None
        )

    def to_search_request(self, lang: str = "en") -> SearchRequest:
        """Convert collected criteria to an API SearchRequest payload."""
        return SearchRequest(
            lang=lang,
            ingredient_ids=self.ingredient_ids,
            max_calorie=self.max_calorie,
            min_protein=self.min_protein,
            min_carbohydrate=self.min_carbohydrate,
            min_fat=self.min_fat,
            min_fiber=self.min_fiber,
            min_sugar=self.min_sugar,
            min_sodium=self.min_sodium,
            category_id=self.category_id,
        )

    def clear(self) -> None:
        """Reset all criteria fields to initial empty state."""
        self.ingredient_names.clear()
        self.ingredient_ids.clear()
        self.max_calorie = None
        self.min_protein = None
        self.min_carbohydrate = None
        self.min_fat = None
        self.min_fiber = None
        self.min_sugar = None
        self.min_sodium = None
        self.category_id = None
        self.category_name = None


@dataclass
class ResultQueue:
    """Maintains search result recipe ids and navigation position."""

    recipe_ids: list[int]
    index: int = 0
    skipped_ids: set[int] = field(default_factory=set)

    @property
    def current_id(self) -> int | None:
        """Return current recipe id or None if list is empty."""
        if 0 <= self.index < len(self.recipe_ids):
            return self.recipe_ids[self.index]
        return None

    @property
    def total(self) -> int:
        """Return total number of matching recipe ids."""
        return len(self.recipe_ids)

    @property
    def position(self) -> int:
        """Return 1-based display position."""
        return self.index + 1

    def has_next(self) -> bool:
        """Return True if there is a next recipe available."""
        return self.index + 1 < len(self.recipe_ids)

    def has_previous(self) -> bool:
        """Return True if there is a previous recipe available."""
        return self.index > 0

    def next(self) -> int | None:
        """Advance index and return next recipe id, or None if at end."""
        if self.has_next():
            self.index += 1
            return self.current_id
        return None

    def previous(self) -> int | None:
        """Move back index and return previous recipe id, or None if at start."""
        if self.has_previous():
            self.index -= 1
            return self.current_id
        return None

    def mark_skipped(self) -> bool:
        """Mark current recipe id as skipped. Return True if newly skipped."""
        cid = self.current_id
        if cid is not None and cid not in self.skipped_ids:
            self.skipped_ids.add(cid)
            return True
        return False

    def remove_current(self) -> int | None:
        """Remove current recipe id (e.g. on 404) and adjust index."""
        if not self.recipe_ids:
            return None
        if 0 <= self.index < len(self.recipe_ids):
            del self.recipe_ids[self.index]
            if self.index >= len(self.recipe_ids):
                self.index = max(0, len(self.recipe_ids) - 1)
            return self.current_id
        return None
