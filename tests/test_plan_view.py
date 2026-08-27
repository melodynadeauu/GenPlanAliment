"""Tests for core.agent.plan_view: turning a flat PlanPropose into the meals-grouped,
kcal-enriched dict ui.components.meal_plan / totals_row / guardrails_bar expect
(see fixtures.demo_plan.DEMO_PLAN for the target shape).

get_nutrition_tool is monkeypatched on the plan_view module itself (not on
core.tools.usda_tool, where it's defined) -- same pattern as llm_adapter.agent_graph.build_graph
in test_llm_adapter.py: patch the name where it's looked up, not where it's declared.
"""
from core.agent import plan_generator, plan_view
from core.agent.llm_adapter import GenerationResult
from core.agent.schemas import PlanFood, PlanPropose
from core.models import Profile
from core.types import Goal, MealType


class _FakeNutritionTool:
    """Stands in for the StructuredTool get_nutrition_tool becomes after core.tools.usda_tool
    adds @tool (see tests/test_usda_tool.py) -- plan_view.py now calls
    get_nutrition_tool.invoke({"fdc_id": ...}), not get_nutrition_tool(fdc_id) directly."""

    def __init__(self, fn):
        self._fn = fn

    def invoke(self, args):
        return self._fn(args["fdc_id"])


PROFILE = Profile(age_years=30, weight_kg=70.0, height_cm=175.0, goal=Goal.MAINTENANCE)

APPLE_NUTRITION = {
    "fdc_id": 1,
    "description": "Apple, raw",
    "macros_per_100g": {"kcal": 52.0, "protein_g": 0.3, "fat_g": 0.2, "carbs_g": 14.0},
}

CHICKEN_NUTRITION = {
    "fdc_id": 2,
    "description": "Chicken breast, grilled",
    "macros_per_100g": {"kcal": 165.0, "protein_g": 31.0, "fat_g": 3.6, "carbs_g": 0.0},
}

RICE_NUTRITION = {
    "fdc_id": 3,
    "description": "Brown rice, cooked",
    "macros_per_100g": {"kcal": 112.0, "protein_g": 2.3, "fat_g": 0.9, "carbs_g": 24.0},
}

NUTRITION_BY_FDC_ID = {"1": APPLE_NUTRITION, "2": CHICKEN_NUTRITION, "3": RICE_NUTRITION}


def test_build_plan_view_places_a_single_food_under_its_meal_with_computed_kcal(monkeypatch):
    monkeypatch.setattr(plan_view, "get_nutrition_tool", _FakeNutritionTool(lambda fdc_id: APPLE_NUTRITION))
    plan = PlanPropose(
        foods=[PlanFood(description="Apple, raw", fdc_id="1", meal=MealType.SNACK, grams=200.0)]
    )

    view = plan_view.build_plan_view(plan, target_kcal=2000.0)

    assert view["target_kcal"] == 2000.0
    assert len(view["meals"]) == 1
    meal = view["meals"][0]
    assert meal["name"] == "Snack"
    assert meal["items"] == [
        {
            "food": "Apple, raw",
            "grams": 200.0,
            "kcal": 104,
            "source": "FDC 1",
            "source_status": "ok",
        }
    ]


def test_build_plan_view_orders_meals_breakfast_to_snack_regardless_of_input_order(monkeypatch):
    monkeypatch.setattr(plan_view, "get_nutrition_tool", _FakeNutritionTool(lambda fdc_id: NUTRITION_BY_FDC_ID[fdc_id]))
    plan = PlanPropose(
        foods=[
            PlanFood(description="Apple, raw", fdc_id="1", meal=MealType.SNACK, grams=100.0),
            PlanFood(description="Chicken breast, grilled", fdc_id="2", meal=MealType.LUNCH, grams=100.0),
            PlanFood(description="Brown rice, cooked", fdc_id="3", meal=MealType.LUNCH, grams=100.0),
        ]
    )

    view = plan_view.build_plan_view(plan, target_kcal=2000.0)

    assert [meal["name"] for meal in view["meals"]] == ["Lunch", "Snack"]
    assert [item["food"] for item in view["meals"][0]["items"]] == [
        "Chicken breast, grilled",
        "Brown rice, cooked",
    ]


def test_build_plan_view_sums_item_kcal_into_meal_and_total_kcal(monkeypatch):
    monkeypatch.setattr(plan_view, "get_nutrition_tool", _FakeNutritionTool(lambda fdc_id: NUTRITION_BY_FDC_ID[fdc_id]))
    plan = PlanPropose(
        foods=[
            PlanFood(description="Chicken breast, grilled", fdc_id="2", meal=MealType.LUNCH, grams=100.0),
            PlanFood(description="Brown rice, cooked", fdc_id="3", meal=MealType.LUNCH, grams=100.0),
        ]
    )

    view = plan_view.build_plan_view(plan, target_kcal=2000.0)

    assert view["meals"][0]["kcal"] == 277  # round(165 + 112)
    assert view["total_kcal"] == 277
    assert view["total_protein_g"] == 33  # round(31.0 + 2.3)


def test_build_plan_view_falls_back_to_estimation_when_nutrition_lookup_fails(monkeypatch):
    monkeypatch.setattr(plan_view, "get_nutrition_tool", _FakeNutritionTool(lambda fdc_id: {"error": "not_found"}))
    plan = PlanPropose(
        foods=[PlanFood(description="Mystery food", fdc_id="999", meal=MealType.DINNER, grams=100.0)]
    )

    view = plan_view.build_plan_view(plan, target_kcal=2000.0)

    item = view["meals"][0]["items"][0]
    assert item["kcal"] == 0
    assert item["source_status"] == "warn"
    assert item["source"] == "estimated — FDC unavailable"
    assert view["total_kcal"] == 0


def test_build_plan_view_omits_meals_with_no_foods(monkeypatch):
    monkeypatch.setattr(plan_view, "get_nutrition_tool", _FakeNutritionTool(lambda fdc_id: APPLE_NUTRITION))
    plan = PlanPropose(
        foods=[PlanFood(description="Apple, raw", fdc_id="1", meal=MealType.BREAKFAST, grams=100.0)]
    )

    view = plan_view.build_plan_view(plan, target_kcal=2000.0)

    assert [meal["name"] for meal in view["meals"]] == ["Breakfast"]


def test_build_plan_view_passes_target_kcal_through_and_returns_empty_guardrails():
    plan = PlanPropose(foods=[])

    view = plan_view.build_plan_view(plan, target_kcal=1806.0)

    assert view["target_kcal"] == 1806.0
    assert view["meals"] == []
    assert view["guardrails"] == []
    assert view["total_kcal"] == 0
    assert view["total_protein_g"] == 0


# --- generate_daily_plan_view (composes plan_generator.generate_daily_plan + build_plan_view,
# so app.py has a single call and no knowledge of PlanPropose/target_kcal) ---


def test_generate_daily_plan_view_returns_the_built_view_on_success(monkeypatch):
    plan = PlanPropose(
        foods=[PlanFood(description="Apple, raw", fdc_id="1", meal=MealType.SNACK, grams=200.0)]
    )
    monkeypatch.setattr(
        plan_generator,
        "generate_daily_plan",
        lambda profile, day: GenerationResult(plan, None, target_kcal=2000.0),
    )
    monkeypatch.setattr(plan_view, "get_nutrition_tool", _FakeNutritionTool(lambda fdc_id: APPLE_NUTRITION))

    view, error = plan_view.generate_daily_plan_view(PROFILE, "monday")

    assert error is None
    assert view == plan_view.build_plan_view(plan, target_kcal=2000.0)


def test_build_plan_view_flags_degraded_plan_with_a_warning_guardrail(monkeypatch):
    monkeypatch.setattr(plan_view, "get_nutrition_tool", _FakeNutritionTool(lambda fdc_id: APPLE_NUTRITION))
    plan = PlanPropose(foods=[PlanFood(description="Apple, raw", fdc_id="1", meal=MealType.SNACK, grams=100.0)])

    view = plan_view.build_plan_view(plan, target_kcal=2000.0, degraded=True)

    assert len(view["guardrails"]) == 1
    assert view["guardrails"][0]["status"] == "warn"


def test_build_plan_view_conforming_plan_has_no_guardrail_warnings(monkeypatch):
    monkeypatch.setattr(plan_view, "get_nutrition_tool", _FakeNutritionTool(lambda fdc_id: APPLE_NUTRITION))
    plan = PlanPropose(foods=[PlanFood(description="Apple, raw", fdc_id="1", meal=MealType.SNACK, grams=100.0)])

    view = plan_view.build_plan_view(plan, target_kcal=2000.0)

    assert view["guardrails"] == []


def test_generate_daily_plan_view_passes_degraded_through(monkeypatch):
    plan = PlanPropose(foods=[])
    monkeypatch.setattr(
        plan_generator,
        "generate_daily_plan",
        lambda profile, day: GenerationResult(plan, None, target_kcal=2000.0, degraded=True),
    )

    view, error = plan_view.generate_daily_plan_view(PROFILE, "monday")

    assert error is None
    assert len(view["guardrails"]) == 1


def test_build_plan_view_names_the_unresolved_food_in_the_degraded_banner(monkeypatch):
    """G-exists: when degrade was caused by a ghost fdc_id, the banner should name it
    instead of showing the generic 'check the total and excluded foods' message."""

    def lookup(fdc_id):
        return {"error": "not_found"} if fdc_id == "999" else APPLE_NUTRITION

    monkeypatch.setattr(plan_view, "get_nutrition_tool", _FakeNutritionTool(lookup))
    plan = PlanPropose(
        foods=[
            PlanFood(description="Apple, raw", fdc_id="1", meal=MealType.SNACK, grams=100.0),
            PlanFood(description="Mystery food", fdc_id="999", meal=MealType.DINNER, grams=100.0),
        ]
    )

    view = plan_view.build_plan_view(plan, target_kcal=2000.0, degraded=True)

    assert len(view["guardrails"]) == 1
    assert "Mystery food" in view["guardrails"][0]["message"]
    assert view["guardrails"][0]["status"] == "warn"


def test_build_plan_view_keeps_the_generic_banner_when_degraded_without_unresolved_foods(monkeypatch):
    monkeypatch.setattr(plan_view, "get_nutrition_tool", _FakeNutritionTool(lambda fdc_id: APPLE_NUTRITION))
    plan = PlanPropose(foods=[PlanFood(description="Apple, raw", fdc_id="1", meal=MealType.SNACK, grams=100.0)])

    view = plan_view.build_plan_view(plan, target_kcal=2000.0, degraded=True)

    assert view["guardrails"] == [
        {"status": "warn", "message": "Plan non-compliant after 2 attempts — check the total and excluded foods."}
    ]


def test_generate_daily_plan_view_returns_no_view_and_the_error_on_failure(monkeypatch):
    monkeypatch.setattr(
        plan_generator,
        "generate_daily_plan",
        lambda profile, day: GenerationResult(None, "timeout"),
    )

    view, error = plan_view.generate_daily_plan_view(PROFILE, "monday")

    assert view is None
    assert error == "timeout"
