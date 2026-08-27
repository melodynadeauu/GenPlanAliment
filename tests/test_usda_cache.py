"""Tests for data.usda.cache: SQLite-backed cache for USDA FoodData Central responses."""
import pytest

from data.usda import cache as usda_cache


@pytest.fixture(autouse=True)
def isolated_db_path(tmp_path, monkeypatch):
    """Redirect DB_PATH to a throwaway file so tests never touch the real cache."""
    monkeypatch.setattr(usda_cache, "DB_PATH", tmp_path / "usda_cache.db")


# --- search cache ---


def test_get_cached_search_returns_none_when_absent():
    assert usda_cache.get_cached_search("apple") is None


def test_set_then_get_cached_search_round_trips():
    usda_cache.set_cached_search("apple", [{"fdc_id": 1, "description": "Apple, raw"}])

    assert usda_cache.get_cached_search("apple") == [{"fdc_id": 1, "description": "Apple, raw"}]


def test_get_cached_search_normalizes_query_case_and_whitespace():
    usda_cache.set_cached_search("  Apple  ", [{"fdc_id": 1, "description": "Apple, raw"}])

    assert usda_cache.get_cached_search("apple") == [{"fdc_id": 1, "description": "Apple, raw"}]
    assert usda_cache.get_cached_search("APPLE") == [{"fdc_id": 1, "description": "Apple, raw"}]


def test_set_cached_search_can_cache_an_empty_result_distinctly_from_absent():
    usda_cache.set_cached_search("zzz_nonexistent", [])

    assert usda_cache.get_cached_search("zzz_nonexistent") == []
    assert usda_cache.get_cached_search("never_queried") is None


def test_set_cached_search_overwrites_previous_value_for_the_same_query():
    usda_cache.set_cached_search("apple", [{"fdc_id": 1, "description": "Apple, raw"}])
    usda_cache.set_cached_search("apple", [{"fdc_id": 2, "description": "Apple, updated"}])

    assert usda_cache.get_cached_search("apple") == [{"fdc_id": 2, "description": "Apple, updated"}]


# --- nutrition cache ---

APPLE_FOOD = {
    "fdc_id": 1,
    "description": "Apple, raw",
    "macros_per_100g": {"kcal": 52.0, "protein_g": 0.3, "fat_g": 0.2, "carbs_g": 14.0},
}


def test_get_cached_nutrition_returns_none_when_absent():
    assert usda_cache.get_cached_nutrition("12345") is None


def test_set_found_then_get_cached_nutrition_round_trips():
    usda_cache.set_cached_nutrition_found("1", APPLE_FOOD)

    assert usda_cache.get_cached_nutrition("1") == {"found": True, "food": APPLE_FOOD}


def test_set_not_found_then_get_cached_nutrition_reports_not_found():
    usda_cache.set_cached_nutrition_not_found("999")

    assert usda_cache.get_cached_nutrition("999") == {"found": False}


def test_set_cached_nutrition_found_overwrites_a_previously_cached_not_found():
    """A re-fetch must replace the stale row, not add a second one."""
    usda_cache.set_cached_nutrition_not_found("1")
    usda_cache.set_cached_nutrition_found("1", APPLE_FOOD)

    assert usda_cache.get_cached_nutrition("1") == {"found": True, "food": APPLE_FOOD}
