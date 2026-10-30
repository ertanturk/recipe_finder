"""Tests for recipe_finder.state SearchCriteria and ResultQueue."""

from recipe_finder.state import ResultQueue, SearchCriteria


def test_search_criteria_empty() -> None:
    criteria = SearchCriteria()
    assert criteria.has_any_filter() is False
    req = criteria.to_search_request(lang="en")
    assert req.ingredient_ids == []
    assert req.max_calorie is None
    assert req.category_id is None


def test_search_criteria_with_filters() -> None:
    criteria = SearchCriteria(
        ingredient_names=["chicken breast"],
        ingredient_ids=[12],
        max_calorie=500.0,
        min_protein=30.0,
        category_id=2,
        category_name="Dinner",
    )
    assert criteria.has_any_filter() is True
    req = criteria.to_search_request(lang="tr")
    assert req.lang == "tr"
    assert req.ingredient_ids == [12]
    assert req.max_calorie == 500.0
    assert req.min_protein == 30.0
    assert req.category_id == 2


def test_search_criteria_clear() -> None:
    criteria = SearchCriteria(
        ingredient_names=["rice"],
        ingredient_ids=[5],
        min_fat=10.0,
        category_id=1,
    )
    assert criteria.has_any_filter() is True
    criteria.clear()
    assert criteria.has_any_filter() is False
    assert criteria.ingredient_names == []
    assert criteria.ingredient_ids == []
    assert criteria.min_fat is None
    assert criteria.category_id is None


def test_result_queue_navigation() -> None:
    queue = ResultQueue(recipe_ids=[101, 102, 103])
    assert queue.total == 3
    assert queue.position == 1
    assert queue.current_id == 101
    assert queue.has_previous() is False
    assert queue.has_next() is True

    next_id = queue.next()
    assert next_id == 102
    assert queue.position == 2
    assert queue.has_previous() is True
    assert queue.has_next() is True

    next_id = queue.next()
    assert next_id == 103
    assert queue.position == 3
    assert queue.has_next() is False

    assert queue.next() is None
    assert queue.current_id == 103

    prev_id = queue.previous()
    assert prev_id == 102
    assert queue.position == 2

    prev_id = queue.previous()
    assert prev_id == 101
    assert queue.position == 1
    assert queue.previous() is None


def test_result_queue_marks_each_recipe_skipped_once() -> None:
    queue = ResultQueue(recipe_ids=[101, 102])

    assert queue.mark_skipped() is True
    assert queue.mark_skipped() is False
    queue.next()
    assert queue.mark_skipped() is True
    queue.previous()
    assert queue.mark_skipped() is False
