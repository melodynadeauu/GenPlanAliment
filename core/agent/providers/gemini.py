"""Gemini provider adapter: a LangChain ChatGoogleGenerativeAI instance plus the bit
core.agent.graph needs to translate this SDK's failures into the canonical error
codes GenerationResult carries. Retry/backoff itself lives once, provider-agnostically,
in core.agent.graph._invoke_with_retry.
"""
import os

import httpx
from dotenv import load_dotenv
from google.genai import errors as genai_errors
from langchain_core.exceptions import ModelRateLimitError
from langchain_google_genai import ChatGoogleGenerativeAI

# gemini-2.5-flash/-lite are 404 on this account ("no longer available to new users");
# gemini-3.5-flash-lite is the working fallback while gemini-3.6-flash's quota is out.
GEMINI_MODEL = "gemini-3.5-flash-lite"


def classify_exception(exc: Exception) -> str | None:
    """Return "rate_limited"/"timeout" for a failure core.agent.graph should retry, or
    None to let it propagate as "api_error". Gemini has no equivalent of Groq's
    tool_use_failed refusal, so this never returns "invalid_output".

    ChatGoogleGenerativeAI re-raises a 429 as its own ModelRateLimitError rather than
    a genai ClientError subclass -- check that first, and keep the raw ClientError/
    ServerError check as a fallback for anything that bypasses the chat model layer.
    """
    if isinstance(exc, ModelRateLimitError):
        return "rate_limited"
    if isinstance(exc, genai_errors.ClientError) and exc.code == 429:
        return "rate_limited"
    if isinstance(exc, genai_errors.ServerError):
        return "timeout"
    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError)):
        return "timeout"
    return None


def _require_api_key(value: str | None) -> str:
    if not value:
        raise RuntimeError(
            "GEMINI_API_KEY is absent or empty. Define it in a .env file at the root of the "
            "project (see .env.example)."
        )
    return value


load_dotenv()
GEMINI_API_KEY = _require_api_key(os.getenv("GEMINI_API_KEY"))


def get_llm() -> ChatGoogleGenerativeAI:
    """Build a fresh chat model instance for one generate() call. max_retries=0: retrying
    what classify_exception() recognizes is core.agent.graph's job (shared across
    providers, bounded, and sleep-mockable in tests), not this SDK's own opaque policy.
    """
    return ChatGoogleGenerativeAI(model=GEMINI_MODEL, google_api_key=GEMINI_API_KEY, max_retries=0)
