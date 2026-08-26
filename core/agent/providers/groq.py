"""Groq provider adapter: translates the canonical tool-calling protocol
(core.agent.tool_schema) to and from the groq SDK (OpenAI-compatible).

Secondary provider (Decisions.docx: "Ajouter llm secondaire au cas où"), not the actively
used path -- Gemini is primary.
"""
import json
import os
import time

import groq
from dotenv import load_dotenv
from groq import Groq

from core.agent.errors import LLMInvalidOutputError, LLMRateLimitedError, LLMTimeoutError
from core.agent.tool_schema import ToolCall, ToolDeclaration

# Verified live against this account on 2026-08-25: llama-3.3-70b-versatile no longer
# exists on this account; openai/gpt-oss-120b is the closest available equivalent with
# confirmed tool-calling support.
GROQ_MODEL = "openai/gpt-oss-120b"

RETRY_DELAYS_SECONDS = [1, 2]
MAX_RETRIES = 2

_RATE_LIMIT_EXCEPTIONS = (groq.RateLimitError,)
_TRANSIENT_EXCEPTIONS = (groq.APITimeoutError, groq.APIConnectionError, groq.InternalServerError)


def _require_api_key(value: str | None) -> str:
    if not value:
        raise RuntimeError(
            "GROQ_API_KEY is absent or empty. Define it in a .env file at the root of the "
            "project (see .env.example)."
        )
    return value


load_dotenv()
GROQ_API_KEY = _require_api_key(os.getenv("GROQ_API_KEY"))
_client = Groq(api_key=GROQ_API_KEY)


def _tool_choice(force_tool_name: str | None):
    if force_tool_name is not None:
        return {"type": "function", "function": {"name": force_tool_name}}
    return "auto"


def start_conversation(system_prompt: str, user_prompt: str, tool_declarations: list[ToolDeclaration]) -> dict:
    tools = [
        {"type": "function", "function": {"name": d.name, "description": d.description, "parameters": d.parameters}}
        for d in tool_declarations
    ]
    return {
        "tools": tools,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }


def call(state: dict, force_tool_name: str | None) -> tuple[dict, list[ToolCall]]:
    """One Groq API call, retried per RETRY_DELAYS_SECONDS/MAX_RETRIES. Appends the model's
    turn to state["messages"] before returning, whether or not it made a tool call.
    """
    attempt = 0
    while True:
        try:
            response = _client.chat.completions.create(
                model=GROQ_MODEL,
                messages=state["messages"],
                tools=state["tools"],
                tool_choice=_tool_choice(force_tool_name),
            )
        except groq.BadRequestError as e:
            if isinstance(e.body, dict) and e.body.get("error", {}).get("code") == "tool_use_failed":
                raise LLMInvalidOutputError() from e
            raise
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

    message = response.choices[0].message
    state["messages"].append(message)

    tool_calls = [
        ToolCall(id=tc.id, name=tc.function.name, arguments=json.loads(tc.function.arguments))
        for tc in (message.tool_calls or [])
    ]
    return state, tool_calls


def append_tool_results(state: dict, results: list[tuple[ToolCall, dict]]) -> dict:
    for tool_call, result in results:
        state["messages"].append({"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(result)})
    return state
