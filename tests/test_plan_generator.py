"""Tests for core.agent.plan_generator: orchestration of one daily plan generation.
data.activity.store / data.preferences.store are monkeypatched so no real DB/file is
touched; llm_adapter.generate is monkeypatched so no real provider is called.
"""
from core.agent import llm_adapter, plan_generator, prompts
from core.agent.schemas import PlanPropose
from core.models import Profile
from core.types import Goal
from data.activity import store as activity_store
from data.preferences import store as preferences_store

PROFILE = Profile(age_years=30, weight_kg=70.0, height_cm=175.0, goal=Goal.MAINTENANCE)


def _stub_stores(monkeypatch, activities=None):
    monkeypatch.setattr(activity_store, "get_activities", lambda day: activities or [])
    monkeypatch.setattr(preferences_store, "load_preferences", lambda: {"likes": [], "dislikes": []})


def test_generate_daily_plan_returns_the_same_target_kcal_used_to_build_the_prompt(monkeypatch):
    """target_kcal is computed once, from the deterministic pipeline -- the value handed
    to the LLM in the prompt and the value returned on GenerationResult must never drift
    apart, so assert they're literally the same number rather than recomputing it here.
    """
    _stub_stores(monkeypatch)
    plan = PlanPropose(foods=[])
    monkeypatch.setattr(llm_adapter, "generate", lambda *a, **k: llm_adapter.GenerationResult(plan, None))

    captured = {}
    original_build_user_prompt = prompts.build_user_prompt

    def spy_build_user_prompt(target_kcal, *args, **kwargs):
        captured["target_kcal"] = target_kcal
        return original_build_user_prompt(target_kcal, *args, **kwargs)

    monkeypatch.setattr(prompts, "build_user_prompt", spy_build_user_prompt)

    result = plan_generator.generate_daily_plan(PROFILE, "monday")

    assert captured["target_kcal"] is not None
    assert result.target_kcal == captured["target_kcal"]


def test_generate_daily_plan_preserves_plan_and_error_from_llm_adapter(monkeypatch):
    _stub_stores(monkeypatch)
    plan = PlanPropose(foods=[])
    monkeypatch.setattr(llm_adapter, "generate", lambda *a, **k: llm_adapter.GenerationResult(plan, None))

    result = plan_generator.generate_daily_plan(PROFILE, "monday")

    assert result.plan is plan
    assert result.error is None


def test_generate_daily_plan_preserves_error_from_llm_adapter(monkeypatch):
    _stub_stores(monkeypatch)
    monkeypatch.setattr(
        llm_adapter, "generate", lambda *a, **k: llm_adapter.GenerationResult(None, "timeout")
    )

    result = plan_generator.generate_daily_plan(PROFILE, "monday")

    assert result.plan is None
    assert result.error == "timeout"
