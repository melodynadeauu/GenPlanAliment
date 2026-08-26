"""Tests for core.agent.graph: the LangGraph tool-calling loop. The chat model is faked
(FakeChatModel) so these tests never call a real provider -- core.agent.providers.{gemini,
groq} are only reached through the `provider` argument's classify_exception(), itself
faked here too (FakeProvider)."""
import json

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool

from core.agent import graph as agent_graph

APPLE = {"description": "Apple", "fdc_id": "1", "meal": "snack", "grams": 100.0}


@tool
def fake_tool(query: str) -> dict:
    """A fake data tool."""
    return {"results": [{"fdc_id": "1", "description": query}]}


@tool
def broken_tool(query: str) -> dict:
    """A fake data tool that raises instead of returning."""
    raise TypeError("boom")


def ai_message(tool_calls=None):
    return AIMessage(content="", tool_calls=tool_calls or [])


def submit_call(id_, foods):
    return {"name": "submit_plan", "args": {"foods": foods}, "id": id_, "type": "tool_call"}


def data_call(id_, name, args):
    return {"name": name, "args": args, "id": id_, "type": "tool_call"}


class _BoundFakeChatModel:
    def __init__(self, parent, tool_choice):
        self._parent = parent
        self.tool_choice = tool_choice

    def invoke(self, messages):
        self._parent.calls.append(self.tool_choice)
        item = self._parent.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class FakeChatModel:
    """Replays a scripted list of turns; each turn is either an AIMessage or an
    exception instance to raise from invoke(). bind_tools() records the tool_choice
    each subsequent invoke() call was bound with, in self.calls."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def bind_tools(self, tools, tool_choice=None):
        return _BoundFakeChatModel(self, tool_choice)


class FakeProvider:
    """Stands in for core.agent.providers.{gemini,groq}: only classify_exception()
    matters to core.agent.graph."""

    def __init__(self, classify=lambda exc: None):
        self.classify_exception = classify


@pytest.fixture(autouse=True)
def no_real_sleep(monkeypatch):
    sleeps = []
    monkeypatch.setattr(agent_graph.time, "sleep", lambda seconds: sleeps.append(seconds))
    return sleeps


def _initial_state():
    return {
        "messages": [SystemMessage(content="system"), HumanMessage(content="user")],
        "turn": 0,
        "tool_was_called": False,
        "plan": None,
        "error": None,
    }


def _tool_messages(result):
    return [m for m in result["messages"] if type(m).__name__ == "ToolMessage"]


def test_max_auto_turns_is_generous_enough_for_one_tool_call_per_turn_models():
    """Verified live against Groq's openai/gpt-oss-120b (2026-08-25): unlike Gemini, which
    batches many tool calls into a single turn, it calls exactly one tool per turn --
    search then lookup, one food at a time. A budget only large enough for Gemini's
    calling pattern starves it before it finishes gathering data, so the forced final
    turn fails instead of ever reaching submit_plan."""
    assert agent_graph.MAX_AUTO_TURNS >= 15


def test_finalizes_immediately_when_submit_plan_called_first_turn():
    model = FakeChatModel([ai_message([submit_call("1", [APPLE])])])
    compiled = agent_graph.build_graph(model, [fake_tool], FakeProvider())

    result = compiled.invoke(_initial_state(), config={"recursion_limit": 50})

    assert result["error"] is None
    assert result["plan"].foods[0].description == "Apple"


def test_executes_data_tool_then_finalizes():
    model = FakeChatModel(
        [
            ai_message([data_call("1", "fake_tool", {"query": "chicken gravy"})]),
            ai_message([submit_call("2", [APPLE])]),
        ]
    )
    compiled = agent_graph.build_graph(model, [fake_tool], FakeProvider())

    result = compiled.invoke(_initial_state(), config={"recursion_limit": 50})

    assert result["error"] is None
    tool_messages = _tool_messages(result)
    assert len(tool_messages) == 1
    assert json.loads(tool_messages[0].content) == {"results": [{"fdc_id": "1", "description": "chicken gravy"}]}
    assert result["tool_was_called"] is True


def test_feeds_back_unknown_tool_error_and_continues():
    model = FakeChatModel(
        [ai_message([data_call("1", "not_a_real_tool", {})]), ai_message([submit_call("2", [])])]
    )
    compiled = agent_graph.build_graph(model, [fake_tool], FakeProvider())

    result = compiled.invoke(_initial_state(), config={"recursion_limit": 50})

    assert result["error"] is None
    assert json.loads(_tool_messages(result)[0].content) == {"error": "unknown_tool"}


def test_feeds_back_tool_execution_error_and_continues():
    model = FakeChatModel(
        [
            ai_message([data_call("1", "broken_tool", {"query": "chicken gravy"})]),
            ai_message([submit_call("2", [])]),
        ]
    )
    compiled = agent_graph.build_graph(model, [broken_tool], FakeProvider())

    result = compiled.invoke(_initial_state(), config={"recursion_limit": 50})

    assert result["error"] is None
    assert json.loads(_tool_messages(result)[0].content) == {"error": "tool_execution_error"}


def test_forces_submit_plan_after_max_auto_turns():
    model = FakeChatModel(
        [ai_message([]) for _ in range(agent_graph.MAX_AUTO_TURNS)] + [ai_message([submit_call("1", [APPLE])])]
    )
    compiled = agent_graph.build_graph(model, [fake_tool], FakeProvider())

    result = compiled.invoke(_initial_state(), config={"recursion_limit": 50})

    assert result["error"] is None
    assert model.calls == [None] * agent_graph.MAX_AUTO_TURNS + ["submit_plan"]


def test_returns_invalid_output_when_forced_turn_still_skips_submit_plan():
    model = FakeChatModel([ai_message([]) for _ in range(agent_graph.MAX_AUTO_TURNS)] + [ai_message([])])
    compiled = agent_graph.build_graph(model, [fake_tool], FakeProvider())

    result = compiled.invoke(_initial_state(), config={"recursion_limit": 50})

    assert result["error"] == "invalid_output"


def test_returns_invalid_output_when_forced_turn_calls_wrong_tool_without_looping_further():
    """route_after_agent must check the turn-budget overflow before the tool_calls check:
    otherwise a provider that doesn't honor tool_choice on the forced turn (returning a
    data-tool call instead of submit_plan) routes to "tools" and the graph loops past the
    intended single forced call instead of finalizing with invalid_output."""
    model = FakeChatModel(
        [ai_message([]) for _ in range(agent_graph.MAX_AUTO_TURNS)]
        + [ai_message([data_call("1", "fake_tool", {"query": "chicken gravy"})])]
    )
    compiled = agent_graph.build_graph(model, [fake_tool], FakeProvider())

    result = compiled.invoke(_initial_state(), config={"recursion_limit": 50})

    assert result["error"] == "invalid_output"
    assert len(model.calls) == agent_graph.MAX_AUTO_TURNS + 1


def test_returns_invalid_output_when_submit_plan_is_empty_and_no_tool_was_called():
    model = FakeChatModel([ai_message([submit_call("1", [])])])
    compiled = agent_graph.build_graph(model, [fake_tool], FakeProvider())

    result = compiled.invoke(_initial_state(), config={"recursion_limit": 50})

    assert result["error"] == "invalid_output"
    assert result["plan"] is None


def test_allows_empty_submit_plan_when_a_tool_was_called_first():
    model = FakeChatModel(
        [
            ai_message([data_call("1", "fake_tool", {"query": "nonexistent food"})]),
            ai_message([submit_call("2", [])]),
        ]
    )
    compiled = agent_graph.build_graph(model, [fake_tool], FakeProvider())

    result = compiled.invoke(_initial_state(), config={"recursion_limit": 50})

    assert result["error"] is None
    assert result["plan"].foods == []


def test_returns_invalid_output_when_submit_plan_arguments_fail_validation():
    bad_call = {"name": "submit_plan", "args": {"foods": [{"description": "Apple"}]}, "id": "1", "type": "tool_call"}
    model = FakeChatModel([ai_message([bad_call])])
    compiled = agent_graph.build_graph(model, [fake_tool], FakeProvider())

    result = compiled.invoke(_initial_state(), config={"recursion_limit": 50})

    assert result["error"] == "invalid_output"


@pytest.mark.parametrize("outcome", ["rate_limited", "timeout"])
def test_retries_then_reports_error_once_retries_exhausted(no_real_sleep, outcome):
    model = FakeChatModel([RuntimeError("boom")] * 3)
    provider = FakeProvider(classify=lambda exc: outcome)
    compiled = agent_graph.build_graph(model, [fake_tool], provider)

    result = compiled.invoke(_initial_state(), config={"recursion_limit": 50})

    assert result["error"] == outcome
    assert no_real_sleep == [1, 2]


def test_retries_transient_failure_then_succeeds(no_real_sleep):
    model = FakeChatModel([RuntimeError("boom"), ai_message([submit_call("1", [APPLE])])])
    provider = FakeProvider(classify=lambda exc: "timeout")
    compiled = agent_graph.build_graph(model, [fake_tool], provider)

    result = compiled.invoke(_initial_state(), config={"recursion_limit": 50})

    assert result["error"] is None
    assert no_real_sleep == [1]


def test_reports_invalid_output_immediately_without_retrying(no_real_sleep):
    model = FakeChatModel([RuntimeError("refused")])
    provider = FakeProvider(classify=lambda exc: "invalid_output")
    compiled = agent_graph.build_graph(model, [fake_tool], provider)

    result = compiled.invoke(_initial_state(), config={"recursion_limit": 50})

    assert result["error"] == "invalid_output"
    assert no_real_sleep == []


def test_reports_api_error_for_an_unclassified_exception_without_retrying(no_real_sleep):
    model = FakeChatModel([RuntimeError("mystery")])
    provider = FakeProvider(classify=lambda exc: None)
    compiled = agent_graph.build_graph(model, [fake_tool], provider)

    result = compiled.invoke(_initial_state(), config={"recursion_limit": 50})

    assert result["error"] == "api_error"
    assert no_real_sleep == []
