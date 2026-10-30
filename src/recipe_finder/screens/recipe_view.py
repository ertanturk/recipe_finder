"""Recipe view screen: single recipe detail with navigation and scroll."""

import re
import textwrap
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor

from prompt_toolkit import ANSI
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from rich.markup import escape

from recipe_finder.api_client import ApiClient, ApiClientError
from recipe_finder.locales import t
from recipe_finder.schemas import RecipeResponse
from recipe_finder.state import ResultQueue, SearchCriteria
from recipe_finder.telemetry import track
from recipe_finder.terminal import (
    get_content_width,
    get_pt_input,
    get_pt_output,
    is_interactive,
    is_utf8,
)
from recipe_finder.theme import (
    NutritionColors,
    create_console,
    get_box_characters,
    get_palette,
)

# Daily reference values (DRV) for calculating bar percentage
DRV_PROTEIN = 50.0
DRV_CARBS = 260.0
DRV_FAT = 70.0
DRV_FIBER = 28.0
DRV_SUGAR = 50.0
DRV_SODIUM = 2300.0
BAR_LENGTH = 20
MIN_WIDTH_FOR_BARS = 60
MAX_VISIBLE_INSTRUCTION_LINES = 6
INSTRUCTION_INDENT = 4
INSTRUCTION_NUMBER_PATTERN = re.compile(r"^(\d+[.)]\s+)(.*)$")


class RecipeDetailCache:
    """In-memory cache for recipe detail responses with background prefetching."""

    def __init__(self, client: ApiClient, lang: str = "en") -> None:
        self.client = client
        self.lang = lang
        self._cache: dict[int, RecipeResponse] = {}
        self._executor = ThreadPoolExecutor(max_workers=1)

    def get(self, recipe_id: int) -> RecipeResponse:
        """Return cached recipe or fetch synchronously from API."""
        if recipe_id not in self._cache:
            self._cache[recipe_id] = self.client.get_recipe(recipe_id, lang=self.lang)
        return self._cache[recipe_id]

    def prefetch(self, recipe_id: int) -> None:
        """Prefetch recipe in background thread if not already cached."""
        if recipe_id not in self._cache:
            self._executor.submit(self._fetch_silent, recipe_id)

    def _fetch_silent(self, recipe_id: int) -> None:
        try:
            if recipe_id not in self._cache:
                self._cache[recipe_id] = self.client.get_recipe(recipe_id, lang=self.lang)
        except Exception:
            pass

    def clear(self) -> None:
        """Clear cached recipe details."""
        self._cache.clear()

    def close(self) -> None:
        """Shut down background executor."""
        self._executor.shutdown(wait=False)


def render_recipe_results_summary(
    total_found: int,
    lang: str = "en",
    width: int = 80,
    no_color: bool = False,
) -> str:
    """Render a short summary of the number of matching recipes."""
    console = create_console(width=width, no_color=no_color)
    palette = get_palette(no_color)

    with console.capture() as capture:
        console.print(
            f"  [{palette.info}]{t('recipe_results_summary', lang).format(total=total_found)}[/{palette.info}]"
        )

    return capture.get()


def _render_bar(val: float, ref_val: float, bar_char: str, empty_char: str) -> str:
    """Generate visual progress bar string based on value vs reference."""
    filled = min(BAR_LENGTH, max(0, int(round((val / ref_val) * BAR_LENGTH))))
    empty = BAR_LENGTH - filled
    return f"{bar_char * filled}{empty_char * empty}"


def _wrap_instruction_lines(lines: Sequence[str], width: int) -> list[str]:
    """Wrap instructions while keeping numbered continuations aligned."""
    available_width = max(1, width - INSTRUCTION_INDENT)
    wrapped_lines: list[str] = []

    for line in lines:
        match = INSTRUCTION_NUMBER_PATTERN.match(line)
        continuation_indent = " " * len(match.group(1)) if match else ""
        wrapped_lines.extend(
            textwrap.wrap(
                line,
                width=available_width,
                subsequent_indent=continuation_indent,
                break_long_words=False,
                break_on_hyphens=False,
            )
            or [""]
        )

    return wrapped_lines


def render_recipe_view(
    recipe: RecipeResponse,
    position: int,
    total: int,
    criteria: SearchCriteria | None = None,
    instructions_scroll_offset: int = 0,
    chosen: bool = False,
    lang: str = "en",
    width: int = 80,
    no_color: bool = False,
) -> str:
    """Render recipe detail screen to an ANSI formatted string."""
    console = create_console(width=width, no_color=no_color)
    box = get_box_characters()
    palette = get_palette(no_color)
    nutrition_colors = NutritionColors()
    use_utf8 = is_utf8()

    bar_fill = "█" if use_utf8 else "#"
    bar_empty = "░" if use_utf8 else "-"

    content_width = min(width - 4, 76)
    divider = box.horizontal * content_width

    # Criteria matches check
    crit = criteria or SearchCriteria()
    calorie_match = crit.max_calorie is not None and recipe.nutrition.calorie <= crit.max_calorie
    protein_match = crit.min_protein is not None and recipe.nutrition.protein >= crit.min_protein
    carbs_match = (
        crit.min_carbohydrate is not None and recipe.nutrition.carbohydrate >= crit.min_carbohydrate
    )
    fat_match = crit.min_fat is not None and recipe.nutrition.fat >= crit.min_fat
    fiber_match = crit.min_fiber is not None and recipe.nutrition.fiber >= crit.min_fiber
    sugar_match = crit.min_sugar is not None and recipe.nutrition.sugar >= crit.min_sugar
    sodium_match = crit.min_sodium is not None and recipe.nutrition.sodium >= crit.min_sodium

    have_ingredient_ids = set(crit.ingredient_ids)

    with console.capture() as capture:
        console.print()

        # Title line with position
        pos_str = f"{position} / {total}"
        name_width = max(10, content_width - len(pos_str) - 2)
        escaped_title = escape(recipe.name)
        console.print(
            f"  [{palette.accent} bold]{escaped_title:<{name_width}}[/{palette.accent} bold]  [{palette.muted}]{pos_str}[/{palette.muted}]"
        )
        console.print(f"  [{palette.border}]{divider}[/{palette.border}]")

        # Prep time and Category line
        prep_label = t("recipe_prep_time", lang)
        min_unit = t("recipe_unit_min", lang)
        cat_label = t("recipe_category", lang)
        cats_str = (
            ", ".join(c.name for c in recipe.categories)
            if recipe.categories
            else t("wizard_category_any", lang)
        )
        console.print(
            f"  [{palette.muted}]{prep_label}:[/{palette.muted}] [{palette.text}]{recipe.prep_time_minutes} {min_unit}[/{palette.text}]     [{palette.muted}]{cat_label}:[/{palette.muted}] [{palette.text}]{escape(cats_str)}[/{palette.text}]"
        )
        console.print()

        # Nutrition block
        console.print(
            f"  [{palette.text} bold]{t('recipe_nutrition_title', lang)}[/{palette.text} bold]"
        )

        cal_color = palette.success if calorie_match else palette.text
        cal_val_str = f"{int(round(recipe.nutrition.calorie))} kcal"
        console.print(
            f"  [{palette.muted}]{t('nutrient_calories', lang):<10}[/{palette.muted}] [{cal_color} bold]{cal_val_str}[/{cal_color} bold]"
        )

        show_bars = width >= MIN_WIDTH_FOR_BARS

        nutrients_data = [
            (
                t("nutrient_protein", lang),
                recipe.nutrition.protein,
                DRV_PROTEIN,
                "g",
                nutrition_colors.protein,
                protein_match,
            ),
            (
                t("recipe_nutrient_carbs", lang),
                recipe.nutrition.carbohydrate,
                DRV_CARBS,
                "g",
                nutrition_colors.carbohydrate,
                carbs_match,
            ),
            (
                t("nutrient_fat", lang),
                recipe.nutrition.fat,
                DRV_FAT,
                "g",
                nutrition_colors.fat,
                fat_match,
            ),
            (
                t("nutrient_fiber", lang),
                recipe.nutrition.fiber,
                DRV_FIBER,
                "g",
                nutrition_colors.fiber,
                fiber_match,
            ),
            (
                t("nutrient_sugar", lang),
                recipe.nutrition.sugar,
                DRV_SUGAR,
                "g",
                nutrition_colors.sugar,
                sugar_match,
            ),
            (
                t("nutrient_sodium", lang),
                recipe.nutrition.sodium,
                DRV_SODIUM,
                "mg",
                nutrition_colors.sodium,
                sodium_match,
            ),
        ]

        for label, val, ref_val, unit, default_color, matched in nutrients_data:
            color = palette.success if matched else default_color
            val_display = f"{int(val) if val.is_integer() else val:g} {unit}"
            if show_bars:
                bar_str = _render_bar(val, ref_val, bar_fill, bar_empty)
                console.print(
                    f"  [{palette.muted}]{label:<10}[/{palette.muted}] [{color}]{bar_str}[/{color}]   [{color} bold]{val_display:>8}[/{color} bold]"
                )
            else:
                console.print(
                    f"  [{palette.muted}]{label:<10}[/{palette.muted}] [{color} bold]{val_display}[/{color} bold]"
                )

        console.print()

        # Ingredients block
        console.print(
            f"  [{palette.text} bold]{t('recipe_ingredients_title', lang)}[/{palette.text} bold]"
        )
        have_tag = escape(f"[{t('recipe_have', lang)}]")
        need_tag = escape(f"[{t('recipe_need', lang)}]")

        for ing in recipe.ingredients:
            has_ing = ing.ingredient_id in have_ingredient_ids
            tag_style = palette.success if has_ing else palette.muted
            tag = have_tag if has_ing else need_tag
            qty_str = f"{int(ing.quantity_grams) if ing.quantity_grams.is_integer() else ing.quantity_grams:g} g"
            escaped_name = escape(ing.name)
            console.print(
                f"  [{tag_style} bold]{tag}[/{tag_style} bold]  [{palette.text}]{escaped_name:<24}[/{palette.text}] [{palette.muted}]{qty_str:>8}[/{palette.muted}]"
            )

        console.print()

        # Instructions block with scroll
        console.print(
            f"  [{palette.text} bold]{t('recipe_instructions_title', lang)}[/{palette.text} bold]"
        )
        raw_lines = [line.strip() for line in recipe.instructions.splitlines() if line.strip()]
        if not raw_lines:
            raw_lines = [recipe.instructions]
        instruction_lines = _wrap_instruction_lines(raw_lines, content_width)

        total_lines = len(instruction_lines)
        offset = max(0, min(instructions_scroll_offset, max(0, total_lines - 1)))
        visible_lines = instruction_lines[offset : offset + MAX_VISIBLE_INSTRUCTION_LINES]

        if offset > 0:
            console.print(f"    [{palette.muted}]^ (scroll up)[/{palette.muted}]")

        for line in visible_lines:
            console.print(
                f"{' ' * INSTRUCTION_INDENT}[{palette.text}]{escape(line)}[/{palette.text}]"
            )

        if offset + MAX_VISIBLE_INSTRUCTION_LINES < total_lines:
            console.print(f"    [{palette.muted}]v (scroll down)[/{palette.muted}]")

        console.print()
        if chosen:
            console.print(
                f"  [{palette.success} bold]{t('recipe_chosen_message', lang)}[/{palette.success} bold]"
            )
            console.print(
                f"  [{palette.muted}]{t('action_main_menu', lang)}: Esc[/{palette.muted}]"
            )
        else:
            console.print(f"  [{palette.muted}]{t('nav_recipe', lang)}[/{palette.muted}]")

    return capture.get()


def render_recipe_chosen_notice(
    recipe_name: str,
    lang: str = "en",
    width: int = 80,
    no_color: bool = False,
) -> str:
    """Render confirmation notice when user selects a recipe."""
    console = create_console(width=width, no_color=no_color)
    box = get_box_characters()
    palette = get_palette(no_color)

    title = t("app_title", lang)
    msg = t("recipe_chosen_message", lang)
    action_text = t("action_main_menu", lang)

    with console.capture() as capture:
        console.print()
        console.print(f"  [{palette.accent} bold]{title}[/{palette.accent} bold]")
        console.print(f"  [{palette.success} bold]{escape(recipe_name)}[/{palette.success} bold]")
        console.print(f"  [{palette.text}]{msg}[/{palette.text}]")
        console.print()
        console.print(
            f"    [{palette.accent} bold]{box.pointer} {action_text}[/{palette.accent} bold]"
        )
        console.print()

    return capture.get()


def show_recipe_view(
    queue: ResultQueue | Sequence[int],
    client: ApiClient,
    criteria: SearchCriteria | None = None,
    lang: str = "en",
    width: int | None = None,
) -> str:
    """Display interactive recipe viewer.

    Returns:
        'main_menu', 'new_search', or 'chosen'.
    """
    result_queue = queue if isinstance(queue, ResultQueue) else ResultQueue(recipe_ids=list(queue))

    if not is_interactive() or result_queue.total == 0:
        return "main_menu"

    recipe_cache = RecipeDetailCache(client=client, lang=lang)
    scroll_offset = 0
    final_action = "main_menu"

    try:
        while result_queue.current_id is not None:
            cid = result_queue.current_id

            # Prefetch next recipe in background thread
            if result_queue.has_next():
                next_id = result_queue.recipe_ids[result_queue.index + 1]
                recipe_cache.prefetch(next_id)

            try:
                recipe = recipe_cache.get(cid)
            except ApiClientError as exc:
                # 404 handling: remove missing recipe and advance
                if exc.error_code == "recipe_not_found" or "404" in exc.message:
                    was_last_recipe = not result_queue.has_next()
                    result_queue.remove_current()
                    if result_queue.total == 0:
                        return "main_menu"
                    if was_last_recipe:
                        from recipe_finder.screens.notices import show_end_of_results_screen

                        choice = show_end_of_results_screen(lang=lang, width=width)
                        return "new_search" if choice == "wizard" else "main_menu"
                    continue

                from recipe_finder.screens.notices import show_error_screen

                choice = show_error_screen(message=exc.message, lang=lang, width=width)
                if choice == "retry":
                    continue
                return "main_menu"

            # Run interactive viewer for current recipe
            current_recipe = recipe
            scroll_state = [scroll_offset]
            chosen_state = [False]
            kb = KeyBindings()
            step_action = "exit"

            @kb.add("c-c")
            def _(event):
                event.app.exit(exception=KeyboardInterrupt())

            @kb.add("escape")
            def _(event):
                nonlocal step_action, final_action
                step_action = "menu"
                final_action = "main_menu"
                event.app.exit()

            @kb.add("right")
            @kb.add("n")
            def _(event, current_recipe=current_recipe, chosen_state=chosen_state):
                nonlocal step_action, final_action
                if chosen_state[0]:
                    return
                # Skip-once telemetry rule
                if result_queue.mark_skipped():
                    track(
                        "recipe_skipped",
                        {
                            "recipe_id": current_recipe.recipe_id,
                            "position": result_queue.position,
                            "total": result_queue.total,
                        },
                    )

                if result_queue.has_next():
                    step_action = "next"
                    event.app.exit()
                else:
                    step_action = "end_of_results"
                    event.app.exit()

            @kb.add("left")
            @kb.add("p")
            def _(event, chosen_state=chosen_state):
                nonlocal step_action
                if chosen_state[0]:
                    return
                if result_queue.has_previous():
                    step_action = "prev"
                    event.app.exit()

            @kb.add("enter")
            def _(event, current_recipe=current_recipe, chosen_state=chosen_state):
                if not chosen_state[0]:
                    track(
                        "recipe_clicked",
                        {
                            "recipe_id": current_recipe.recipe_id,
                            "position": result_queue.position,
                            "total": result_queue.total,
                        },
                    )
                    chosen_state[0] = True
                    event.app.invalidate()

            @kb.add("up")
            @kb.add("k")
            def _(event, scroll_state=scroll_state):
                if scroll_state[0] > 0:
                    scroll_state[0] -= 1
                    event.app.invalidate()

            @kb.add("down")
            @kb.add("j")
            def _(event, scroll_state=scroll_state):
                scroll_state[0] += 1
                event.app.invalidate()

            @kb.add("pageup")
            def _(event, scroll_state=scroll_state):
                nonlocal scroll_offset
                scroll_offset = max(0, scroll_offset - 5)
                event.app.invalidate()

            @kb.add("pagedown")
            def _(event, scroll_state=scroll_state):
                scroll_state[0] += 5
                event.app.invalidate()

            def get_text(
                current_recipe=current_recipe,
                scroll_state=scroll_state,
                chosen_state=chosen_state,
            ):
                cw = width or get_content_width()
                return ANSI(
                    render_recipe_view(
                        recipe=current_recipe,
                        position=result_queue.position,
                        total=result_queue.total,
                        criteria=criteria,
                        instructions_scroll_offset=scroll_state[0],
                        chosen=chosen_state[0],
                        lang=lang,
                        width=cw,
                    )
                )

            app: Application[None] = Application(
                layout=Layout(Window(FormattedTextControl(get_text))),
                key_bindings=kb,
                full_screen=False,
                output=get_pt_output(),
                input=get_pt_input(),
            )
            app.run()

            if step_action == "next":
                result_queue.next()
                scroll_offset = 0
            elif step_action == "prev":
                result_queue.previous()
                scroll_offset = 0
            elif step_action == "end_of_results":
                from recipe_finder.screens.notices import show_end_of_results_screen

                choice = show_end_of_results_screen(lang=lang, width=width)
                if choice == "new_search":
                    return "new_search"
                return "main_menu"
            elif step_action == "menu":
                return "main_menu"

        return final_action

    finally:
        recipe_cache.close()
