"""LLM-facing tools wrapping data.usda.client.

Two distinct tools rather than one generic dispatch with an "action" param,
so each stays a plain, single-purpose function an LLM can call directly.
Neither ever raises: on failure they return {"error": <code>}, one of
data.usda.client's four error codes (not_found, rate_limited, timeout,
api_error).
"""
from core.nutrition.usda_nutrients import extract_macros
from data.usda import client as usda_client


def search_food_tool(query: str) -> dict:
    """Search USDA foods for `query`. Success: {"results": [{"fdc_id", "description"}, ...]}
    (client.py already trims each result to fdc_id + description; passed through as-is).
    Failure: {"error": <code>}.
    """
    result = usda_client.search_food(query, usda_client.USDA_API_KEY)
    if result.error is not None:
        return {"error": result.error}
    return {"results": result.food}


def get_nutrition_tool(fdc_id: str) -> dict:
    """Look up nutrition for `fdc_id`. Success: {"fdc_id", "description",
    "macros_per_100g"} -- the raw foodNutrients list is never returned to the
    LLM, only the extracted macros (see core.nutrition.usda_nutrients).
    Failure: {"error": <code>}.
    """
    result = usda_client.get_nutrition(fdc_id, usda_client.USDA_API_KEY)
    if result.error is not None:
        return {"error": result.error}
    food = result.food
    assert isinstance(food, dict)
    return {
        "fdc_id": food["fdc_id"],
        "description": food["description"],
        "macros_per_100g": extract_macros(food["foodNutrients"]),
    }
