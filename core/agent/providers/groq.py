"""Groq provider adapter: a LangChain ChatGroq instance plus the bit core.agent.graph
needs to translate this SDK's failures into the canonical error codes
GenerationResult carries. Secondary provider -- Gemini is primary, this is the
rate-limit fallback.
"""
import os

import groq
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from pydantic import SecretStr

# llama-3.3-70b-versatile no longer exists on this account; this is the closest
# available equivalent with confirmed tool-calling support.
GROQ_MODEL = "openai/gpt-oss-120b"


def classify_exception(exc: Exception) -> str | None:
    """Return "rate_limited"/"timeout" for a failure core.agent.graph should retry,
    "invalid_output" for one to report immediately without retrying, or None to let
    it propagate as "api_error". A forced tool_choice the model refuses surfaces as
    groq.BadRequestError with body["error"]["code"] == "tool_use_failed".
    """
    if isinstance(exc, groq.BadRequestError):
        if isinstance(exc.body, dict) and exc.body.get("error", {}).get("code") == "tool_use_failed":
            return "invalid_output"
        return None
    if isinstance(exc, groq.RateLimitError):
        return "rate_limited"
    if isinstance(exc, (groq.APITimeoutError, groq.APIConnectionError, groq.InternalServerError)):
        return "timeout"
    return None


def _require_api_key(value: str | None) -> str:
    if not value:
        raise RuntimeError(
            "GROQ_API_KEY is absent or empty. Define it in a .env file at the root of the "
            "project (see .env.example)."
        )
    return value


load_dotenv()
GROQ_API_KEY = _require_api_key(os.getenv("GROQ_API_KEY"))


def get_llm() -> ChatGroq:
    """Build a fresh chat model instance for one generate() call. max_retries=0: retrying
    what classify_exception() recognizes is core.agent.graph's job (shared across
    providers, bounded, and sleep-mockable in tests), not this SDK's own opaque policy.
    """
    return ChatGroq(model=GROQ_MODEL, api_key=SecretStr(GROQ_API_KEY), max_retries=0)
