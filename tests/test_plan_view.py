"""Tests for core.agent.plan_view: turning a flat PlanPropose into the meals-grouped,
kcal-enriched dict ui.components.meal_plan / totals_row / guardrails_bar expect
(see fixtures.demo_plan.DEMO_PLAN for the target shape).

get_nutrition_tool is monkeypatched on the plan_view module itself (not on
core.tools.usda_tool, where it's defined) -- same pattern as llm_adapter._provider in
test_llm_adapter.py: patch the name where it's looked up, not where it's declared.
"""
from core.agent import plan_generator, plan_view
from core.agent.llm_adapter import GenerationResult
from core.agent.schemas import PlanFood, PlanPropose
from core.models import Profile
from core.types import Goal, MealType

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
    monkeypatch.setattr(plan_view, "get_nutrition_tool", lambda fdc_id: APPLE_NUTRITION)
    plan = PlanPropose(
        foods=[PlanFood(description="Apple, raw", fdc_id="1", meal=MealType.SNACK, grams=200.0)]
    )

    view = plan_view.build_plan_view(plan, target_kcal=2000.0)

    assert view["target_kcal"] == 2000.0
    assert len(view["meals"]) == 1
    meal = view["meals"][0]
    assert meal["name"] == "Collation"
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
    monkeypatch.setattr(plan_view, "get_nutrition_tool", lambda fdc_id: NUTRITION_BY_FDC_ID[fdc_id])
    plan = PlanPropose(
        foods=[
            PlanFood(description="Apple, raw", fdc_id="1", meal=MealType.SNACK, grams=100.0),
            PlanFood(description="Chicken breast, grilled", fdc_id="2", meal=MealType.LUNCH, grams=100.0),
            PlanFood(description="Brown rice, cooked", fdc_id="3", meal=MealType.LUNCH, grams=100.0),
        ]
    )

    view = plan_view.build_plan_view(plan, target_kcal=2000.0)

    assert [meal["name"] for meal in view["meals"]] == ["Dîner", "Collation"]
    assert [item["food"] for item in view["meals"][0]["items"]] == [
        "Chicken breast, grilled",
        "Brown rice, cooked",
    ]


def test_build_plan_view_sums_item_kcal_into_meal_and_total_kcal(monkeypatch):
    monkeypatch.setattr(plan_view, "get_nutrition_tool", lambda fdc_id: NUTRITION_BY_FDC_ID[fdc_id])
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
    monkeypatch.setattr(plan_view, "get_nutrition_tool", lambda fdc_id: {"error": "not_found"})
    plan = PlanPropose(
        foods=[PlanFood(description="Mystery food", fdc_id="999", meal=MealType.DINNER, grams=100.0)]
    )

    view = plan_view.build_plan_view(plan, target_kcal=2000.0)

    item = view["meals"][0]["items"][0]
    assert item["kcal"] == 0
    assert item["source_status"] == "warn"
    assert item["source"] == "estimation — FDC indisponible"
    assert view["total_kcal"] == 0


def test_build_plan_view_omits_meals_with_no_foods(monkeypatch):
    monkeypatch.setattr(plan_view, "get_nutrition_tool", lambda fdc_id: APPLE_NUTRITION)
    plan = PlanPropose(
        foods=[PlanFood(description="Apple, raw", fdc_id="1", meal=MealType.BREAKFAST, grams=100.0)]
    )

    view = plan_view.build_plan_view(plan, target_kcal=2000.0)

    assert [meal["name"] for meal in view["meals"]] == ["Déjeuner"]


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
    monkeypatch.setattr(plan_view, "get_nutrition_tool", lambda fdc_id: APPLE_NUTRITION)

    view, error = plan_view.generate_daily_plan_view(PROFILE, "monday")

    assert error is None
    assert view == plan_view.build_plan_view(plan, target_kcal=2000.0)


def test_generate_daily_plan_view_returns_no_view_and_the_error_on_failure(monkeypatch):
    monkeypatch.setattr(
        plan_generator,
        "generate_daily_plan",
        lambda profile, day: GenerationResult(None, "timeout"),
    )

    view, error = plan_view.generate_daily_plan_view(PROFILE, "monday")

    assert view is None
    assert error == "timeout"
