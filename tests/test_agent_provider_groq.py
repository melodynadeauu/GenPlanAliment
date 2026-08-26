"""Tests for core.agent.providers.groq. The module-level Groq client is faked -- these
tests never call the real Groq API."""
import json

import groq as groq_sdk
import pytest

from core.agent.errors import LLMInvalidOutputError, LLMRateLimitedError, LLMTimeoutError
from core.agent.providers import groq
from core.agent.tool_schema import ToolCall, ToolDeclaration


class FakeFunction:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments


class FakeToolCall:
    def __init__(self, id, name, arguments_json):
        self.id = id
        self.function = FakeFunction(name, arguments_json)


class FakeMessage:
    def __init__(self, tool_calls=None):
        self.tool_calls = tool_calls or []


class FakeCompletion:
    def __init__(self, message):
        self.choices = [type("Choice", (), {"message": message})()]


class FakeCompletions:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def create(self, model, messages, tools, tool_choice):
        self.calls.append({"model": model, "messages": list(messages), "tools": tools, "tool_choice": tool_choice})
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class FakeClient:
    def __init__(self, responses):
        self.chat = type("Chat", (), {"completions": FakeCompletions(responses)})()


def install_fake_client(monkeypatch, responses):
    fake = FakeClient(responses)
    monkeypatch.setattr(groq, "_client", fake)
    return fake


def fake_response(status_code):
    return type("Response", (), {"request": None, "status_code": status_code, "headers": {}})()


@pytest.fixture(autouse=True)
def no_real_sleep(monkeypatch):
    sleeps = []
    monkeypatch.setattr(groq.time, "sleep", lambda seconds: sleeps.append(seconds))
    return sleeps


DECLARATIONS = [
    ToolDeclaration(
        name="search_food_tool",
        description="Search.",
        parameters={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
    )
]


def test_start_conversation_builds_system_and_user_messages_plus_tools():
    state = groq.start_conversation("be helpful", "find apples", DECLARATIONS)

    assert state["messages"] == [
        {"role": "system", "content": "be helpful"},
        {"role": "user", "content": "find apples"},
    ]
    assert state["tools"] == [
        {
            "type": "function",
            "function": {
                "name": "search_food_tool",
                "description": "Search.",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            },
        }
    ]


def test_call_returns_tool_call_and_appends_model_turn(monkeypatch):
    message = FakeMessage([FakeToolCall("call_1", "search_food_tool", json.dumps({"query": "chicken gravy"}))])
    install_fake_client(monkeypatch, [FakeCompletion(message)])
    state = {"tools": [], "messages": [{"role": "user", "content": "hi"}]}

    new_state, tool_calls = groq.call(state, force_tool_name=None)

    assert tool_calls == [ToolCall(id="call_1", name="search_food_tool", arguments={"query": "chicken gravy"})]
    assert new_state["messages"][-1] is message


def test_call_uses_auto_tool_choice_by_default(monkeypatch):
    fake = install_fake_client(monkeypatch, [FakeCompletion(FakeMessage())])
    state = {"tools": [], "messages": []}

    groq.call(state, force_tool_name=None)

    assert fake.chat.completions.calls[0]["tool_choice"] == "auto"
    assert fake.chat.completions.calls[0]["model"] == groq.GROQ_MODEL


def test_call_forces_named_tool_when_force_tool_name_given(monkeypatch):
    fake = install_fake_client(monkeypatch, [FakeCompletion(FakeMessage())])
    state = {"tools": [], "messages": []}

    groq.call(state, force_tool_name="submit_plan")

    assert fake.chat.completions.calls[0]["tool_choice"] == {"type": "function", "function": {"name": "submit_plan"}}


def test_call_returns_no_tool_calls_when_model_only_produced_text(monkeypatch):
    install_fake_client(monkeypatch, [FakeCompletion(FakeMessage())])
    state = {"tools": [], "messages": []}

    _state, tool_calls = groq.call(state, force_tool_name=None)

    assert tool_calls == []


def test_call_retries_transient_error_then_succeeds(monkeypatch, no_real_sleep):
    message = FakeMessage([FakeToolCall("call_1", "submit_plan", "{}")])
    install_fake_client(monkeypatch, [groq_sdk.APITimeoutError(request=None), FakeCompletion(message)])
    state = {"tools": [], "messages": []}

    _state, tool_calls = groq.call(state, force_tool_name=None)

    assert tool_calls[0].name == "submit_plan"
    assert no_real_sleep == [1]


def test_call_raises_timeout_error_after_exhausting_retries(monkeypatch, no_real_sleep):
    install_fake_client(monkeypatch, [groq_sdk.APITimeoutError(request=None)] * 3)
    state = {"tools": [], "messages": []}

    with pytest.raises(LLMTimeoutError):
        groq.call(state, force_tool_name=None)

    assert no_real_sleep == [1, 2]


def test_call_raises_rate_limited_error_after_exhausting_retries(monkeypatch):
    error = groq_sdk.RateLimitError("rate limited", response=fake_response(429), body=None)
    install_fake_client(monkeypatch, [error] * 3)
    state = {"tools": [], "messages": []}

    with pytest.raises(LLMRateLimitedError):
        groq.call(state, force_tool_name=None)


def test_call_raises_invalid_output_error_when_forced_tool_choice_is_refused(monkeypatch):
    """Verified live: a forced tool_choice the model doesn't honor surfaces as
    groq.BadRequestError with body["error"]["code"] == "tool_use_failed" -- treated as
    invalid output, not a transient failure, so it isn't retried."""
    error = groq_sdk.BadRequestError(
        "tool refused", response=fake_response(400), body={"error": {"code": "tool_use_failed"}}
    )
    install_fake_client(monkeypatch, [error])
    state = {"tools": [], "messages": []}

    with pytest.raises(LLMInvalidOutputError):
        groq.call(state, force_tool_name="submit_plan")


def test_call_reraises_bad_request_error_for_other_codes(monkeypatch):
    error = groq_sdk.BadRequestError(
        "bad schema", response=fake_response(400), body={"error": {"code": "invalid_request_error"}}
    )
    install_fake_client(monkeypatch, [error])
    state = {"tools": [], "messages": []}

    with pytest.raises(groq_sdk.BadRequestError):
        groq.call(state, force_tool_name=None)


def test_append_tool_results_adds_tool_role_messages():
    state = {"messages": []}
    tool_call = ToolCall(id="call_1", name="search_food_tool", arguments={"query": "apple"})

    new_state = groq.append_tool_results(state, [(tool_call, {"results": []})])

    assert new_state["messages"] == [
        {"role": "tool", "tool_call_id": "call_1", "content": json.dumps({"results": []})}
    ]
