"""Tests for core.agent.providers.gemini: the thin LangChain-facing adapter.
get_llm() only constructs a ChatGoogleGenerativeAI instance -- no network call happens
here. classify_exception() is pure and tested directly against real
google.genai.errors instances (constructing one needs no network call either)."""
import httpx
from google.genai import errors as genai_errors
from langchain_core.exceptions import ModelRateLimitError
from langchain_google_genai import ChatGoogleGenerativeAI

from core.agent.providers import gemini


def test_get_llm_returns_a_configured_chat_google_generative_ai_instance():
    llm = gemini.get_llm()

    assert isinstance(llm, ChatGoogleGenerativeAI)
    assert llm.model == gemini.GEMINI_MODEL


def test_get_llm_disables_the_sdks_own_retries():
    """core.agent.graph._invoke_with_retry owns retry/backoff now -- see Task 6."""
    llm = gemini.get_llm()

    assert llm.max_retries == 0


def test_classify_exception_returns_rate_limited_for_a_langchain_model_rate_limit_error():
    """This is what ChatGoogleGenerativeAI actually raises for a real 429: its own
    GoogleRateLimitError, a langchain_core.exceptions.ModelRateLimitError -- NOT a
    genai_errors.ClientError subclass. Verified live against langchain-google-genai
    4.3.5."""
    exc = ModelRateLimitError("quota exceeded")

    assert gemini.classify_exception(exc) == "rate_limited"


def test_classify_exception_returns_rate_limited_for_a_429_client_error():
    """Fallback branch: exercised only by a raw genai_errors.ClientError that bypasses
    the ChatGoogleGenerativeAI layer -- the real chat model wraps this into
    ModelRateLimitError instead, covered above."""
    exc = genai_errors.ClientError(code=429, response_json={"error": {"message": "quota"}})

    assert gemini.classify_exception(exc) == "rate_limited"


def test_classify_exception_returns_none_for_a_non_429_client_error():
    exc = genai_errors.ClientError(code=400, response_json={"error": {"message": "bad request"}})

    assert gemini.classify_exception(exc) is None


def test_classify_exception_returns_timeout_for_any_server_error():
    exc = genai_errors.ServerError(code=503, response_json={"error": {"message": "unavailable"}})

    assert gemini.classify_exception(exc) == "timeout"


def test_classify_exception_returns_timeout_for_an_httpx_connect_error():
    assert gemini.classify_exception(httpx.ConnectError("down")) == "timeout"


def test_classify_exception_returns_timeout_for_an_httpx_timeout_exception():
    assert gemini.classify_exception(httpx.TimeoutException("timed out")) == "timeout"


def test_classify_exception_returns_none_for_an_unrelated_exception():
    assert gemini.classify_exception(RuntimeError("boom")) is None
