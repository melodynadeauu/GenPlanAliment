"""The provider-agnostic agent loop: force a structured PlanPropose out of whichever
LLM_PROVIDER is configured, executing data tools (search_food_tool/get_nutrition_tool)
along the way. Never raises -- see GenerationResult.
"""
import os
from dataclasses import dataclass
from typing import Callable

from dotenv import load_dotenv
from pydantic import ValidationError

from core.agent.errors import LLMInvalidOutputError, LLMRateLimitedError, LLMTimeoutError
from core.agent.schemas import PlanPropose
from core.agent.tool_schema import ToolCall, build_submit_plan_declaration, build_tool_declaration

SUBMIT_PLAN_TOOL_NAME = "submit_plan"
# Sized for Groq's openai/gpt-oss-120b, which calls exactly one tool per turn (search then
# lookup, one food at a time) -- unlike Gemini, which batches many tool calls into a single
# turn and typically finishes in 1. A lower budget starves the one-tool-per-turn pattern
# before it's done gathering data, so the forced final turn errors instead of ever reaching
# submit_plan (verified live against Groq on 2026-08-25).
MAX_AUTO_TURNS = 15


def _require_provider(value: str | None) -> str:
    if value not in ("gemini", "groq"):
        raise RuntimeError(
            f"LLM_PROVIDER must be 'gemini' or 'groq', got {value!r}. Define it in a .env "
            "file at the root of the project (see .env.example)."
        )
    return value


load_dotenv()
LLM_PROVIDER = _require_provider(os.getenv("LLM_PROVIDER"))

if LLM_PROVIDER == "gemini":
    from core.agent.providers import gemini as _provider
else:
    from core.agent.providers import groq as _provider


@dataclass(frozen=True)
class GenerationResult:
    """Outcome of generate(): either `plan` on success, or `error` (one of "rate_limited",
    "timeout", "api_error", "invalid_output") on failure -- never both, never an exception.

    target_kcal defaults to None here -- generate() itself doesn't know the calorie target,
    it only drives the tool-calling loop. plan_generator.generate_daily_plan() fills it in
    from the deterministic pipeline it already ran before calling generate().
    """

    plan: PlanPropose | None
    error: str | None
    target_kcal: float | None = None


def generate(system_prompt: str, user_prompt: str, tools: list[Callable[..., dict]]) -> GenerationResult:
    """Run the tool-calling loop against the configured provider until the LLM calls
    submit_plan with a valid PlanPropose payload, up to MAX_AUTO_TURNS turns in auto mode.
    If it still hasn't by then, one final call forces submit_plan via the provider's native
    forced tool-choice, rather than giving up -- Decisions.docx's guardrail: a bounded
    number of attempts before degrading, never an unbounded loop.
    """
    tools_by_name = {fn.__name__: fn for fn in tools}
    tool_was_called = False
    try:
        declarations = [build_tool_declaration(fn) for fn in tools] + [build_submit_plan_declaration()]
        state = _provider.start_conversation(system_prompt, user_prompt, declarations)
    except Exception:
        return GenerationResult(None, "api_error")

    for _turn in range(MAX_AUTO_TURNS):
        outcome = _call_provider(state, force_tool_name=None)
        if isinstance(outcome, GenerationResult):
            return outcome
        state, tool_calls = outcome

        submit_call = _find_call(tool_calls, SUBMIT_PLAN_TOOL_NAME)
        if submit_call is not None:
            return _finalize(submit_call, tool_was_called)

        if tool_calls:
            tool_was_called = True
            state = _provider.append_tool_results(state, _execute(tool_calls, tools_by_name))

    outcome = _call_provider(state, force_tool_name=SUBMIT_PLAN_TOOL_NAME)
    if isinstance(outcome, GenerationResult):
        return outcome
    _state, tool_calls = outcome

    submit_call = _find_call(tool_calls, SUBMIT_PLAN_TOOL_NAME)
    if submit_call is None:
        return GenerationResult(None, "invalid_output")
    return _finalize(submit_call, tool_was_called)


def _call_provider(state, force_tool_name: str | None):
    """Run one provider turn, translating its canonical exceptions into a GenerationResult.
    Returns (state, tool_calls) on success, or a GenerationResult on failure -- the caller
    tells the two apart with isinstance().
    """
    try:
        return _provider.call(state, force_tool_name)
    except LLMRateLimitedError:
        return GenerationResult(None, "rate_limited")
    except LLMTimeoutError:
        return GenerationResult(None, "timeout")
    except LLMInvalidOutputError:
        return GenerationResult(None, "invalid_output")
    except Exception:
        return GenerationResult(None, "api_error")


def _find_call(tool_calls: list[ToolCall], name: str) -> ToolCall | None:
    return next((tc for tc in tool_calls if tc.name == name), None)


def _execute(tool_calls: list[ToolCall], tools_by_name: dict) -> list[tuple[ToolCall, dict]]:
    results = []
    for tool_call in tool_calls:
        fn = tools_by_name.get(tool_call.name)
        if fn is None:
            result = {"error": "unknown_tool"}
        else:
            try:
                result = fn(**tool_call.arguments)
            except Exception:
                result = {"error": "tool_execution_error"}
        results.append((tool_call, result))
    return results


def _finalize(submit_call: ToolCall, tool_was_called: bool) -> GenerationResult:
    try:
        plan = PlanPropose(**submit_call.arguments)
    except (ValidationError, TypeError):
        return GenerationResult(None, "invalid_output")
    # PlanPropose itself allows an empty foods list (see core.agent.schemas), but an empty
    # plan is only genuinely valid if the LLM actually tried and found nothing to add --
    # not if it skipped straight to submit_plan without ever calling a data tool.
    if not plan.foods and not tool_was_called:
        return GenerationResult(None, "invalid_output")
    return GenerationResult(plan, None)
