"""Tests for core.agent.llm_adapter: the provider-agnostic tool-calling loop.
core.agent.providers.{gemini,groq} are never touched here -- llm_adapter._provider is
swapped for a fake that speaks the same three-function protocol.
"""
import pytest

from core.agent import llm_adapter
from core.agent.errors import LLMInvalidOutputError, LLMRateLimitedError, LLMTimeoutError
from core.agent.tool_schema import ToolCall


def fake_tool(query: str) -> dict:
    """A fake data tool."""
    return {"results": [{"fdc_id": "1", "description": query}]}


def broken_tool(query: str) -> dict:
    """A fake data tool that raises instead of returning."""
    raise TypeError("boom")


class FakeProvider:
    """Replays a scripted list of turns; each turn is either a list[ToolCall] (what the
    model called this turn) or an exception instance to raise from call()."""

    def __init__(self, turns):
        self.turns = list(turns)
        self.calls = []
        self.appended_results = []

    def start_conversation(self, system_prompt, user_prompt, tool_declarations):
        return {"system_prompt": system_prompt, "user_prompt": user_prompt, "declarations": tool_declarations}

    def call(self, state, force_tool_name):
        self.calls.append(force_tool_name)
        turn = self.turns.pop(0)
        if isinstance(turn, Exception):
            raise turn
        return state, turn

    def append_tool_results(self, state, results):
        self.appended_results.append(results)
        return state


@pytest.fixture
def fake_provider(monkeypatch):
    def _install(turns):
        provider = FakeProvider(turns)
        monkeypatch.setattr(llm_adapter, "_provider", provider)
        return provider

    return _install


def test_generate_finalizes_immediately_when_submit_plan_called_first_turn(fake_provider):
    submit_call = ToolCall(
        id="1",
        name="submit_plan",
        arguments={
            "foods": [{"description": "Apple", "fdc_id": "1", "meal": "snack", "grams": 100.0}]
        },
    )
    fake_provider([[submit_call]])

    result = llm_adapter.generate("system", "user", [fake_tool])

    assert result.error is None
    assert result.plan.foods[0].description == "Apple"


def test_generate_executes_data_tool_then_finalizes(fake_provider):
    tool_call = ToolCall(id="1", name="fake_tool", arguments={"query": "chicken gravy"})
    submit_call = ToolCall(
        id="2",
        name="submit_plan",
        arguments={
            "foods": [
                {"description": "CHICKEN GRAVY", "fdc_id": "2620254", "meal": "lunch", "grams": 150.0}
            ]
        },
    )
    provider = fake_provider([[tool_call], [submit_call]])

    result = llm_adapter.generate("system", "user", [fake_tool])

    assert result.error is None
    assert provider.appended_results == [
        [(tool_call, {"results": [{"fdc_id": "1", "description": "chicken gravy"}]})]
    ]


def test_generate_feeds_back_unknown_tool_error_and_continues(fake_provider):
    unknown_call = ToolCall(id="1", name="not_a_real_tool", arguments={})
    submit_call = ToolCall(id="2", name="submit_plan", arguments={"foods": []})
    provider = fake_provider([[unknown_call], [submit_call]])

    result = llm_adapter.generate("system", "user", [fake_tool])

    assert result.error is None
    assert provider.appended_results == [[(unknown_call, {"error": "unknown_tool"})]]


def test_generate_feeds_back_tool_execution_error_and_continues(fake_provider):
    broken_call = ToolCall(id="1", name="broken_tool", arguments={"query": "chicken gravy"})
    submit_call = ToolCall(id="2", name="submit_plan", arguments={"foods": []})
    provider = fake_provider([[broken_call], [submit_call]])

    result = llm_adapter.generate("system", "user", [broken_tool])

    assert result.error is None
    assert provider.appended_results == [[(broken_call, {"error": "tool_execution_error"})]]


def test_max_auto_turns_is_generous_enough_for_one_tool_call_per_turn_models():
    """Verified live against Groq's openai/gpt-oss-120b (2026-08-25): unlike Gemini, which
    batches many tool calls into a single turn, it calls exactly one tool per turn --
    search then lookup, one food at a time. A budget only large enough for Gemini's
    calling pattern starves it before it finishes gathering data, so the forced final
    turn fails with a tool_choice mismatch (core.agent.providers.groq raises
    LLMInvalidOutputError) instead of ever reaching submit_plan."""
    assert llm_adapter.MAX_AUTO_TURNS >= 15


def test_generate_forces_submit_plan_after_max_auto_turns(fake_provider):
    submit_call = ToolCall(
        id="1",
        name="submit_plan",
        arguments={
            "foods": [{"description": "Apple", "fdc_id": "1", "meal": "snack", "grams": 100.0}]
        },
    )
    provider = fake_provider([[]] * llm_adapter.MAX_AUTO_TURNS + [[submit_call]])

    result = llm_adapter.generate("system", "user", [fake_tool])

    assert result.error is None
    assert provider.calls == [None] * llm_adapter.MAX_AUTO_TURNS + ["submit_plan"]


def test_generate_returns_invalid_output_when_submit_plan_is_empty_and_no_tool_was_called(fake_provider):
    """The LLM must ground every food in a search_food_tool/get_nutrition_tool call before
    submitting -- a bare `foods: []` with no tool call anywhere beforehand means it never
    tried, not that an empty plan is genuinely correct."""
    submit_call = ToolCall(id="1", name="submit_plan", arguments={"foods": []})
    fake_provider([[submit_call]])

    result = llm_adapter.generate("system", "user", [fake_tool])

    assert result == llm_adapter.GenerationResult(None, "invalid_output")


def test_generate_returns_invalid_output_when_forced_turn_submits_empty_with_no_prior_tool_calls(fake_provider):
    submit_call = ToolCall(id="1", name="submit_plan", arguments={"foods": []})
    fake_provider([[]] * llm_adapter.MAX_AUTO_TURNS + [[submit_call]])

    result = llm_adapter.generate("system", "user", [fake_tool])

    assert result == llm_adapter.GenerationResult(None, "invalid_output")


def test_generate_returns_invalid_output_when_forced_turn_still_skips_submit_plan(fake_provider):
    fake_provider([[]] * llm_adapter.MAX_AUTO_TURNS + [[]])

    result = llm_adapter.generate("system", "user", [fake_tool])

    assert result == llm_adapter.GenerationResult(None, "invalid_output")


def test_generate_returns_invalid_output_when_submit_plan_arguments_fail_validation(fake_provider):
    bad_call = ToolCall(id="1", name="submit_plan", arguments={"foods": [{"description": "Apple"}]})
    fake_provider([[bad_call]])

    result = llm_adapter.generate("system", "user", [fake_tool])

    assert result == llm_adapter.GenerationResult(None, "invalid_output")


@pytest.mark.parametrize(
    "exception, expected_error",
    [
        (LLMRateLimitedError(), "rate_limited"),
        (LLMTimeoutError(), "timeout"),
        (LLMInvalidOutputError(), "invalid_output"),
        (RuntimeError("boom"), "api_error"),
    ],
)
def test_generate_maps_provider_exceptions_to_error_codes(fake_provider, exception, expected_error):
    fake_provider([exception])

    result = llm_adapter.generate("system", "user", [fake_tool])

    assert result == llm_adapter.GenerationResult(None, expected_error)
