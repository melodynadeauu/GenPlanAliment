"""Gemini provider adapter: a ChatGoogleGenerativeAI instance plus failure
classification for core.agent.graph. Retry/backoff lives in
core.agent.graph._invoke_with_retry.
"""
import os

import httpx
from dotenv import load_dotenv
from google.genai import errors as genai_errors
from langchain_core.exceptions import ModelRateLimitError
from langchain_google_genai import ChatGoogleGenerativeAI

# gemini-2.5-* is 404 on this account; gemini-3.5-flash-lite is the current
# working model.
GEMINI_MODEL = "gemini-3.5-flash-lite"


def classify_exception(exc: Exception) -> str | None:
    """Returns "rate_limited"/"timeout" for a retryable failure, else None
    ("api_error"). Never "invalid_output" (no Gemini equivalent to Groq's
    tool_use_failed).
    """
    if isinstance(exc, ModelRateLimitError):
        return "rate_limited"
    # Fallback for a 429 that bypasses ChatGoogleGenerativeAI's own re-raise.
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
    """Fresh chat model instance. max_retries=0: retries are core.agent.graph's
    job, not the SDK's.
    """
    return ChatGoogleGenerativeAI(model=GEMINI_MODEL, google_api_key=GEMINI_API_KEY, max_retries=0)
