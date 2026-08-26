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


class _FakeNutritionTool:
    """Stands in for core.tools.usda_tool.get_nutrition_tool: only .invoke() matters
    to resolve_recompute_node. get_nutrition_tool is a frozen pydantic StructuredTool,
    so its .invoke can't be monkeypatched in place -- the whole object is replaced
    instead (see fake_nutrition_lookup below).
    """

    @staticmethod
    def invoke(args):
        return {"macros_per_100g": {"kcal": 100.0, "protein_g": 1.0, "fat_g": 0.0, "carbs_g": 0.0}}


@pytest.fixture(autouse=True)
def fake_nutrition_lookup(monkeypatch):
    """resolve_recompute_node calls the real get_nutrition_tool -- fake it here so no
    test in this file ever hits the network. 100 kcal/100g means a 100g food resolves
    to exactly 100 kcal, matching APPLE's grams below.
    """
    monkeypatch.setattr(agent_graph, "get_nutrition_tool", _FakeNutritionTool())


def _initial_state(target_kcal=0.0, dislikes=None):
    """target_kcal defaults to 0 (falsy), which skips the G1 conformity check entirely
    -- most pre-existing tests in this file care about the tool-calling loop, not the
    calorie/dislikes guardrails, so they'd otherwise need a food-count-matching target."""
    return {
        "messages": [SystemMessage(content="system"), HumanMessage(content="user")],
        "turn": 0,
        "tool_was_called": False,
        "plan": None,
        "error": None,
        "target_kcal": target_kcal,
        "dislikes": dislikes or [],
        "resolved_total_kcal": None,
        "attempt": 1,
        "degraded": False,
        "violations": [],
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


# --- G1/G2/G3/G7: resolve_recompute / validate_guardrails / retry / degrade ---


def test_conforming_plan_reaches_finalize_without_retry():
    """APPLE is 100g and fake_nutrition_lookup resolves 100 kcal/100g -> total 100 kcal,
    matching target_kcal=100 exactly. No dislikes. Must finalize on the first attempt."""
    model = FakeChatModel([ai_message([submit_call("1", [APPLE])])])
    compiled = agent_graph.build_graph(model, [fake_tool], FakeProvider())

    result = compiled.invoke(_initial_state(target_kcal=100.0), config={"recursion_limit": 50})

    assert result["error"] is None
    assert result["degraded"] is False
    assert result["attempt"] == 1
    assert result["plan"].foods[0].description == "Apple"


def test_disliked_food_triggers_one_retry_then_succeeds():
    """First proposal is on the dislikes list; second (after the injected violation
    reason) isn't. Must finalize on attempt 2, not degrade."""
    bad = {"description": "Apple", "fdc_id": "1", "meal": "snack", "grams": 100.0}
    good = {"description": "Pear", "fdc_id": "2", "meal": "snack", "grams": 100.0}
    model = FakeChatModel([ai_message([submit_call("1", [bad])]), ai_message([submit_call("2", [good])])])
    compiled = agent_graph.build_graph(model, [fake_tool], FakeProvider())

    result = compiled.invoke(
        _initial_state(target_kcal=100.0, dislikes=["apple"]), config={"recursion_limit": 50}
    )

    assert result["error"] is None
    assert result["degraded"] is False
    assert result["attempt"] == 2
    assert result["plan"].foods[0].description == "Pear"


def test_exhausted_retries_degrades_instead_of_looping_forever():
    """Every attempt keeps violating -- after MAX_ATTEMPTS, degrade rather than loop
    forever or silently show a non-conforming plan."""
    bad = {"description": "Apple", "fdc_id": "1", "meal": "snack", "grams": 100.0}
    model = FakeChatModel([ai_message([submit_call(str(i), [bad])]) for i in range(agent_graph.MAX_ATTEMPTS)])
    compiled = agent_graph.build_graph(model, [fake_tool], FakeProvider())

    result = compiled.invoke(
        _initial_state(target_kcal=100.0, dislikes=["apple"]), config={"recursion_limit": 50}
    )

    assert result["error"] is None
    assert result["degraded"] is True
    assert result["plan"] is not None  # degraded still returns the last plan, with a warning
    assert result["attempt"] == agent_graph.MAX_ATTEMPTS
