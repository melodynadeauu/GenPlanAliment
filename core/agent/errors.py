"""Canonical exceptions a provider adapter (core.agent.providers.*) raises to report an
unrecoverable failure for one LLM call -- core.agent.llm_adapter catches these instead of
any provider SDK's own exception types, so the loop itself never imports google-generativeai
or groq.
"""


class LLMRateLimitedError(Exception):
    """The provider's rate limit was hit and retries were exhausted."""


class LLMTimeoutError(Exception):
    """The provider timed out or returned a transient server error, and retries were
    exhausted."""


class LLMInvalidOutputError(Exception):
    """The provider produced output that doesn't satisfy the requested structured output
    (e.g. a forced tool call the model refused to make)."""
