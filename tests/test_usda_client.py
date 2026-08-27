"""Tests for data.usda.client happy paths and caching. All requests.get calls are faked."""
import dataclasses

import pytest

from data.usda import cache as usda_cache
from data.usda import client as usda_client


@pytest.fixture(autouse=True)
def isolated_db_path(tmp_path, monkeypatch):
    """Redirect DB_PATH to a throwaway file so tests never touch the real cache."""
    monkeypatch.setattr(usda_cache, "DB_PATH", tmp_path / "usda_cache.db")


class FakeResponse:
    def __init__(self, json_data=None, status_code=200, headers=None):
        self._json_data = json_data
        self.status_code = status_code
        self.headers = headers or {}

    def json(self):
        return self._json_data


def make_fake_get(json_data, calls, status_code=200):
    """Return a fake requests.get that records each call and replays `json_data`."""

    def fake_get(url, params=None, timeout=None):
        calls.append({"url": url, "params": params, "timeout": timeout})
        return FakeResponse(json_data, status_code=status_code)

    return fake_get


# --- FoodLookupResult ---


def test_food_lookup_result_is_frozen():
    result = usda_client.FoodLookupResult(food={"a": 1}, error=None)
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.error = "not_found"


# --- search_food ---


def test_search_food_returns_results_and_caches_them(monkeypatch):
    calls = []
    api_response = {
        "foods": [
            {"fdcId": 123456, "description": "Apple, raw"},
            {"fdcId": 789012, "description": "Apple juice"},
        ]
    }
    monkeypatch.setattr(usda_client.requests, "get", make_fake_get(api_response, calls))

    result = usda_client.search_food("apple", "FAKE_KEY")

    assert result.error is None
    assert result.food == [
        {"fdc_id": 123456, "description": "Apple, raw"},
        {"fdc_id": 789012, "description": "Apple juice"},
    ]
    assert len(calls) == 1
    assert calls[0]["url"] == "https://api.nal.usda.gov/fdc/v1/foods/search"
    assert calls[0]["params"] == {"query": "apple", "api_key": "FAKE_KEY"}
    assert calls[0]["timeout"] == 5

    assert usda_cache.get_cached_search("apple") == result.food


def test_search_food_returns_not_found_when_no_results(monkeypatch):
    calls = []
    monkeypatch.setattr(usda_client.requests, "get", make_fake_get({"foods": []}, calls))

    result = usda_client.search_food("zzz_nonexistent", "FAKE_KEY")

    assert result == usda_client.FoodLookupResult(None, "not_found")


def test_search_food_uses_cache_on_second_call(monkeypatch):
    calls = []
    api_response = {"foods": [{"fdcId": 1, "description": "Apple"}]}
    monkeypatch.setattr(usda_client.requests, "get", make_fake_get(api_response, calls))

    usda_client.search_food("apple", "FAKE_KEY")
    usda_client.search_food("  Apple  ", "FAKE_KEY")

    assert len(calls) == 1


def test_search_food_caches_not_found_so_second_call_skips_network(monkeypatch):
    calls = []
    monkeypatch.setattr(usda_client.requests, "get", make_fake_get({"foods": []}, calls))

    usda_client.search_food("zzz_nonexistent", "FAKE_KEY")
    result = usda_client.search_food("zzz_nonexistent", "FAKE_KEY")

    assert len(calls) == 1
    assert result == usda_client.FoodLookupResult(None, "not_found")


# --- get_nutrition ---

# Real /food/2620254-shaped response, trimmed to the fields client.py reads. foodNutrients
# carries far more than the four macros (sodium, cholesterol, vitamins, ...) -- only
# kcal/protein/fat/carbs are extracted and cached, see data.usda.nutrients.MACRO_FIELDS.
FOOD_DETAIL_EXAMPLE = {
    "dataType": "Branded",
    "description": "NUT 'N BERRY MIX",
    "fdcId": 534358,
    "foodNutrients": [
        {"nutrient": {"number": "208", "name": "Energy"}, "amount": 65.0},
        {"nutrient": {"number": "203", "name": "Protein"}, "amount": 1.61},
        {"nutrient": {"number": "204", "name": "Total lipid (fat)"}, "amount": 4.03},
        {"nutrient": {"number": "205", "name": "Carbohydrate, by difference"}, "amount": 4.84},
        {"nutrient": {"number": "303", "name": "Iron, Fe"}, "amount": 0.53},
    ],
}

EXPECTED_FOOD = {
    "fdc_id": 534358,
    "description": "NUT 'N BERRY MIX",
    "macros_per_100g": {"kcal": 65.0, "protein_g": 1.61, "fat_g": 4.03, "carbs_g": 4.84},
}


def test_get_nutrition_returns_and_caches_only_the_four_extracted_macros(monkeypatch):
    """Iron (and everything else in foodNutrients besides the four macros) is dropped --
    it's never read anywhere downstream, and keeping it was the old cache's main source
    of bloat (3.4MB for 48 entries)."""
    calls = []
    monkeypatch.setattr(usda_client.requests, "get", make_fake_get(FOOD_DETAIL_EXAMPLE, calls))

    result = usda_client.get_nutrition("534358", "FAKE_KEY")

    assert result.error is None
    assert result.food == EXPECTED_FOOD
    assert len(calls) == 1
    assert calls[0]["url"] == "https://api.nal.usda.gov/fdc/v1/food/534358"
    assert calls[0]["params"] == {"api_key": "FAKE_KEY"}
    assert calls[0]["timeout"] == 5

    assert usda_cache.get_cached_nutrition("534358") == {"found": True, "food": EXPECTED_FOOD}


def test_get_nutrition_uses_cache_on_second_call(monkeypatch):
    calls = []
    monkeypatch.setattr(usda_client.requests, "get", make_fake_get(FOOD_DETAIL_EXAMPLE, calls))

    usda_client.get_nutrition("534358", "FAKE_KEY")
    usda_client.get_nutrition("534358", "FAKE_KEY")

    assert len(calls) == 1


def test_get_nutrition_returns_not_found_when_no_nutrients(monkeypatch):
    calls = []
    monkeypatch.setattr(
        usda_client.requests,
        "get",
        make_fake_get({"fdcId": 1, "description": "Empty", "foodNutrients": []}, calls),
    )

    result = usda_client.get_nutrition("1", "FAKE_KEY")

    assert result == usda_client.FoodLookupResult(None, "not_found")


def test_get_nutrition_caches_not_found_so_second_call_skips_network(monkeypatch):
    calls = []
    monkeypatch.setattr(
        usda_client.requests,
        "get",
        make_fake_get({"fdcId": 1, "description": "Empty", "foodNutrients": []}, calls),
    )

    usda_client.get_nutrition("1", "FAKE_KEY")
    result = usda_client.get_nutrition("1", "FAKE_KEY")

    assert len(calls) == 1
    assert result == usda_client.FoodLookupResult(None, "not_found")


def test_get_nutrition_backfills_a_row_cached_before_a_macro_field_existed(monkeypatch):
    """A row cached by an older version of data.usda.nutrients.MACRO_FIELDS (missing a
    field extract_macros now extracts) must not be trusted as-is -- one live call
    refreshes it with the full current set of macros, then the cache is fresh again."""
    calls = []
    monkeypatch.setattr(usda_client.requests, "get", make_fake_get(FOOD_DETAIL_EXAMPLE, calls))
    stale_food = {
        "fdc_id": 534358,
        "description": "NUT 'N BERRY MIX",
        "macros_per_100g": {"kcal": 65.0, "protein_g": 1.61, "fat_g": 4.03},  # carbs_g missing
    }
    usda_cache.set_cached_nutrition_found("534358", stale_food)

    result = usda_client.get_nutrition("534358", "FAKE_KEY")

    assert len(calls) == 1  # backfilled live, not trusted as cached
    assert result.food == EXPECTED_FOOD
    assert usda_cache.get_cached_nutrition("534358") == {"found": True, "food": EXPECTED_FOOD}


def test_get_nutrition_refetches_a_cached_zero_kcal_row_when_other_macros_are_nonzero(monkeypatch):
    """A row cached by the old extract_macros (only read nutrient "208") has kcal == 0.0
    for a food that actually has energy, just reported under a field it didn't know about
    yet. Non-zero protein/fat/carbs alongside kcal == 0.0 is the tell -- refetch live once
    so the cache self-heals instead of quietly keeping the wrong 0."""
    calls = []
    monkeypatch.setattr(usda_client.requests, "get", make_fake_get(FOOD_DETAIL_EXAMPLE, calls))
    stale_food = {
        "fdc_id": 534358,
        "description": "NUT 'N BERRY MIX",
        "macros_per_100g": {"kcal": 0.0, "protein_g": 1.61, "fat_g": 4.03, "carbs_g": 4.84},
    }
    usda_cache.set_cached_nutrition_found("534358", stale_food)

    result = usda_client.get_nutrition("534358", "FAKE_KEY")

    assert len(calls) == 1  # refetched live, not trusted as cached
    assert result.food == EXPECTED_FOOD
    assert usda_cache.get_cached_nutrition("534358") == {"found": True, "food": EXPECTED_FOOD}


def test_get_nutrition_trusts_a_cached_row_with_genuinely_zero_kcal_and_zero_other_macros(monkeypatch):
    """A food with kcal == 0.0 AND all other macros == 0.0 (e.g. water) is plausibly
    correct, not stale -- must not trigger a refetch."""
    calls = []
    monkeypatch.setattr(usda_client.requests, "get", make_fake_get(FOOD_DETAIL_EXAMPLE, calls))
    water_food = {
        "fdc_id": 999,
        "description": "Water",
        "macros_per_100g": {"kcal": 0.0, "protein_g": 0.0, "fat_g": 0.0, "carbs_g": 0.0},
    }
    usda_cache.set_cached_nutrition_found("999", water_food)

    result = usda_client.get_nutrition("999", "FAKE_KEY")

    assert len(calls) == 0
    assert result.food == water_food
