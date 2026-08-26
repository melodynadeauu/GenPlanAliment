"""Tests for core.agent.llm_adapter: builds the LangGraph graph (core.agent.graph) for
the configured provider and translates its final state into GenerationResult.
core.agent.graph itself is never touched here -- llm_adapter.agent_graph.build_graph is
monkeypatched to return a fake compiled graph with a scripted final state.
"""
import pytest
from langchain_core.messages import HumanMessage, SystemMessage

from core.agent import llm_adapter
from core.agent.schemas import PlanFood, PlanPropose


class FakeCompiledGraph:
    def __init__(self, final_state):
        self.final_state = final_state
        self.invoke_calls = []

    def invoke(self, initial_state, config=None):
        self.invoke_calls.append((initial_state, config))
        return self.final_state


@pytest.fixture
def fake_build_graph(monkeypatch):
    def _install(final_state):
        fake_graph = FakeCompiledGraph(final_state)
        monkeypatch.setattr(llm_adapter.agent_graph, "build_graph", lambda *a, **k: fake_graph)
        return fake_graph

    return _install


def test_generate_returns_the_plan_from_the_final_state_on_success(fake_build_graph):
    plan = PlanPropose(foods=[PlanFood(description="Apple", fdc_id="1", meal="snack", grams=100.0)])
    fake_build_graph({"plan": plan, "error": None})

    result = llm_adapter.generate("system", "user", [])

    assert result == llm_adapter.GenerationResult(plan, None)


@pytest.mark.parametrize("error", ["rate_limited", "timeout", "api_error", "invalid_output"])
def test_generate_returns_the_error_from_the_final_state(fake_build_graph, error):
    fake_build_graph({"plan": None, "error": error})

    result = llm_adapter.generate("system", "user", [])

    assert result == llm_adapter.GenerationResult(None, error)


def test_generate_builds_the_initial_state_with_system_and_user_messages(fake_build_graph):
    fake_graph = fake_build_graph({"plan": None, "error": "timeout"})

    llm_adapter.generate("sys prompt", "user prompt", [])

    initial_state, config = fake_graph.invoke_calls[0]
    assert isinstance(initial_state["messages"][0], SystemMessage)
    assert initial_state["messages"][0].content == "sys prompt"
    assert isinstance(initial_state["messages"][1], HumanMessage)
    assert initial_state["messages"][1].content == "user prompt"
    assert initial_state["turn"] == 0
    assert initial_state["tool_was_called"] is False
    assert initial_state["plan"] is None
    assert initial_state["error"] is None
    assert config["recursion_limit"] >= 50


def test_generate_returns_api_error_if_the_graph_itself_raises(monkeypatch):
    """Defense in depth for the "never raises" contract: core.agent.graph's own nodes
    already turn every LLM/tool failure into a state["error"] string, but LangGraph's
    runtime can still raise between node executions on its own (e.g. GraphRecursionError
    if a provider ever violated tool_choice badly enough to blow the turn budget) --
    that exception happens outside any node's try/except, so generate() must catch it too,
    not just trust the graph's final_state["error"] to always be reachable."""

    class RaisingGraph:
        def invoke(self, initial_state, config=None):
            raise RuntimeError("graph blew up")

    monkeypatch.setattr(llm_adapter.agent_graph, "build_graph", lambda *a, **k: RaisingGraph())

    result = llm_adapter.generate("system", "user", [])

    assert result == llm_adapter.GenerationResult(None, "api_error")


def test_generate_returns_api_error_if_build_graph_itself_raises(monkeypatch):
    """get_llm()/build_graph() must be inside generate()'s try too: get_llm() can raise
    (pydantic validation, missing env setup) and build_graph() calls bind_tools(), which
    can raise ValueError on an unconvertible tool schema. Neither happens inside
    compiled.invoke(), so this is a distinct failure point from the RaisingGraph case
    above."""

    def _raise(*a, **k):
        raise ValueError("unconvertible tool schema")

    monkeypatch.setattr(llm_adapter.agent_graph, "build_graph", _raise)

    result = llm_adapter.generate("system", "user", [])

    assert result == llm_adapter.GenerationResult(None, "api_error")
