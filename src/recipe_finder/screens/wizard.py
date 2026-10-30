"""Search wizard screen: ingredients, nutrition, category, and review."""

from collections.abc import Sequence
from dataclasses import dataclass

from prompt_toolkit import ANSI
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from rich.markup import escape

from recipe_finder.api_client import ApiClient, ApiClientError
from recipe_finder.cache import IngredientCache, load_ingredient_cache
from recipe_finder.locales import t
from recipe_finder.schemas import CategoryResponse
from recipe_finder.state import SearchCriteria
from recipe_finder.telemetry import track
from recipe_finder.terminal import (
    get_content_width,
    get_pt_input,
    get_pt_output,
    is_interactive,
)
from recipe_finder.theme import create_console, get_box_characters, get_palette

REVIEW_ACTIONS = ("search", "edit", "cancel")


@dataclass(frozen=True)
class NutrientMetric:
    """Nutritional metric definition for wizard selection."""

    key: str
    label_key: str
    target_type: str
    unit: str
    attribute_name: str


NUTRIENT_METRICS: tuple[NutrientMetric, ...] = (
    NutrientMetric(
        key="calories",
        label_key="nutrient_calories",
        target_type="max",
        unit="kcal",
        attribute_name="max_calorie",
    ),
    NutrientMetric(
        key="protein",
        label_key="nutrient_protein",
        target_type="min",
        unit="g",
        attribute_name="min_protein",
    ),
    NutrientMetric(
        key="carbohydrate",
        label_key="nutrient_carbohydrate",
        target_type="min",
        unit="g",
        attribute_name="min_carbohydrate",
    ),
    NutrientMetric(
        key="fat",
        label_key="nutrient_fat",
        target_type="min",
        unit="g",
        attribute_name="min_fat",
    ),
    NutrientMetric(
        key="fiber",
        label_key="nutrient_fiber",
        target_type="min",
        unit="g",
        attribute_name="min_fiber",
    ),
    NutrientMetric(
        key="sugar",
        label_key="nutrient_sugar",
        target_type="min",
        unit="g",
        attribute_name="min_sugar",
    ),
    NutrientMetric(
        key="sodium",
        label_key="nutrient_sodium",
        target_type="min",
        unit="mg",
        attribute_name="min_sodium",
    ),
)


def render_wizard_step1(
    chips: Sequence[str],
    query: str,
    suggestions: Sequence[str],
    selected_suggestion_index: int,
    no_match: bool = False,
    lang: str = "en",
    width: int = 80,
    no_color: bool = False,
) -> str:
    """Render wizard step 1: ingredient input and autocomplete suggestions."""
    console = create_console(width=width, no_color=no_color)
    box = get_box_characters()
    palette = get_palette(no_color)

    step_label = f"{t('wizard_step', lang)} 1/3: {t('wizard_step_1_title', lang)}"
    hint = t("wizard_step_1_hint", lang)
    nav_hint = t("nav_wizard_step1", lang)

    with console.capture() as capture:
        console.print()
        console.print(f"  [{palette.accent} bold]{step_label}[/{palette.accent} bold]")
        console.print(f"  [{palette.muted}]{hint}[/{palette.muted}]")
        console.print(
            f"  [{palette.border}]{box.horizontal * min(width - 4, 46)}[/{palette.border}]"
        )
        console.print()

        if chips:
            chip_line = " ".join(
                f"[{palette.info}]{escape(f'[{c}]')}[/{palette.info}]" for c in chips
            )
            console.print(f"  {chip_line}")
            console.print()

        console.print(
            f"  [{palette.accent}]{box.pointer}[/{palette.accent}] [{palette.text}]{escape(query)}[/{palette.text}][blink]_[/blink]"
        )
        console.print()

        if no_match and query.strip():
            msg = t("wizard_no_ingredient_found", lang)
            console.print(f"    [{palette.warning}]{msg}[/{palette.warning}]")
        elif suggestions:
            for idx, item in enumerate(suggestions):
                escaped_item = escape(item)
                if idx == selected_suggestion_index:
                    console.print(
                        f"    [{palette.accent} bold]{box.pointer} {escaped_item}[/{palette.accent} bold]"
                    )
                else:
                    console.print(f"      [{palette.text}]{escaped_item}[/{palette.text}]")

        console.print()
        console.print(f"  [{palette.muted}]{nav_hint}[/{palette.muted}]")

    return capture.get()


def render_wizard_step2_select(
    selected_index: int,
    checked_keys: set[str],
    lang: str = "en",
    width: int = 80,
    no_color: bool = False,
) -> str:
    """Render wizard step 2 selection: pick which nutrition metrics to set."""
    console = create_console(width=width, no_color=no_color)
    box = get_box_characters()
    palette = get_palette(no_color)

    step_label = f"{t('wizard_step', lang)} 2/3: {t('wizard_step_2_title', lang)}"
    hint = t("wizard_step_2_hint", lang)
    nav_hint = t("nav_wizard_select", lang)

    with console.capture() as capture:
        console.print()
        console.print(f"  [{palette.accent} bold]{step_label}[/{palette.accent} bold]")
        console.print(f"  [{palette.muted}]{hint}[/{palette.muted}]")
        console.print(
            f"  [{palette.border}]{box.horizontal * min(width - 4, 46)}[/{palette.border}]"
        )
        console.print()

        for idx, metric in enumerate(NUTRIENT_METRICS):
            mark = escape("[x]") if metric.key in checked_keys else escape("[ ]")
            label = f"{t(metric.label_key, lang)} ({metric.target_type} {metric.unit})"
            if idx == selected_index:
                console.print(
                    f"    [{palette.accent} bold]{box.pointer} {mark} {label}[/{palette.accent} bold]"
                )
            else:
                console.print(f"      [{palette.text}]{mark} {label}[/{palette.text}]")

        console.print()
        console.print(f"  [{palette.muted}]{nav_hint}[/{palette.muted}]")

    return capture.get()


def render_wizard_step2_input(
    metric: NutrientMetric,
    input_value: str,
    error_message: str = "",
    lang: str = "en",
    width: int = 80,
    no_color: bool = False,
) -> str:
    """Render wizard step 2 input: enter numeric value for selected metric."""
    console = create_console(width=width, no_color=no_color)
    box = get_box_characters()
    palette = get_palette(no_color)

    step_label = f"{t('wizard_step', lang)} 2/3: {t('wizard_step_2_title', lang)}"
    metric_label = f"{t(metric.label_key, lang)} ({metric.target_type} {metric.unit})"
    prompt = f"{t('wizard_step_2_enter_value', lang)} {metric_label}"
    nav_hint = t("nav_wizard_input", lang)

    with console.capture() as capture:
        console.print()
        console.print(f"  [{palette.accent} bold]{step_label}[/{palette.accent} bold]")
        console.print(f"  [{palette.text}]{prompt}[/{palette.text}]")
        console.print(
            f"  [{palette.border}]{box.horizontal * min(width - 4, 46)}[/{palette.border}]"
        )
        console.print()

        console.print(
            f"  [{palette.accent}]{box.pointer}[/{palette.accent}] [{palette.text}]{escape(input_value)}[/{palette.text}][blink]_[/blink]"
        )

        if error_message:
            console.print(f"  [{palette.error}]{error_message}[/{palette.error}]")

        console.print()
        console.print(f"  [{palette.muted}]{nav_hint}[/{palette.muted}]")

    return capture.get()


def render_wizard_step3_category(
    categories: Sequence[CategoryResponse],
    selected_index: int,
    lang: str = "en",
    width: int = 80,
    no_color: bool = False,
) -> str:
    """Render wizard step 3: category selection list with Any default."""
    console = create_console(width=width, no_color=no_color)
    box = get_box_characters()
    palette = get_palette(no_color)

    step_label = f"{t('wizard_step', lang)} 3/3: {t('wizard_step_3_title', lang)}"
    nav_hint = t("nav_wizard_category", lang)

    items = [t("wizard_category_any", lang)] + [c.name for c in categories]

    with console.capture() as capture:
        console.print()
        console.print(f"  [{palette.accent} bold]{step_label}[/{palette.accent} bold]")
        console.print(
            f"  [{palette.border}]{box.horizontal * min(width - 4, 46)}[/{palette.border}]"
        )
        console.print()

        for idx, label in enumerate(items):
            if idx == selected_index:
                console.print(
                    f"    [{palette.accent} bold]{box.pointer} {label}[/{palette.accent} bold]"
                )
            else:
                console.print(f"      [{palette.text}]{label}[/{palette.text}]")

        console.print()
        console.print(f"  [{palette.muted}]{nav_hint}[/{palette.muted}]")

    return capture.get()


def render_wizard_review(
    criteria: SearchCriteria,
    selected_option_index: int,
    validation_error: str = "",
    lang: str = "en",
    width: int = 80,
    no_color: bool = False,
) -> str:
    """Render search review screen with summary and action choices."""
    console = create_console(width=width, no_color=no_color)
    box = get_box_characters()
    palette = get_palette(no_color)

    title = t("wizard_review_title", lang)
    divider = box.horizontal * min(width - 4, 46)
    actions = [
        t("wizard_review_action_search", lang),
        t("wizard_review_action_edit", lang),
        t("wizard_review_action_cancel", lang),
    ]
    nav_hint = t("nav_wizard_review", lang)

    with console.capture() as capture:
        console.print()
        console.print(f"  [{palette.accent} bold]{title}[/{palette.accent} bold]")
        console.print(f"  [{palette.border}]{divider}[/{palette.border}]")

        if criteria.ingredient_names:
            names = ", ".join(criteria.ingredient_names)
            console.print(
                f"  [{palette.muted}]{t('wizard_review_ingredients', lang):<14}[/{palette.muted}] [{palette.text}]{names}[/{palette.text}]"
            )

        for metric in NUTRIENT_METRICS:
            val = getattr(criteria, metric.attribute_name, None)
            if val is not None:
                display_val = f"{val:g}" if isinstance(val, (int, float)) else str(val)
                label = t(metric.label_key, lang)
                summary_val = f"{metric.target_type} {display_val} {metric.unit}"
                console.print(
                    f"  [{palette.muted}]{label:<14}[/{palette.muted}] [{palette.info}]{summary_val}[/{palette.info}]"
                )

        cat_display = criteria.category_name or t("wizard_category_any", lang)
        console.print(
            f"  [{palette.muted}]{t('wizard_review_category', lang):<14}[/{palette.muted}] [{palette.text}]{cat_display}[/{palette.text}]"
        )

        console.print(f"  [{palette.border}]{divider}[/{palette.border}]")

        if validation_error:
            console.print(f"  [{palette.error}]{validation_error}[/{palette.error}]")
            console.print()

        for idx, label in enumerate(actions):
            if idx == selected_option_index:
                console.print(
                    f"    [{palette.accent} bold]{box.pointer} {label}[/{palette.accent} bold]"
                )
            else:
                console.print(f"      [{palette.text}]{label}[/{palette.text}]")

        console.print()
        console.print(f"  [{palette.muted}]{nav_hint}[/{palette.muted}]")

    return capture.get()


class _WizardSession:
    """Manages interactive state and key handling across wizard steps."""

    def __init__(
        self,
        cache: IngredientCache,
        categories: list[CategoryResponse],
        criteria: SearchCriteria,
        lang: str = "en",
        width: int | None = None,
    ) -> None:
        self.cache = cache
        self.categories = categories
        self.criteria = criteria
        self.lang = lang
        self.width = width

        self.current_step = "ingredients"

        # Step 1
        self.step1_query = ""
        self.step1_suggestions: list[str] = cache.suggest("", limit=8)
        self.step1_selected_suggestion = 0
        self.step1_no_match = False

        # Step 2
        self.step2_selected_metric_idx = 0
        self.step2_checked_metrics: set[str] = {
            m.key for m in NUTRIENT_METRICS if getattr(criteria, m.attribute_name, None) is not None
        }
        self.step2_input_metrics: list[NutrientMetric] = []
        self.step2_active_input_idx = 0
        self.step2_input_str = ""
        self.step2_error_msg = ""

        # Step 3
        self.step3_selected_idx = 0
        if criteria.category_id is not None:
            for c_idx, cat in enumerate(categories):
                if cat.category_id == criteria.category_id:
                    self.step3_selected_idx = c_idx + 1
                    break

        # Review
        self.review_selected_idx = 0
        self.review_validation_error = ""
        self.finished_action = "cancel"

    def on_escape(self, app: Application[None]) -> None:
        """Handle Esc key press."""
        if self.current_step == "ingredients":
            self.finished_action = "cancel"
            app.exit()
        elif self.current_step in ("nutrition_input", "category"):
            self.current_step = "nutrition_select"
            app.invalidate()
        elif self.current_step == "nutrition_select":
            self.current_step = "ingredients"
            app.invalidate()
        elif self.current_step == "review":
            self.current_step = "category"
            app.invalidate()

    def on_up(self, app: Application[None]) -> None:
        """Handle Up arrow navigation."""
        if self.current_step == "ingredients":
            if self.step1_suggestions:
                self.step1_selected_suggestion = (self.step1_selected_suggestion - 1) % len(
                    self.step1_suggestions
                )
        elif self.current_step == "nutrition_select":
            self.step2_selected_metric_idx = (self.step2_selected_metric_idx - 1) % len(
                NUTRIENT_METRICS
            )
        elif self.current_step == "category":
            total_cats = len(self.categories) + 1
            self.step3_selected_idx = (self.step3_selected_idx - 1) % total_cats
        elif self.current_step == "review":
            self.review_selected_idx = (self.review_selected_idx - 1) % len(REVIEW_ACTIONS)
        app.invalidate()

    def on_down(self, app: Application[None]) -> None:
        """Handle Down arrow navigation."""
        if self.current_step == "ingredients":
            if self.step1_suggestions:
                self.step1_selected_suggestion = (self.step1_selected_suggestion + 1) % len(
                    self.step1_suggestions
                )
        elif self.current_step == "nutrition_select":
            self.step2_selected_metric_idx = (self.step2_selected_metric_idx + 1) % len(
                NUTRIENT_METRICS
            )
        elif self.current_step == "category":
            total_cats = len(self.categories) + 1
            self.step3_selected_idx = (self.step3_selected_idx + 1) % total_cats
        elif self.current_step == "review":
            self.review_selected_idx = (self.review_selected_idx + 1) % len(REVIEW_ACTIONS)
        app.invalidate()

    def on_space(self, app: Application[None]) -> None:
        """Handle Space toggle or character input."""
        if self.current_step == "nutrition_select":
            metric_key = NUTRIENT_METRICS[self.step2_selected_metric_idx].key
            if metric_key in self.step2_checked_metrics:
                self.step2_checked_metrics.remove(metric_key)
            else:
                self.step2_checked_metrics.add(metric_key)
        elif self.current_step == "ingredients":
            self.step1_query += " "
            self.step1_suggestions = self.cache.suggest(self.step1_query, limit=8)
            self.step1_no_match = len(self.step1_suggestions) == 0 and bool(
                self.step1_query.strip()
            )
            if self.step1_no_match:
                track("invalid_input", {"step": "ingredients", "field": "ingredients"})
        app.invalidate()

    def on_backspace(self, app: Application[None]) -> None:
        """Handle Backspace character or chip deletion."""
        if self.current_step == "ingredients":
            if self.step1_query:
                self.step1_query = self.step1_query[:-1]
                self.step1_suggestions = self.cache.suggest(self.step1_query, limit=8)
                self.step1_no_match = len(self.step1_suggestions) == 0 and bool(
                    self.step1_query.strip()
                )
            elif self.criteria.ingredient_names:
                self.criteria.ingredient_names.pop()
                if self.criteria.ingredient_ids:
                    self.criteria.ingredient_ids.pop()
        elif self.current_step == "nutrition_input" and self.step2_input_str:
            self.step2_input_str = self.step2_input_str[:-1]
        app.invalidate()

    def on_tab(self, app: Application[None]) -> None:
        """Handle Tab completion for ingredients."""
        if self.current_step == "ingredients" and self.step1_suggestions:
            chosen = self.step1_suggestions[self.step1_selected_suggestion]
            if chosen not in self.criteria.ingredient_names:
                self.criteria.ingredient_names.append(chosen)
                ing_id = self.cache.get_id(chosen)
                if ing_id is not None:
                    self.criteria.ingredient_ids.append(ing_id)
            self.step1_query = ""
            self.step1_suggestions = self.cache.suggest("", limit=8)
            self.step1_selected_suggestion = 0
            self.step1_no_match = False
        app.invalidate()

    def on_enter(self, app: Application[None]) -> None:
        """Handle Enter key advance or selection."""
        if self.current_step == "ingredients":
            if self.step1_query.strip() and self.step1_suggestions:
                chosen = self.step1_suggestions[self.step1_selected_suggestion]
                if chosen not in self.criteria.ingredient_names:
                    self.criteria.ingredient_names.append(chosen)
                    ing_id = self.cache.get_id(chosen)
                    if ing_id is not None:
                        self.criteria.ingredient_ids.append(ing_id)
                self.step1_query = ""
                self.step1_suggestions = self.cache.suggest("", limit=8)
                self.step1_selected_suggestion = 0
                self.step1_no_match = False
            elif not self.step1_query.strip():
                self.current_step = "nutrition_select"

        elif self.current_step == "nutrition_select":
            self.step2_input_metrics = [
                m for m in NUTRIENT_METRICS if m.key in self.step2_checked_metrics
            ]
            if self.step2_input_metrics:
                self.step2_active_input_idx = 0
                metric = self.step2_input_metrics[0]
                curr_val = getattr(self.criteria, metric.attribute_name, None)
                self.step2_input_str = f"{curr_val:g}" if curr_val is not None else ""
                self.step2_error_msg = ""
                self.current_step = "nutrition_input"
            else:
                for m in NUTRIENT_METRICS:
                    setattr(self.criteria, m.attribute_name, None)
                self.current_step = "category"

        elif self.current_step == "nutrition_input":
            active_metric = self.step2_input_metrics[self.step2_active_input_idx]
            val_text = self.step2_input_str.strip()
            proceed = True
            if not val_text:
                setattr(self.criteria, active_metric.attribute_name, None)
            else:
                try:
                    num_val = float(val_text)
                    if num_val < 0:
                        self.step2_error_msg = t("wizard_invalid_number", self.lang)
                        track("invalid_input", {"step": "nutrition", "field": active_metric.key})
                        proceed = False
                    else:
                        setattr(self.criteria, active_metric.attribute_name, num_val)
                except ValueError:
                    self.step2_error_msg = t("wizard_invalid_number", self.lang)
                    track("invalid_input", {"step": "nutrition", "field": active_metric.key})
                    proceed = False

            if proceed:
                self.step2_active_input_idx += 1
                if self.step2_active_input_idx < len(self.step2_input_metrics):
                    next_metric = self.step2_input_metrics[self.step2_active_input_idx]
                    curr_val = getattr(self.criteria, next_metric.attribute_name, None)
                    self.step2_input_str = f"{curr_val:g}" if curr_val is not None else ""
                    self.step2_error_msg = ""
                else:
                    self.current_step = "category"

        elif self.current_step == "category":
            if self.step3_selected_idx == 0:
                self.criteria.category_id = None
                self.criteria.category_name = None
            else:
                cat = self.categories[self.step3_selected_idx - 1]
                self.criteria.category_id = cat.category_id
                self.criteria.category_name = cat.name
            self.current_step = "review"

        elif self.current_step == "review":
            chosen_opt = REVIEW_ACTIONS[self.review_selected_idx]
            if chosen_opt == "search":
                if not self.criteria.has_any_filter():
                    self.review_validation_error = t("wizard_error_at_least_one", self.lang)
                else:
                    self.finished_action = "search"
                    app.exit()
            elif chosen_opt == "edit":
                self.current_step = "ingredients"
            elif chosen_opt == "cancel":
                self.finished_action = "cancel"
                app.exit()

        app.invalidate()

    def on_char(self, char: str, app: Application[None]) -> None:
        """Handle character typing."""
        if self.current_step == "ingredients" and char.isprintable():
            self.step1_query += char
            self.step1_suggestions = self.cache.suggest(self.step1_query, limit=8)
            self.step1_selected_suggestion = 0
            self.step1_no_match = len(self.step1_suggestions) == 0 and bool(
                self.step1_query.strip()
            )
            if self.step1_no_match:
                track("invalid_input", {"step": "ingredients", "field": "ingredients"})
        elif self.current_step == "nutrition_input" and (char.isdigit() or char == "."):
            self.step2_input_str += char
        app.invalidate()

    def get_content(self) -> ANSI:
        """Render the current step screen to ANSI FormattedText."""
        cw = self.width or get_content_width()
        if self.current_step == "ingredients":
            return ANSI(
                render_wizard_step1(
                    chips=self.criteria.ingredient_names,
                    query=self.step1_query,
                    suggestions=self.step1_suggestions,
                    selected_suggestion_index=self.step1_selected_suggestion,
                    no_match=self.step1_no_match,
                    lang=self.lang,
                    width=cw,
                )
            )
        if self.current_step == "nutrition_select":
            return ANSI(
                render_wizard_step2_select(
                    selected_index=self.step2_selected_metric_idx,
                    checked_keys=self.step2_checked_metrics,
                    lang=self.lang,
                    width=cw,
                )
            )
        if self.current_step == "nutrition_input":
            active_metric = self.step2_input_metrics[self.step2_active_input_idx]
            return ANSI(
                render_wizard_step2_input(
                    metric=active_metric,
                    input_value=self.step2_input_str,
                    error_message=self.step2_error_msg,
                    lang=self.lang,
                    width=cw,
                )
            )
        if self.current_step == "category":
            return ANSI(
                render_wizard_step3_category(
                    categories=self.categories,
                    selected_index=self.step3_selected_idx,
                    lang=self.lang,
                    width=cw,
                )
            )
        if self.current_step == "review":
            return ANSI(
                render_wizard_review(
                    criteria=self.criteria,
                    selected_option_index=self.review_selected_idx,
                    validation_error=self.review_validation_error,
                    lang=self.lang,
                    width=cw,
                )
            )
        return ANSI("")

    def run(self) -> str:
        """Run the interactive wizard application."""
        kb = KeyBindings()

        @kb.add("c-c")
        def _(event):
            event.app.exit(exception=KeyboardInterrupt())

        @kb.add("escape")
        def _(event):
            self.on_escape(event.app)

        @kb.add("up")
        @kb.add("k")
        def _(event):
            self.on_up(event.app)

        @kb.add("down")
        @kb.add("j")
        def _(event):
            self.on_down(event.app)

        @kb.add("space")
        def _(event):
            self.on_space(event.app)

        @kb.add("backspace")
        def _(event):
            self.on_backspace(event.app)

        @kb.add("tab")
        def _(event):
            self.on_tab(event.app)

        @kb.add("enter")
        def _(event):
            self.on_enter(event.app)

        @kb.add("<any>")
        def _(event):
            self.on_char(event.data, event.app)

        app: Application[None] = Application(
            layout=Layout(Window(FormattedTextControl(self.get_content))),
            key_bindings=kb,
            full_screen=False,
            output=get_pt_output(),
            input=get_pt_input(),
        )
        app.run()
        return self.finished_action


def show_search_wizard(
    client: ApiClient,
    lang: str = "en",
    width: int | None = None,
    criteria: SearchCriteria | None = None,
    cache: IngredientCache | None = None,
) -> tuple[str, SearchCriteria, list[int]]:
    """Interactive search wizard coordinator.

    Returns:
        tuple of (action, criteria, recipe_ids) where action is 'results', 'main_menu', or 'cancel'.
    """
    if not is_interactive():
        return "cancel", criteria or SearchCriteria(), []

    criteria = criteria or SearchCriteria()

    if cache is None:
        try:
            cache = load_ingredient_cache(client, lang)
        except Exception:
            cache = IngredientCache([])

    try:
        categories = client.get_categories(lang=lang)
    except Exception:
        categories = []

    while True:
        session = _WizardSession(
            cache=cache,
            categories=categories,
            criteria=criteria,
            lang=lang,
            width=width,
        )
        finished_action = session.run()

        if finished_action == "cancel":
            return "cancel", criteria, []

        if finished_action == "search":
            track(
                "search_executed",
                {
                    "has_ingredients": bool(criteria.ingredient_ids),
                    "ingredient_count": len(criteria.ingredient_ids),
                    "has_category": criteria.category_id is not None,
                },
            )
            try:
                search_req = criteria.to_search_request(lang=lang)
                response = client.search(search_req)
                if not response.recipe_ids:
                    track("no_results", {"lang": lang})
                    from recipe_finder.screens.notices import show_no_results_screen

                    choice = show_no_results_screen(lang=lang, width=width)
                    if choice == "wizard":
                        continue
                    return "main_menu", criteria, []
                return "results", criteria, response.recipe_ids
            except ApiClientError as exc:
                track("error", {"error_code": exc.error_code or "search_failed"})
                from recipe_finder.screens.notices import show_error_screen

                choice = show_error_screen(message=exc.message, lang=lang, width=width)
                if choice == "retry":
                    continue
                return "main_menu", criteria, []
