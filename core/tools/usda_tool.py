"""LLM-facing tools wrapping data.usda.client.

Two @tool-decorated functions, each a plain single-purpose call the LLM can make
directly. Neither raises: on failure they return {"error": <code>}, one of
data.usda.client's four error codes.

@tool turns a function into a StructuredTool -- it's no longer a plain callable, so
call it through .invoke({...}), not directly (see core.agent.plan_view).
"""
from langchain_core.tools import tool

from data.usda import client as usda_client


@tool
def search_food_tool(query: str) -> dict:
    """Search USDA foods for `query`.
    Success: {"results": [{"fdc_id", "description"}, ...]}. Failure: {"error": <code>}.
    """
    result = usda_client.search_food(query, usda_client.USDA_API_KEY)
    if result.error is not None:
        return {"error": result.error}
    return {"results": result.food}


@tool
def get_nutrition_tool(fdc_id: str) -> dict:
    """Look up nutrition for `fdc_id`.
    Success: {"fdc_id", "description", "macros_per_100g"}. Failure: {"error": <code>}.
    """
    result = usda_client.get_nutrition(fdc_id, usda_client.USDA_API_KEY)
    if result.error is not None:
        return {"error": result.error}
    assert isinstance(result.food, dict)
    return result.food
