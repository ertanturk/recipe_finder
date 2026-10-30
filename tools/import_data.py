"""Tool to import ingredients and recipes from a JSON file into RecipeDB."""

import contextlib
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, NamedTuple

import typer
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from sqlalchemy import Engine, create_engine, select
from sqlalchemy.orm import Session

from recipe_api.models_recipe import (
    Ingredient,
    Localization,
    Recipe,
    RecipeCategories,
    RecipeCategory,
    RecipeIngredient,
    TextKey,
)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from tools.model_data import Cookbook, LocalizedString  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    with contextlib.suppress(Exception):
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore
if hasattr(sys.stderr, "reconfigure"):
    with contextlib.suppress(Exception):
        sys.stderr.reconfigure(encoding="utf-8")  # type: ignore

console = Console()
app = typer.Typer(
    name="import-data",
    help="Import ingredients and recipes from a JSON file into RecipeDB.",
    rich_markup_mode="rich",
    add_completion=False,
)

DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = ("en", "tr")


class Settings(BaseSettings):
    """Database settings for data import."""

    ADMIN_DB_URL: SecretStr

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@dataclass
class ExistingIds:
    """Stores existing database IDs mapped by casefolded English name."""

    ingredients: dict[str, int]
    recipes: dict[str, int]
    categories: dict[str, int]


class ImportStats(NamedTuple):
    """Counts of added and skipped items."""

    added: int
    skipped: int


def get_admin_engine() -> Engine:
    """Create a database engine with admin privileges."""
    return create_engine(Settings().ADMIN_DB_URL.get_secret_value())


def load_cookbook(path: Path) -> Cookbook:
    """Read the JSON file and check it against the Cookbook model."""
    return Cookbook.model_validate_json(path.read_text(encoding="utf-8"))


def create_text(session: Session, text: LocalizedString) -> int:
    """Insert a text key and its localizations, returning the generated text ID."""
    text_key = TextKey()
    session.add(text_key)
    session.flush()

    for lang in SUPPORTED_LANGUAGES:
        session.add(
            Localization(
                text_id=text_key.text_id,
                language_code=lang,
                text_value=getattr(text, lang),
            )
        )
    session.flush()
    return text_key.text_id


def load_existing(session: Session) -> ExistingIds:
    """Load existing ingredient, recipe, and category IDs mapped by English name."""
    ingredient_stmt = (
        select(Localization.text_value, Ingredient.ingredient_id)
        .join(Ingredient, Ingredient.name_text_id == Localization.text_id)
        .where(Localization.language_code == DEFAULT_LANGUAGE)
    )
    ingredients = {
        name.casefold(): ingredient_id for name, ingredient_id in session.execute(ingredient_stmt)
    }

    recipe_stmt = (
        select(Localization.text_value, Recipe.recipe_id)
        .join(Recipe, Recipe.name_text_id == Localization.text_id)
        .where(Localization.language_code == DEFAULT_LANGUAGE)
    )
    recipes = {name.casefold(): recipe_id for name, recipe_id in session.execute(recipe_stmt)}

    category_stmt = (
        select(Localization.text_value, RecipeCategory.category_id)
        .join(RecipeCategory, RecipeCategory.name_text_id == Localization.text_id)
        .where(Localization.language_code == DEFAULT_LANGUAGE)
    )
    categories = {
        name.casefold(): category_id for name, category_id in session.execute(category_stmt)
    }

    return ExistingIds(
        ingredients=ingredients,
        recipes=recipes,
        categories=categories,
    )


def find_problems(cookbook: Cookbook, existing: ExistingIds) -> list[str]:
    """Find missing ingredients or categories referenced by recipes."""
    file_ingredients = {item.name.en.casefold() for item in cookbook.ingredients}
    available_ingredients = set(existing.ingredients.keys()) | file_ingredients
    available_categories = set(existing.categories.keys())

    problems: list[str] = []
    for recipe in cookbook.recipes:
        for ingredient in recipe.ingredients:
            if ingredient.name.casefold() not in available_ingredients:
                problems.append(
                    f"Recipe '{recipe.name.en}' references unknown ingredient: '{ingredient.name}'"
                )
        for category in recipe.categories:
            if category.casefold() not in available_categories:
                problems.append(
                    f"Recipe '{recipe.name.en}' references unknown category: '{category}'"
                )
    return problems


def import_ingredients(session: Session, cookbook: Cookbook, existing: ExistingIds) -> ImportStats:
    """Import new ingredients, skipping those that already exist."""
    added = 0
    skipped = 0

    for ingredient in cookbook.ingredients:
        name_key = ingredient.name.en.casefold()
        if name_key in existing.ingredients:
            skipped += 1
            continue

        name_text_id = create_text(session, ingredient.name)
        db_ingredient = Ingredient(
            name_text_id=name_text_id,
            ingredient_calorie=ingredient.per_100g.calorie,
            ingredient_protein=ingredient.per_100g.protein,
            ingredient_fat=ingredient.per_100g.fat,
            ingredient_carbohydrate=ingredient.per_100g.carbohydrate,
            ingredient_sugar=ingredient.per_100g.sugar,
            ingredient_fiber=ingredient.per_100g.fiber,
            ingredient_sodium=ingredient.per_100g.sodium,
        )
        session.add(db_ingredient)
        session.flush()

        existing.ingredients[name_key] = db_ingredient.ingredient_id
        added += 1

    return ImportStats(added=added, skipped=skipped)


def import_recipes(session: Session, cookbook: Cookbook, existing: ExistingIds) -> ImportStats:
    """Import new recipes, skipping those that already exist."""
    added = 0
    skipped = 0

    for recipe in cookbook.recipes:
        name_key = recipe.name.en.casefold()
        if name_key in existing.recipes:
            skipped += 1
            continue

        name_text_id = create_text(session, recipe.name)
        instructions_text_id = create_text(session, recipe.instructions)

        db_recipe = Recipe(
            name_text_id=name_text_id,
            instructions_text_id=instructions_text_id,
            recipe_prep_time_in_minutes=recipe.prep_time_minutes,
        )
        session.add(db_recipe)
        session.flush()

        for category in recipe.categories:
            category_id = existing.categories[category.casefold()]
            session.add(
                RecipeCategories(
                    recipe_id=db_recipe.recipe_id,
                    category_id=category_id,
                )
            )

        for ingredient in recipe.ingredients:
            ingredient_id = existing.ingredients[ingredient.name.casefold()]
            session.add(
                RecipeIngredient(
                    recipe_id=db_recipe.recipe_id,
                    ingredient_id=ingredient_id,
                    ingredient_quantity=ingredient.grams,
                )
            )

        session.flush()
        existing.recipes[name_key] = db_recipe.recipe_id
        added += 1

    return ImportStats(added=added, skipped=skipped)


def execute_import(
    session: Session,
    cookbook: Cookbook,
    dry_run: bool = False,
    console_out: Console | None = None,
) -> tuple[ImportStats, ImportStats]:
    """Execute validation and import within a database session.

    Args:
        session: Active database session.
        cookbook: Validated cookbook data.
        dry_run: When True, rolls back the transaction.
        console_out: Optional Rich console for styled output.

    Returns:
        Tuple containing ingredient stats and recipe stats.
    """
    out = console_out or console

    with out.status(
        "[bold cyan]Loading existing records from database...[/bold cyan]", spinner="dots"
    ):
        existing = load_existing(session)
    out.print(
        f"[bold green]✓[/bold green] Database cache loaded: "
        f"[cyan]{len(existing.ingredients)}[/cyan] ingredients, "
        f"[cyan]{len(existing.recipes)}[/cyan] recipes, "
        f"[cyan]{len(existing.categories)}[/cyan] categories"
    )

    with out.status("[bold cyan]Validating recipe dependencies...[/bold cyan]", spinner="dots"):
        problems = find_problems(cookbook, existing)
    if problems:
        out.print(f"[bold red]Found {len(problems)} problem(s):[/bold red]")
        for problem in problems:
            out.print(f"  [red]-[/red] {problem}")
        sys.exit(1)
    out.print("[bold green]✓[/bold green] Reference check passed: all dependencies resolved")

    try:
        with out.status("[bold cyan]Importing ingredients...[/bold cyan]", spinner="dots"):
            ingredient_stats = import_ingredients(session, cookbook, existing)
        out.print(
            f"[bold green]✓[/bold green] Ingredients processed: "
            f"[green]{ingredient_stats.added} added[/green], "
            f"[yellow]{ingredient_stats.skipped} skipped[/yellow]"
        )

        with out.status("[bold cyan]Importing recipes...[/bold cyan]", spinner="dots"):
            recipe_stats = import_recipes(session, cookbook, existing)
        out.print(
            f"[bold green]✓[/bold green] Recipes processed: "
            f"[green]{recipe_stats.added} added[/green], "
            f"[yellow]{recipe_stats.skipped} skipped[/yellow]"
        )

        with out.status(
            "[bold cyan]Finalizing database transaction...[/bold cyan]", spinner="dots"
        ):
            if dry_run:
                session.rollback()
            else:
                session.commit()

        table = Table(
            title="Import Summary",
            border_style="cyan",
            header_style="bold cyan",
            show_lines=True,
        )
        table.add_column("Entity", style="bold")
        table.add_column("Added", justify="right", style="green")
        table.add_column("Skipped", justify="right", style="yellow")
        table.add_column("Total", justify="right", style="bold")
        table.add_row(
            "Ingredients",
            str(ingredient_stats.added),
            str(ingredient_stats.skipped),
            str(ingredient_stats.added + ingredient_stats.skipped),
        )
        table.add_row(
            "Recipes",
            str(recipe_stats.added),
            str(recipe_stats.skipped),
            str(recipe_stats.added + recipe_stats.skipped),
        )
        out.print(table)

        out.print(
            f"{ingredient_stats.added} ingredients added, {ingredient_stats.skipped} skipped, "
            f"{recipe_stats.added} recipes added, {recipe_stats.skipped} skipped"
        )
        if dry_run:
            out.print(
                "[bold yellow][DRY RUN] All database changes have been rolled back.[/bold yellow]"
            )
        else:
            out.print("[bold green]✓ All database changes successfully committed.[/bold green]")
        out.print("[dim]Remember to run db/check_rules.sql.[/dim]")
        return ingredient_stats, recipe_stats
    except Exception as err:
        session.rollback()
        out.print(f"[bold red]Import transaction failed:[/bold red] {err}")
        raise


@app.command()
def main(
    path: Annotated[
        Path,
        typer.Argument(
            help="Path to the JSON cookbook file to import.",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
        ),
    ],
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            "-d",
            help="Simulate import and roll back all changes instead of committing.",
        ),
    ] = False,
) -> None:
    """Import ingredients and recipes from a JSON file into RecipeDB."""
    console.print(
        Panel.fit(
            f"[bold cyan]RecipeDB Data Import[/bold cyan]\n"
            f"[dim]File:[/dim] [bright_white]{path}[/bright_white]\n"
            f"[dim]Mode:[/dim] {'[bold yellow]DRY RUN (no database changes will be saved)[/bold yellow]' if dry_run else '[bold green]LIVE IMPORT (changes will be committed)[/bold green]'}",
            border_style="cyan",
            title="[bold]Recipe Finder[/bold]",
        )
    )

    with console.status(
        "[bold cyan]Reading and validating cookbook JSON...[/bold cyan]", spinner="dots"
    ):
        try:
            cookbook = load_cookbook(path)
        except Exception as err:
            console.print(f"[bold red]Failed to load cookbook file:[/bold red] {err}")
            raise typer.Exit(code=1) from err

    console.print(
        f"[bold green]✓[/bold green] Loaded cookbook: "
        f"[cyan]{len(cookbook.ingredients)}[/cyan] ingredients, "
        f"[cyan]{len(cookbook.recipes)}[/cyan] recipes"
    )

    with console.status("[bold cyan]Connecting to database...[/bold cyan]", spinner="dots"):
        try:
            engine = get_admin_engine()
        except Exception as err:
            console.print(f"[bold red]Database connection failed:[/bold red] {err}")
            raise typer.Exit(code=1) from err

    with Session(engine) as session:
        execute_import(session, cookbook, dry_run=dry_run, console_out=console)


if __name__ == "__main__":
    app()
