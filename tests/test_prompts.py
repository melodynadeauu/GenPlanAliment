"""Tests for core.agent.prompts."""
from core.agent.prompts import build_system_prompt


def test_system_prompt_forbids_medical_advice():
    prompt = build_system_prompt().lower()
    assert "not medical advice" in prompt or "not a medical" in prompt
    assert "professional" in prompt


def test_system_prompt_tells_the_llm_to_verify_its_total_before_submitting():
    prompt = build_system_prompt().lower()
    assert "compute_plan_total" in prompt
    assert "before" in prompt and "submit_plan" in prompt
