"""Tests for core.agent.providers.groq: the thin LangChain-facing adapter.
get_llm() only constructs a ChatGroq instance -- no network call happens here.
classify_exception() is pure and tested directly against real groq SDK exception
instances (constructing one needs no network call either)."""
import groq as groq_sdk
from langchain_groq import ChatGroq

from core.agent.providers import groq


def fake_response(status_code):
    return type("Response", (), {"request": None, "status_code": status_code, "headers": {}})()


def test_get_llm_returns_a_configured_chat_groq_instance():
    llm = groq.get_llm()

    assert isinstance(llm, ChatGroq)
    assert llm.model_name == groq.GROQ_MODEL


def test_get_llm_disables_the_sdks_own_retries():
    """core.agent.graph._invoke_with_retry owns retry/backoff now -- see Task 6."""
    llm = groq.get_llm()

    assert llm.max_retries == 0


def test_classify_exception_returns_rate_limited_for_rate_limit_error():
    error = groq_sdk.RateLimitError("rate limited", response=fake_response(429), body=None)

    assert groq.classify_exception(error) == "rate_limited"


def test_classify_exception_returns_timeout_for_transient_errors():
    errors = [
        groq_sdk.APITimeoutError(request=None),
        groq_sdk.APIConnectionError(request=None),
        groq_sdk.InternalServerError("down", response=fake_response(500), body=None),
    ]

    for error in errors:
        assert groq.classify_exception(error) == "timeout"


def test_classify_exception_returns_invalid_output_when_forced_tool_choice_is_refused():
    """Verified live: a forced tool_choice the model doesn't honor surfaces as
    groq.BadRequestError with body["error"]["code"] == "tool_use_failed"."""
    error = groq_sdk.BadRequestError(
        "tool refused", response=fake_response(400), body={"error": {"code": "tool_use_failed"}}
    )

    assert groq.classify_exception(error) == "invalid_output"


def test_classify_exception_returns_none_for_other_bad_request_errors():
    error = groq_sdk.BadRequestError(
        "bad schema", response=fake_response(400), body={"error": {"code": "invalid_request_error"}}
    )

    assert groq.classify_exception(error) is None


def test_classify_exception_returns_none_for_an_unrelated_exception():
    assert groq.classify_exception(RuntimeError("boom")) is None
