"""Turns a flat PlanPropose into the meals-grouped, kcal-enriched dict
ui.components.meal_plan / totals_row / guardrails_bar expect (see
fixtures.demo_plan.DEMO_PLAN for the target shape).

PlanFood carries no kcal/macros -- trusting the LLM's own arithmetic would drift
from ground truth, so this module re-looks up each food via get_nutrition_tool
(cache-warm from generation) and computes kcal/protein deterministically.
"""
from core.agent import plan_generator
from core.agent.schemas import PlanPropose
from core.models import Profile
from core.tools.usda_tool import get_nutrition_tool
from core.types import MealType

MEAL_LABELS = {
    MealType.BREAKFAST: "Breakfast",
    MealType.LUNCH: "Lunch",
    MealType.DINNER: "Dinner",
    MealType.SNACK: "Snack",
}

MEAL_ORDER = [MealType.BREAKFAST, MealType.LUNCH, MealType.DINNER, MealType.SNACK]

_LOOKUP_FAILED_SOURCE = "estimated (FDC unavailable)"


def generate_daily_plan_view(profile: Profile, day: str) -> tuple[dict | None, str | None]:
    """Generate + build a view in one call: (view, None) on success, (None, error)
    on failure -- so app.py never has to know about PlanPropose or target_kcal.
    """
    result = plan_generator.generate_daily_plan(profile, day)
    if result.error:
        return None, result.error
    assert result.plan is not None
    assert result.target_kcal is not None
    return (
        build_plan_view(result.plan, result.target_kcal, degraded=result.degraded, adjusted=result.adjusted),
        None,
    )


def build_plan_view(plan: PlanPropose, target_kcal: float, degraded: bool = False, adjusted: bool = False) -> dict:
    """Group `plan.foods` by meal and enrich each with a fresh kcal lookup. Never
    raises: a food whose lookup fails is kept with kcal=0 and a "warn" status.

    `degraded` (G7: the graph exhausted its guardrail-retry attempts) surfaces as a
    "warn" guardrail entry instead of silently showing a non-conforming plan.

    `adjusted` (G7 business-rule fallback: grams were rescaled to hit target_kcal
    instead of degrading) surfaces as a distinct, non-alarming "info" guardrail entry.
    Mutually exclusive with `degraded` by construction -- checked in that order anyway,
    `degraded` taking priority, so a caller passing both by mistake still gets a warning.
    """
    items_by_meal: dict[MealType, list[dict]] = {meal: [] for meal in MEAL_ORDER}
    total_kcal = 0.0
    total_protein_g = 0.0
    unresolved_names: list[str] = []

    for food in plan.foods:
        item, kcal, protein_g = _build_item(food)
        items_by_meal[food.meal].append(item)
        total_kcal += kcal
        total_protein_g += protein_g
        if item["source_status"] == "warn":
            unresolved_names.append(food.description)

    meals = [
        {
            "name": MEAL_LABELS[meal],
            "kcal": round(sum(item["kcal"] for item in items)),
            "items": items,
        }
        for meal in MEAL_ORDER
        if (items := items_by_meal[meal])
    ]

    guardrails = []
    if degraded:
        if unresolved_names:
            # G-exists caused (or contributed to) the degrade: name the ghost food(s)
            # instead of the generic message, so the warning is actionable.
            message = (
                f"Plan non-compliant after 2 attempts: {', '.join(unresolved_names)} "
                "could not be found in USDA and are shown as estimated."
            )
        else:
            message = "Plan non-compliant after 2 attempts. Check the total and excluded foods."
        guardrails = [{"status": "warn", "message": message}]
    elif adjusted:
        guardrails = [
            {
                "status": "info",
                "message": "Portions adjusted automatically to meet the calorie target.",
            }
        ]

    return {
        "target_kcal": target_kcal,
        "total_kcal": round(total_kcal),
        "total_protein_g": round(total_protein_g),
        "meals": meals,
        "guardrails": guardrails,
    }


def _build_item(food) -> tuple[dict, float, float]:
    """One food -> (display item, kcal, protein_g)."""
    nutrition = get_nutrition_tool.invoke({"fdc_id": food.fdc_id})

    if "error" in nutrition:
        return (
            {
                "food": food.description,
                "grams": food.grams,
                "kcal": 0,
                "source": _LOOKUP_FAILED_SOURCE,
                "source_status": "warn",
            },
            0.0,
            0.0,
        )

    macros = nutrition["macros_per_100g"]
    scale = food.grams / 100
    kcal = macros["kcal"] * scale
    protein_g = macros["protein_g"] * scale

    item = {
        "food": food.description,
        "grams": food.grams,
        "kcal": round(kcal),
        "source": f"FDC {food.fdc_id}",
        "source_status": "ok",
    }
    return item, kcal, protein_g
