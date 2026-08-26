"""Gemini provider adapter: a LangChain ChatGoogleGenerativeAI instance plus the one bit
core.agent.graph needs to translate this SDK's own failures into the canonical error
codes GenerationResult can carry -- retry/backoff itself now lives once,
provider-agnostically, in core.agent.graph._invoke_with_retry.
"""
import os

import httpx
from dotenv import load_dotenv
from google.genai import errors as genai_errors
from langchain_core.exceptions import ModelRateLimitError
from langchain_google_genai import ChatGoogleGenerativeAI

# Verified live against this SDK/account on 2026-08-25: "gemini-2-flash" doesn't exist, and
# every Gemini 2.x flash model on this account is dead -- gemini-2.5-flash and
# gemini-2.5-flash-lite both 404 with "no longer available to new users", redirecting to
# gemini-3.6-flash (rate-limited) and gemini-3.5-flash-lite respectively. gemini-3.5-flash-lite
# is a genuinely separate model from gemini-3.6-flash (confirmed responding live), so it's used
# here as the working fallback while gemini-3.6-flash's quota is exhausted.
GEMINI_MODEL = "gemini-3.5-flash-lite"


def classify_exception(exc: Exception) -> str | None:
    """Return "rate_limited"/"timeout" for a failure core.agent.graph should retry, or
    None to let it propagate as "api_error". langchain-google-genai (the google-genai
    SDK, not the deprecated google-generativeai/google-api-core stack) raises
    google.genai.errors.ClientError/ServerError for every HTTP failure, with the status
    code on .code -- not a distinct exception class per status the way
    google.api_core.exceptions used to have, so the code itself is what's inspected here.
    Gemini has no equivalent of Groq's tool_use_failed refusal on a forced tool_choice,
    so this never returns "invalid_output".

    ChatGoogleGenerativeAI re-raises a 429 ClientError as its own GoogleRateLimitError
    (a langchain_core.exceptions.ModelRateLimitError), NOT a ClientError subclass --
    verified live against langchain-google-genai 4.3.5. Check the LangChain-classified
    type first; keep the raw genai_errors.ClientError check as a fallback for anything
    that bypasses the chat model layer.
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
