"""Canonical exceptions a provider adapter raises for one LLM call failure.
core.agent.graph catches these instead of any provider SDK's own types.
"""


class LLMRateLimitedError(Exception):
    """The provider's rate limit was hit and retries were exhausted."""


class LLMTimeoutError(Exception):
    """The provider timed out or returned a transient server error, and retries were
    exhausted."""


class LLMInvalidOutputError(Exception):
    """The provider produced output that doesn't satisfy the requested structured output
    (e.g. a forced tool call the model refused to make)."""
