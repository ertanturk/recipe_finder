"""Models that check the JSON file used to import ingredients and recipes."""

from collections import Counter
from typing import Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

Category = Literal["breakfast", "lunch", "dinner", "snack"]

# Pure fat has about 884 kcal per 100 g, so nothing can be higher than this.
MAX_CALORIE_PER_100G = 900.0
# Allowed rounding error when adding up grams per 100 g of food.
GRAM_TOLERANCE = 1


def find_duplicates(names: list[str]) -> list[str]:
    """Return the names that appear more than once, ignoring case.

    Args:
        names: Names to check.

    Returns:
        Each repeated name once, in lowercase.
    """
    counts = Counter(name.casefold() for name in names)
    return [name for name, count in counts.items() if count > 1]


class StrictModel(BaseModel):
    """Base for all import models: strips spaces and rejects unknown keys."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class LocalizedString(StrictModel):
    """A text in every supported language."""

    en: str = Field(min_length=1)
    tr: str = Field(min_length=1)


class NutritionalValues(StrictModel):
    """Nutrition per 100 g of raw ingredient. Sodium is in mg, the rest in g.

    Carbohydrate is the total and already includes sugar and fiber.
    Calorie is in kcal.
    """

    calorie: float = Field(ge=0, le=MAX_CALORIE_PER_100G)
    protein: float = Field(ge=0)
    fat: float = Field(ge=0)
    carbohydrate: float = Field(ge=0)
    sugar: float = Field(ge=0)
    fiber: float = Field(ge=0)
    sodium: float = Field(ge=0)

    @model_validator(mode="after")
    def check_plausible(self) -> Self:
        """Reject values that cannot be true for 100 g of food."""
        macros = self.protein + self.fat + self.carbohydrate
        if macros > 100 + GRAM_TOLERANCE:
            raise ValueError("protein + fat + carbohydrate is more than 100 g")
        if self.sugar + self.fiber > self.carbohydrate + GRAM_TOLERANCE:
            raise ValueError("sugar + fiber is more than total carbohydrate")
        return self


class IngredientDefinition(StrictModel):
    """An ingredient with its names and nutrition."""

    name: LocalizedString
    per_100g: NutritionalValues


class RecipeIngredient(StrictModel):
    """An ingredient used in a recipe, with its weight."""

    # Matched with the English ingredient name, ignoring case.
    name: str = Field(min_length=1)
    grams: float = Field(gt=0)


class Recipe(StrictModel):
    """A recipe with texts, prep time, categories, and ingredients."""

    name: LocalizedString
    instructions: LocalizedString
    prep_time_minutes: int = Field(gt=0)
    categories: list[Category] = Field(min_length=1)
    ingredients: list[RecipeIngredient] = Field(min_length=1)

    @field_validator("categories")
    @classmethod
    def check_categories_unique(cls, value: list[Category]) -> list[Category]:
        """Reject a category that is listed twice (the DB key forbids it)."""
        if len(set(value)) != len(value):
            raise ValueError("a category is listed more than once")
        return value

    @field_validator("ingredients")
    @classmethod
    def check_ingredients_unique(cls, value: list[RecipeIngredient]) -> list[RecipeIngredient]:
        """Reject an ingredient that is listed twice (the DB key forbids it)."""
        duplicates = find_duplicates([item.name for item in value])
        if duplicates:
            raise ValueError(f"ingredient listed more than once: {', '.join(duplicates)}")
        return value


class Cookbook(StrictModel):
    """The whole JSON file.

    Either list can be empty, so a file can hold only recipes that use
    ingredients which are already in the database. The import script checks
    that every recipe ingredient exists.
    """

    ingredients: list[IngredientDefinition] = Field(default_factory=list)
    recipes: list[Recipe] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_not_empty_and_unique(self) -> Self:
        """Reject an empty file and names that are used more than once."""
        if not self.ingredients and not self.recipes:
            raise ValueError("the file has no ingredients and no recipes")

        ingredient_dupes = find_duplicates([i.name.en for i in self.ingredients])
        if ingredient_dupes:
            raise ValueError(f"ingredient defined more than once: {', '.join(ingredient_dupes)}")

        recipe_dupes = find_duplicates([r.name.en for r in self.recipes])
        if recipe_dupes:
            raise ValueError(f"recipe defined more than once: {', '.join(recipe_dupes)}")
        return self
