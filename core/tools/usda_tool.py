"""LLM-facing tools wrapping data.usda.client.

Two distinct @tool-decorated functions rather than one generic dispatch with an
"action" param, so each stays a plain, single-purpose function an LLM can call
directly. Neither ever raises: on failure they return {"error": <code>}, one of
data.usda.client's four error codes (not_found, rate_limited, timeout, api_error).

@tool (langchain_core.tools) turns each function into a StructuredTool: its .name,
.description and argument schema are inferred from the function name, docstring and
type hints -- core.agent.graph binds these straight to the LLM, replacing the manual
JSON-schema building core.agent.tool_schema used to do by hand. Because of that, a
StructuredTool is no longer a plain callable -- call through .invoke({...}), not
tool(...) directly. core.agent.plan_view does this for get_nutrition_tool.
"""
from langchain_core.tools import tool

from data.usda import client as usda_client


@tool
def search_food_tool(query: str) -> dict:
    """Search USDA foods for `query`. Success: {"results": [{"fdc_id", "description"}, ...]}
    (client.py already trims each result to fdc_id + description; passed through as-is).
    Failure: {"error": <code>}.
    """
    result = usda_client.search_food(query, usda_client.USDA_API_KEY)
    if result.error is not None:
        return {"error": result.error}
    return {"results": result.food}


@tool
def get_nutrition_tool(fdc_id: str) -> dict:
    """Look up nutrition for `fdc_id`. Success: {"fdc_id", "description",
    "macros_per_100g"} -- client.py already extracts and caches only these macros
    (see data.usda.nutrients), so this is a passthrough, not a transform.
    Failure: {"error": <code>}.
    """
    result = usda_client.get_nutrition(fdc_id, usda_client.USDA_API_KEY)
    if result.error is not None:
        return {"error": result.error}
    assert isinstance(result.food, dict)
    return result.food
