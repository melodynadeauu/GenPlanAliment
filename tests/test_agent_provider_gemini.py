"""Tests for core.agent.providers.gemini. google.generativeai.GenerativeModel is faked --
these tests never call the real Gemini API."""
import pytest
from google.api_core import exceptions as gemini_exceptions

from core.agent.errors import LLMRateLimitedError, LLMTimeoutError
from core.agent.providers import gemini
from core.agent.tool_schema import ToolCall, ToolDeclaration, build_submit_plan_declaration


class FakeFunctionCall:
    """Mimics google.generativeai's proto FunctionCall: falsy (like an empty proto) when
    there's no call, since gemini.call() checks `part.function_call` truthiness."""

    def __init__(self, name="", args=None):
        self.name = name
        self.args = args or {}

    def __bool__(self):
        return bool(self.name)


class FakePart:
    def __init__(self, function_call=None):
        self.function_call = function_call or FakeFunctionCall()


class FakeContent:
    def __init__(self, parts):
        self.parts = parts


class FakeCandidate:
    def __init__(self, parts):
        self.content = FakeContent(parts)


class FakeResponse:
    def __init__(self, parts):
        self.candidates = [FakeCandidate(parts)]


class FakeGeminiModel:
    def __init__(self, responses):
        self.responses = list(responses)
        self.generate_content_calls = []

    def generate_content(self, messages, tool_config=None):
        self.generate_content_calls.append({"messages": list(messages), "tool_config": tool_config})
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


@pytest.fixture(autouse=True)
def no_real_sleep(monkeypatch):
    sleeps = []
    monkeypatch.setattr(gemini.time, "sleep", lambda seconds: sleeps.append(seconds))
    return sleeps


DECLARATIONS = [
    ToolDeclaration(
        name="search_food_tool",
        description="Search.",
        parameters={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
    )
]


def test_start_conversation_builds_model_with_tools_and_system_instruction(monkeypatch):
    captured = {}

    def fake_generative_model(model_name, system_instruction=None, tools=None):
        captured["model_name"] = model_name
        captured["system_instruction"] = system_instruction
        captured["tools"] = tools
        return FakeGeminiModel([])

    monkeypatch.setattr(gemini.genai, "GenerativeModel", fake_generative_model)

    state = gemini.start_conversation("be helpful", "find apples", DECLARATIONS)

    assert captured["model_name"] == gemini.GEMINI_MODEL
    assert captured["system_instruction"] == "be helpful"
    assert captured["tools"] is not None
    assert state["messages"] == [{"role": "user", "parts": ["find apples"]}]


def test_start_conversation_accepts_real_normalized_submit_plan_schema(monkeypatch):
    """The real build_submit_plan_declaration() output (PlanPropose.model_json_schema(),
    normalized to strip $ref/$defs/title) must be accepted by the REAL
    google.generativeai.types.FunctionDeclaration/Tool constructors -- this project's whole
    design hinges on that (verified live during design, but only GenerativeModel itself is
    faked here, so no network call happens; FunctionDeclaration/Tool construction and
    validation run for real client-side)."""
    captured = {}

    def fake_generative_model(model_name, system_instruction=None, tools=None):
        captured["model_name"] = model_name
        captured["tools"] = tools
        return FakeGeminiModel([])

    monkeypatch.setattr(gemini.genai, "GenerativeModel", fake_generative_model)

    gemini.start_conversation("system", "user", [build_submit_plan_declaration()])

    assert captured["model_name"] == gemini.GEMINI_MODEL


def test_call_returns_tool_call_and_appends_model_turn():
    fc = FakeFunctionCall(name="search_food_tool", args={"query": "chicken gravy"})
    response = FakeResponse([FakePart(fc)])
    state = {"model": FakeGeminiModel([response]), "messages": [{"role": "user", "parts": ["hi"]}]}

    new_state, tool_calls = gemini.call(state, force_tool_name=None)

    assert tool_calls == [
        ToolCall(id="search_food_tool-0", name="search_food_tool", arguments={"query": "chicken gravy"})
    ]
    assert len(new_state["messages"]) == 2


def test_call_converts_nested_map_and_repeated_composite_args():
    """Verified live: Gemini returns nested function_call.args as proto-plus
    MapComposite/RepeatedComposite, not plain dict/list -- a shallow dict() isn't enough."""

    class FakeMapComposite:
        def __init__(self, data):
            self._data = data

        def items(self):
            return self._data.items()

    class FakeRepeatedComposite:
        def __init__(self, items):
            self._items = items

        def __iter__(self):
            return iter(self._items)

    nested_args = FakeMapComposite({"foods": FakeRepeatedComposite([FakeMapComposite({"grams": 150.0})])})
    fc = FakeFunctionCall(name="submit_plan", args=nested_args)
    state = {"model": FakeGeminiModel([FakeResponse([FakePart(fc)])]), "messages": []}

    _state, tool_calls = gemini.call(state, force_tool_name=None)

    assert tool_calls[0].arguments == {"foods": [{"grams": 150.0}]}


def test_call_uses_auto_mode_by_default():
    model = FakeGeminiModel([FakeResponse([FakePart()])])
    state = {"model": model, "messages": []}

    gemini.call(state, force_tool_name=None)

    assert model.generate_content_calls[0]["tool_config"] == {"function_calling_config": {"mode": "AUTO"}}


def test_call_forces_named_tool_when_force_tool_name_given():
    model = FakeGeminiModel([FakeResponse([FakePart(FakeFunctionCall("submit_plan", {}))])])
    state = {"model": model, "messages": []}

    gemini.call(state, force_tool_name="submit_plan")

    assert model.generate_content_calls[0]["tool_config"] == {
        "function_calling_config": {"mode": "ANY", "allowed_function_names": ["submit_plan"]}
    }


def test_call_returns_no_tool_calls_when_model_only_produced_text():
    state = {"model": FakeGeminiModel([FakeResponse([FakePart()])]), "messages": []}

    _state, tool_calls = gemini.call(state, force_tool_name=None)

    assert tool_calls == []


def test_call_retries_transient_error_then_succeeds(no_real_sleep):
    response = FakeResponse([FakePart(FakeFunctionCall("submit_plan", {}))])
    model = FakeGeminiModel([gemini_exceptions.ServiceUnavailable("down"), response])
    state = {"model": model, "messages": []}

    _state, tool_calls = gemini.call(state, force_tool_name=None)

    assert tool_calls[0].name == "submit_plan"
    assert no_real_sleep == [1]


def test_call_raises_timeout_error_after_exhausting_retries(no_real_sleep):
    model = FakeGeminiModel([gemini_exceptions.DeadlineExceeded("slow")] * 3)
    state = {"model": model, "messages": []}

    with pytest.raises(LLMTimeoutError):
        gemini.call(state, force_tool_name=None)

    assert no_real_sleep == [1, 2]


def test_call_raises_rate_limited_error_after_exhausting_retries():
    model = FakeGeminiModel([gemini_exceptions.ResourceExhausted("quota")] * 3)
    state = {"model": model, "messages": []}

    with pytest.raises(LLMRateLimitedError):
        gemini.call(state, force_tool_name=None)


def test_call_does_not_retry_non_transient_errors():
    model = FakeGeminiModel([gemini_exceptions.InvalidArgument("bad request")])
    state = {"model": model, "messages": []}

    with pytest.raises(gemini_exceptions.InvalidArgument):
        gemini.call(state, force_tool_name=None)

    assert len(model.generate_content_calls) == 1


def test_append_tool_results_adds_function_response_messages():
    """Verified live: the function-response turn must use role "user", not "function" --
    this SDK/backend rejects role "function" with "Role 'function' is not supported"."""
    state = {"messages": []}
    tool_call = ToolCall(id="1", name="search_food_tool", arguments={"query": "apple"})

    new_state = gemini.append_tool_results(state, [(tool_call, {"results": []})])

    assert new_state["messages"] == [
        {"role": "user", "parts": [{"function_response": {"name": "search_food_tool", "response": {"results": []}}}]}
    ]
