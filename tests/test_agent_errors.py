"""Tests for core.agent.errors: the canonical exceptions each provider adapter translates
its own SDK's failures into, so core.agent.llm_adapter never imports a provider SDK
directly."""
from core.agent.errors import LLMInvalidOutputError, LLMRateLimitedError, LLMTimeoutError


def test_errors_are_exception_subclasses():
    assert issubclass(LLMRateLimitedError, Exception)
    assert issubclass(LLMTimeoutError, Exception)
    assert issubclass(LLMInvalidOutputError, Exception)


def test_errors_are_distinct_from_each_other():
    assert not issubclass(LLMRateLimitedError, LLMTimeoutError)
    assert not issubclass(LLMTimeoutError, LLMInvalidOutputError)
    assert not issubclass(LLMInvalidOutputError, LLMRateLimitedError)
