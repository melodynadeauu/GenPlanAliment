"""Gemini provider adapter: translates the canonical tool-calling protocol
(core.agent.tool_schema) to and from the google-generativeai SDK.
"""
import os
import time

import google.generativeai as genai
from dotenv import load_dotenv
from google.api_core import exceptions as gemini_exceptions
from google.generativeai.types import FunctionDeclaration, Tool

from core.agent.errors import LLMRateLimitedError, LLMTimeoutError
from core.agent.tool_schema import ToolCall, ToolDeclaration

# Verified live against this SDK/account on 2026-08-25: Decisions.docx's "Gemini 2.5 Flash"
# 404s with "no longer available to new users. Please update your code to use
# models/gemini-3.6-flash" -- that replacement is what's used here.
GEMINI_MODEL = "gemini-3.6-flash"

RETRY_DELAYS_SECONDS = [1, 2]
MAX_RETRIES = 2

_RATE_LIMIT_EXCEPTIONS = (gemini_exceptions.ResourceExhausted,)
_TRANSIENT_EXCEPTIONS = (
    gemini_exceptions.DeadlineExceeded,
    gemini_exceptions.ServiceUnavailable,
    gemini_exceptions.InternalServerError,
)


def _require_api_key(value: str | None) -> str:
    if not value:
        raise RuntimeError(
            "GEMINI_API_KEY is absent or empty. Define it in a .env file at the root of the "
            "project (see .env.example)."
        )
    return value


load_dotenv()
GEMINI_API_KEY = _require_api_key(os.getenv("GEMINI_API_KEY"))
genai.configure(api_key=GEMINI_API_KEY)


def _to_python(value):
    """Recursively convert proto-plus MapComposite/RepeatedComposite (what this SDK returns
    for function_call.args) into plain dict/list. Verified live: a nested submit_plan call
    (foods: [...]) comes back with nested MapComposite/RepeatedComposite, not plain Python.
    """
    if hasattr(value, "items"):
        return {key: _to_python(item) for key, item in value.items()}
    if hasattr(value, "__iter__") and not isinstance(value, (str, bytes)):
        return [_to_python(item) for item in value]
    return value


def _tool_config(force_tool_name: str | None) -> dict:
    if force_tool_name is not None:
        return {"function_calling_config": {"mode": "ANY", "allowed_function_names": [force_tool_name]}}
    return {"function_calling_config": {"mode": "AUTO"}}


def start_conversation(system_prompt: str, user_prompt: str, tool_declarations: list[ToolDeclaration]) -> dict:
    """Gemini conversation state: the configured model (tools baked in -- they don't change
    across a generate() call's turns) plus the message history.
    """
    tools = [
        Tool(
            function_declarations=[
                FunctionDeclaration(name=d.name, description=d.description, parameters=d.parameters)
                for d in tool_declarations
            ]
        )
    ]
    model = genai.GenerativeModel(GEMINI_MODEL, system_instruction=system_prompt, tools=tools)
    return {"model": model, "messages": [{"role": "user", "parts": [user_prompt]}]}


def call(state: dict, force_tool_name: str | None) -> tuple[dict, list[ToolCall]]:
    """One Gemini API call, retried per RETRY_DELAYS_SECONDS/MAX_RETRIES. Appends the
    model's turn to state["messages"] before returning, whether or not it made a tool call,
    so the next call sees it.
    """
    attempt = 0
    while True:
        try:
            response = state["model"].generate_content(
                state["messages"], tool_config=_tool_config(force_tool_name)
            )
        except _RATE_LIMIT_EXCEPTIONS:
            if attempt >= MAX_RETRIES:
                raise LLMRateLimitedError()
            time.sleep(RETRY_DELAYS_SECONDS[attempt])
            attempt += 1
            continue
        except _TRANSIENT_EXCEPTIONS:
            if attempt >= MAX_RETRIES:
                raise LLMTimeoutError()
            time.sleep(RETRY_DELAYS_SECONDS[attempt])
            attempt += 1
            continue
        break

    content = response.candidates[0].content
    state["messages"].append(content)

    tool_calls = [
        ToolCall(
            id=f"{part.function_call.name}-{i}",
            name=part.function_call.name,
            arguments=_to_python(part.function_call.args),
        )
        for i, part in enumerate(content.parts)
        if part.function_call
    ]
    return state, tool_calls


def append_tool_results(state: dict, results: list[tuple[ToolCall, dict]]) -> dict:
    """Verified live: the function-response turn must use role "user" -- this SDK/backend
    rejects role "function" ("Role 'function' is not supported"); "user" is what the SDK's
    own automatic-function-calling path uses internally.
    """
    for tool_call, result in results:
        state["messages"].append(
            {"role": "user", "parts": [{"function_response": {"name": tool_call.name, "response": result}}]}
        )
    return state
