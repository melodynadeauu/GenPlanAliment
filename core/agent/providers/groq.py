"""Groq provider adapter: a ChatGroq instance plus failure classification for
core.agent.graph. Secondary provider; Gemini is primary.
"""
import os

import groq
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from pydantic import SecretStr

# llama-3.3-70b-versatile no longer exists on this account; closest equivalent
# with tool-calling support.
GROQ_MODEL = "openai/gpt-oss-120b"


def classify_exception(exc: Exception) -> str | None:
    """Returns "rate_limited"/"timeout"/"invalid_output", or None ("api_error").
    A refused forced tool_choice surfaces as groq.BadRequestError with
    body["error"]["code"] == "tool_use_failed".
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
    """Fresh chat model instance. max_retries=0: retries are core.agent.graph's
    job, not the SDK's.
    """
    return ChatGroq(model=GROQ_MODEL, api_key=SecretStr(GROQ_API_KEY), max_retries=0)
