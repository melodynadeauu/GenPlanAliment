"""Canonical tool vocabulary shared between the LLM loop (core.agent.llm_adapter) and each
provider adapter (core.agent.providers.*): declaring tools to a provider, and reporting
back what the provider asked to call.
"""
import inspect
from dataclasses import dataclass
from typing import Callable

from core.agent.schemas import PlanPropose

_PYTHON_TYPE_TO_JSON_SCHEMA = {
    str: {"type": "string"},
    float: {"type": "number"},
    int: {"type": "integer"},
}


@dataclass(frozen=True)
class ToolDeclaration:
    """A tool as advertised to the LLM: name, description, and its JSON-schema parameters."""

    name: str
    description: str
    parameters: dict


@dataclass(frozen=True)
class ToolCall:
    """One tool invocation requested by the LLM, translated from the provider's own shape."""

    id: str
    name: str
    arguments: dict


def build_tool_declaration(func: Callable[..., dict]) -> ToolDeclaration:
    """Introspect `func`'s signature into a ToolDeclaration. Only str/float/int parameters
    are supported -- every core.tools.usda_tool function takes a single str, which is all
    this needs today; extend _PYTHON_TYPE_TO_JSON_SCHEMA if a future tool needs more.
    """
    signature = inspect.signature(func)
    properties = {}
    required = []
    for param_name, param in signature.parameters.items():
        if param.annotation not in _PYTHON_TYPE_TO_JSON_SCHEMA:
            raise ValueError(
                f"build_tool_declaration: unsupported parameter type {param.annotation!r} for "
                f"{func.__name__}({param_name}); add it to _PYTHON_TYPE_TO_JSON_SCHEMA."
            )
        properties[param_name] = _PYTHON_TYPE_TO_JSON_SCHEMA[param.annotation]
        required.append(param_name)

    description = " ".join(line.strip() for line in (func.__doc__ or "").strip().splitlines())
    return ToolDeclaration(
        name=func.__name__,
        description=description,
        parameters={"type": "object", "properties": properties, "required": required},
    )


def build_submit_plan_declaration() -> ToolDeclaration:
    """The synthetic "I'm done" tool: calling it with a valid PlanPropose payload ends the
    tool-calling loop (core.agent.llm_adapter.generate). Its schema comes from PlanPropose
    itself, normalized -- neither Gemini nor Groq accept pydantic's raw $ref/$defs/title
    output (verified live: Gemini raises "Unknown field for Schema: $defs", and then
    ": title" once refs are inlined; Groq silently ignores an unresolved $ref and lets the
    model invent field names instead of validating against the real ones).
    """
    raw_schema = PlanPropose.model_json_schema()
    defs = raw_schema.get("$defs", {})
    parameters = _normalize_schema(raw_schema, defs)
    return ToolDeclaration(
        name="submit_plan",
        description="Submit the final, complete meal plan once all foods have been looked up.",
        parameters=parameters,
    )


def _normalize_schema(schema, defs: dict):
    """Recursively inline "$ref" against `defs` and drop "$defs"/"title" keys -- the parts
    of pydantic's JSON schema output that Gemini's and Groq's function-calling parameter
    validation don't accept.
    """
    if isinstance(schema, dict):
        if "$ref" in schema:
            target_name = schema["$ref"].rsplit("/", 1)[-1]
            return _normalize_schema(defs[target_name], defs)
        return {
            key: _normalize_schema(value, defs)
            for key, value in schema.items()
            if key not in ("$defs", "title")
        }
    if isinstance(schema, list):
        return [_normalize_schema(item, defs) for item in schema]
    return schema
