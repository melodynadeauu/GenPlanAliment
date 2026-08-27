"""Tests for core.tools.usda_tool: LLM-facing @tool wrappers around data.usda.client.

data.usda.client.search_food/get_nutrition are monkeypatched directly; retry/caching
behavior is covered in tests/test_usda_client*.
"""
import pytest

from core.tools import usda_tool
from data.usda import client as usda_client

ERROR_CODES = ["not_found", "rate_limited", "timeout", "api_error"]


# --- wiring: these are real LangChain tools, not plain functions ---


def test_search_food_tool_is_a_structured_tool_named_after_the_function():
    assert usda_tool.search_food_tool.name == "search_food_tool"
    assert "Search USDA foods" in usda_tool.search_food_tool.description


def test_get_nutrition_tool_is_a_structured_tool_named_after_the_function():
    assert usda_tool.get_nutrition_tool.name == "get_nutrition_tool"
    assert "Look up nutrition" in usda_tool.get_nutrition_tool.description


def test_a_structured_tool_is_no_longer_directly_callable():
    """@tool makes it a StructuredTool; callers must use .invoke({...})."""
    with pytest.raises(TypeError):
        usda_tool.search_food_tool("apple")


# --- search_food_tool ---


def test_search_food_tool_returns_results_on_success(monkeypatch):
    monkeypatch.setattr(
        usda_client,
        "search_food",
        lambda query, api_key: usda_client.FoodLookupResult(
            [{"fdc_id": 123, "description": "Apple, raw"}], None
        ),
    )

    result = usda_tool.search_food_tool.invoke({"query": "apple"})

    assert result == {"results": [{"fdc_id": 123, "description": "Apple, raw"}]}


def test_search_food_tool_passes_query_and_module_api_key(monkeypatch):
    calls = []
    monkeypatch.setattr(
        usda_client,
        "search_food",
        lambda query, api_key: calls.append((query, api_key)) or usda_client.FoodLookupResult([], None),
    )

    usda_tool.search_food_tool.invoke({"query": "banana"})

    assert calls == [("banana", usda_client.USDA_API_KEY)]


@pytest.mark.parametrize("error_code", ERROR_CODES)
def test_search_food_tool_returns_error_dict_never_raises(monkeypatch, error_code):
    monkeypatch.setattr(
        usda_client,
        "search_food",
        lambda query, api_key: usda_client.FoodLookupResult(None, error_code),
    )

    result = usda_tool.search_food_tool.invoke({"query": "zzz_nonexistent"})

    assert result == {"error": error_code}


# --- get_nutrition_tool ---


CHICKEN_GRAVY_FOOD = {
    "fdc_id": 2620254,
    "description": "CHICKEN GRAVY, CHICKEN",
    "macros_per_100g": {"kcal": 65.0, "protein_g": 1.61, "fat_g": 4.03, "carbs_g": 4.84},
}


def test_get_nutrition_tool_passes_through_the_client_food_dict_unchanged(monkeypatch):
    """get_nutrition_tool is a passthrough, not a transform."""
    monkeypatch.setattr(
        usda_client,
        "get_nutrition",
        lambda fdc_id, api_key: usda_client.FoodLookupResult(CHICKEN_GRAVY_FOOD, None),
    )

    result = usda_tool.get_nutrition_tool.invoke({"fdc_id": "2620254"})

    assert result == CHICKEN_GRAVY_FOOD


def test_get_nutrition_tool_passes_fdc_id_and_module_api_key(monkeypatch):
    calls = []
    monkeypatch.setattr(
        usda_client,
        "get_nutrition",
        lambda fdc_id, api_key: calls.append((fdc_id, api_key))
        or usda_client.FoodLookupResult(CHICKEN_GRAVY_FOOD, None),
    )

    usda_tool.get_nutrition_tool.invoke({"fdc_id": "2620254"})

    assert calls == [("2620254", usda_client.USDA_API_KEY)]


@pytest.mark.parametrize("error_code", ERROR_CODES)
def test_get_nutrition_tool_returns_error_dict_never_raises(monkeypatch, error_code):
    monkeypatch.setattr(
        usda_client,
        "get_nutrition",
        lambda fdc_id, api_key: usda_client.FoodLookupResult(None, error_code),
    )

    result = usda_tool.get_nutrition_tool.invoke({"fdc_id": "1"})

    assert result == {"error": error_code}
