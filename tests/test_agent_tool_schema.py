"""Tests for core.agent.tool_schema: turning Python callables and PlanPropose into the
JSON-schema tool declarations an LLM provider accepts."""
import pytest

from core.agent.tool_schema import ToolDeclaration, build_submit_plan_declaration, build_tool_declaration
from core.tools.usda_tool import get_nutrition_tool, search_food_tool


def test_build_tool_declaration_from_search_food_tool():
    declaration = build_tool_declaration(search_food_tool)

    assert declaration == ToolDeclaration(
        name="search_food_tool",
        description=(
            'Search USDA foods for `query`. Success: {"results": [{"fdc_id", "description"}, ...]} '
            "(client.py already trims each result to fdc_id + description; passed through as-is). "
            'Failure: {"error": <code>}.'
        ),
        parameters={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
    )


def test_build_tool_declaration_from_get_nutrition_tool():
    declaration = build_tool_declaration(get_nutrition_tool)

    assert declaration.name == "get_nutrition_tool"
    assert declaration.parameters == {
        "type": "object",
        "properties": {"fdc_id": {"type": "string"}},
        "required": ["fdc_id"],
    }


def test_build_tool_declaration_rejects_unsupported_parameter_type():
    def unsupported_tool(items: list) -> dict:
        """Not supported."""
        return {}

    with pytest.raises(ValueError, match="list"):
        build_tool_declaration(unsupported_tool)


def test_build_submit_plan_declaration_has_no_refs_defs_or_titles():
    declaration = build_submit_plan_declaration()

    assert declaration.name == "submit_plan"
    serialized = repr(declaration.parameters)
    assert "$ref" not in serialized
    assert "$defs" not in serialized
    assert "'title'" not in serialized


def test_build_submit_plan_declaration_matches_plan_propose_shape():
    declaration = build_submit_plan_declaration()

    assert declaration.parameters == {
        "type": "object",
        "description": "A proposed meal plan: the list of foods that make it up.",
        "properties": {
            "foods": {
                "type": "array",
                "items": {
                    "type": "object",
                    "description": "One food item in a proposed plan.",
                    "properties": {
                        "description": {"type": "string"},
                        "fdc_id": {"type": "string"},
                        "grams": {
                            "type": "number",
                            "description": (
                                "The actual portion consumed, in grams. Independent of the 100g scale that "
                                "core.tools.usda_tool.get_nutrition_tool's macros_per_100g is expressed in -- "
                                "not itself a unit to convert, it's the multiplier applied to that per-100g figure."
                            ),
                        },
                    },
                    "required": ["description", "fdc_id", "grams"],
                },
            }
        },
        "required": ["foods"],
    }
