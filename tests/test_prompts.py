"""Tests for core.agent.prompts."""
from core.agent.prompts import build_system_prompt


def test_system_prompt_forbids_medical_advice():
    prompt = build_system_prompt().lower()
    assert "not medical advice" in prompt or "not a medical" in prompt
    assert "professional" in prompt
