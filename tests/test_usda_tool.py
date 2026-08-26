"""Tests for core.tools.usda_tool: LLM-facing wrappers around data.usda.client.

data.usda.client.search_food / get_nutrition are monkeypatched directly (not
requests.get) -- these tests only check the tool's own wrapping, not the
client's retry/caching behaviour, which is covered in tests/test_usda_client*.
"""
import pytest

from core.tools import usda_tool
from data.usda import client as usda_client

ERROR_CODES = ["not_found", "rate_limited", "timeout", "api_error"]


# --- search_food_tool ---


def test_search_food_tool_returns_results_on_success(monkeypatch):
    monkeypatch.setattr(
        usda_client,
        "search_food",
        lambda query, api_key: usda_client.FoodLookupResult(
            [{"fdc_id": 123, "description": "Apple, raw"}], None
        ),
    )

    result = usda_tool.search_food_tool("apple")

    assert result == {"results": [{"fdc_id": 123, "description": "Apple, raw"}]}


def test_search_food_tool_passes_query_and_module_api_key(monkeypatch):
    calls = []
    monkeypatch.setattr(
        usda_client,
        "search_food",
        lambda query, api_key: calls.append((query, api_key)) or usda_client.FoodLookupResult([], None),
    )

    usda_tool.search_food_tool("banana")

    assert calls == [("banana", usda_client.USDA_API_KEY)]


@pytest.mark.parametrize("error_code", ERROR_CODES)
def test_search_food_tool_returns_error_dict_never_raises(monkeypatch, error_code):
    monkeypatch.setattr(
        usda_client,
        "search_food",
        lambda query, api_key: usda_client.FoodLookupResult(None, error_code),
    )

    result = usda_tool.search_food_tool("zzz_nonexistent")

    assert result == {"error": error_code}


# --- get_nutrition_tool ---


CHICKEN_GRAVY_FOOD = {
    "fdc_id": 2620254,
    "description": "CHICKEN GRAVY, CHICKEN",
    "macros_per_100g": {"kcal": 65.0, "protein_g": 1.61, "fat_g": 4.03, "carbs_g": 4.84},
}


def test_get_nutrition_tool_passes_through_the_client_food_dict_unchanged(monkeypatch):
    """client.get_nutrition already extracts/caches only the four macros (see
    data.usda.nutrients) -- get_nutrition_tool is a passthrough, not a transform."""
    monkeypatch.setattr(
        usda_client,
        "get_nutrition",
        lambda fdc_id, api_key: usda_client.FoodLookupResult(CHICKEN_GRAVY_FOOD, None),
    )

    result = usda_tool.get_nutrition_tool("2620254")

    assert result == CHICKEN_GRAVY_FOOD


def test_get_nutrition_tool_passes_fdc_id_and_module_api_key(monkeypatch):
    calls = []
    monkeypatch.setattr(
        usda_client,
        "get_nutrition",
        lambda fdc_id, api_key: calls.append((fdc_id, api_key))
        or usda_client.FoodLookupResult(CHICKEN_GRAVY_FOOD, None),
    )

    usda_tool.get_nutrition_tool("2620254")

    assert calls == [("2620254", usda_client.USDA_API_KEY)]


@pytest.mark.parametrize("error_code", ERROR_CODES)
def test_get_nutrition_tool_returns_error_dict_never_raises(monkeypatch, error_code):
    monkeypatch.setattr(
        usda_client,
        "get_nutrition",
        lambda fdc_id, api_key: usda_client.FoodLookupResult(None, error_code),
    )

    result = usda_tool.get_nutrition_tool("1")

    assert result == {"error": error_code}
