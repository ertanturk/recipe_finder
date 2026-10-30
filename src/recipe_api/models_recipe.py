from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class RecipeBase(DeclarativeBase):
    """Base class for the Recipe DB tables."""


class Language(RecipeBase):
    """Represents a language."""

    __tablename__ = "Languages"
    __table_args__ = {"info": {"bind_key": "RecipeDB"}}

    language_code: Mapped[str] = mapped_column(String(10), primary_key=True, nullable=False)
    language_name: Mapped[str] = mapped_column(String(50), nullable=False)

    localizations: Mapped[list["Localization"]] = relationship(back_populates="language")


class TextKey(RecipeBase):
    """Represents a text key for localization."""

    __tablename__ = "Text_Keys"
    __table_args__ = {"info": {"bind_key": "RecipeDB"}}

    text_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, nullable=False)


class Localization(RecipeBase):
    """Represents a localization for a recipe."""

    __tablename__ = "Localization"
    __table_args__ = {"info": {"bind_key": "RecipeDB"}}

    text_id: Mapped[int] = mapped_column(
        ForeignKey("Text_Keys.text_id"), primary_key=True, nullable=False
    )
    language_code: Mapped[str] = mapped_column(
        ForeignKey("Languages.language_code"), primary_key=True, nullable=False
    )
    text_value: Mapped[str] = mapped_column(Text, nullable=False)

    language: Mapped["Language"] = relationship(back_populates="localizations")


class Recipe(RecipeBase):
    """Represents a recipe."""

    __tablename__ = "Recipes"
    __table_args__ = (
        CheckConstraint("recipe_prep_time_in_minutes > 0", name="CK_Recipes_PrepTime"),
        CheckConstraint("name_text_id <> instructions_text_id", name="CK_Recipes_Text_Ids"),
        {"info": {"bind_key": "RecipeDB"}},
    )

    recipe_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, nullable=False)
    name_text_id: Mapped[int] = mapped_column(
        ForeignKey("Text_Keys.text_id"), unique=True, nullable=False
    )
    instructions_text_id: Mapped[int] = mapped_column(
        ForeignKey("Text_Keys.text_id"), unique=True, nullable=False
    )
    recipe_prep_time_in_minutes: Mapped[int] = mapped_column(nullable=False)

    categories: Mapped[list["RecipeCategory"]] = relationship(
        secondary="Recipe_Categories", back_populates="recipes"
    )

    recipe_ingredients: Mapped[list["RecipeIngredient"]] = relationship(back_populates="recipe")


class RecipeCategory(RecipeBase):
    """Represents a category for a recipe."""

    __tablename__ = "Recipe_Category"
    __table_args__ = {"info": {"bind_key": "RecipeDB"}}

    category_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, nullable=False)
    name_text_id: Mapped[int] = mapped_column(
        ForeignKey("Text_Keys.text_id"), unique=True, nullable=False
    )

    recipes: Mapped[list["Recipe"]] = relationship(
        secondary="Recipe_Categories", back_populates="categories"
    )


class RecipeCategories(RecipeBase):
    """Represents the many-to-many relationship between recipes and categories."""

    __tablename__ = "Recipe_Categories"
    __table_args__ = {"info": {"bind_key": "RecipeDB"}}

    recipe_id: Mapped[int] = mapped_column(
        ForeignKey("Recipes.recipe_id"), primary_key=True, nullable=False
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("Recipe_Category.category_id"), primary_key=True, nullable=False
    )


class Ingredient(RecipeBase):
    """Represents an ingredient used in a recipe."""

    __tablename__ = "Ingredients"
    __table_args__ = (
        CheckConstraint("ingredient_calorie >= 0"),
        CheckConstraint("ingredient_protein >= 0"),
        CheckConstraint("ingredient_fat >= 0"),
        CheckConstraint("ingredient_carbohydrate >= 0"),
        CheckConstraint("ingredient_sugar >= 0"),
        CheckConstraint("ingredient_fiber >= 0"),
        CheckConstraint("ingredient_sodium >= 0"),
        {"info": {"bind_key": "RecipeDB"}},
    )

    ingredient_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, nullable=False)
    name_text_id: Mapped[int] = mapped_column(
        ForeignKey("Text_Keys.text_id"), unique=True, nullable=False
    )
    ingredient_calorie: Mapped[float] = mapped_column(nullable=False)
    ingredient_protein: Mapped[float] = mapped_column(nullable=False)
    ingredient_fat: Mapped[float] = mapped_column(nullable=False)
    ingredient_carbohydrate: Mapped[float] = mapped_column(nullable=False)
    ingredient_sugar: Mapped[float] = mapped_column(nullable=False)
    ingredient_fiber: Mapped[float] = mapped_column(nullable=False)
    ingredient_sodium: Mapped[float] = mapped_column(nullable=False)


class RecipeIngredient(RecipeBase):
    """Represents an ingredient used in a recipe."""

    __tablename__ = "Recipe_Ingredients"
    __table_args__ = (
        CheckConstraint("ingredient_quantity > 0"),
        {"info": {"bind_key": "RecipeDB"}},
    )

    recipe_id: Mapped[int] = mapped_column(ForeignKey("Recipes.recipe_id"), primary_key=True)
    ingredient_id: Mapped[int] = mapped_column(
        ForeignKey("Ingredients.ingredient_id"), primary_key=True
    )
    ingredient_quantity: Mapped[float] = mapped_column(nullable=False)

    recipe: Mapped["Recipe"] = relationship(back_populates="recipe_ingredients")
