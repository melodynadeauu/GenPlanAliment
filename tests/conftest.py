"""Ensure test collection never hard-fails on a missing .env: every module under
core.agent imports core.agent.llm_adapter transitively, which requires these env vars
at import time. Real values (from a populated .env) always win; these are placeholders
so a fresh clone can still run tests that never touch an LLM or a real API key.
"""
import os

os.environ.setdefault("LLM_PROVIDER", "gemini")
os.environ.setdefault("GEMINI_API_KEY", "test-placeholder-key")
os.environ.setdefault("GROQ_API_KEY", "test-placeholder-key")
os.environ.setdefault("USDA_API_KEY", "test-placeholder-key")
