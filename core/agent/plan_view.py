"""Turns a flat PlanPropose (core.agent.schemas) into the meals-grouped, kcal-enriched
dict ui.components.meal_plan / totals_row / guardrails_bar expect (see
fixtures.demo_plan.DEMO_PLAN for the target shape).

PlanFood only carries description/fdc_id/meal/grams -- no kcal or macros, since trusting
the LLM's own arithmetic would drift from ground truth. So this module re-looks-up each
food's macros_per_100g via get_nutrition_tool (already cached from generation, see
data.usda.cache) and computes kcal/protein deterministically, the same way
core.nutrition.energy computes everything else in the pipeline.

guardrails is [] unless `degraded` is set: evaluating deficit caps / excluded foods
happens upstream in core.agent.graph's validate_guardrails_node (G1/G2), which this
module doesn't own -- it only surfaces the resulting degraded flag as a warning entry.
"""
from core.agent import plan_generator
from core.agent.schemas import PlanPropose
from core.models import Profile
from core.tools.usda_tool import get_nutrition_tool
from core.types import MealType

MEAL_LABELS_FR = {
    MealType.BREAKFAST: "Déjeuner",
    MealType.LUNCH: "Dîner",
    MealType.DINNER: "Souper",
    MealType.SNACK: "Collation",
}

# Fixed display order -- independent of the order foods happen to arrive in PlanPropose.
MEAL_ORDER = [MealType.BREAKFAST, MealType.LUNCH, MealType.DINNER, MealType.SNACK]

_LOOKUP_FAILED_SOURCE = "estimation — FDC indisponible"


def generate_daily_plan_view(profile: Profile, day: str) -> tuple[dict | None, str | None]:
    """Compose plan_generator.generate_daily_plan() + build_plan_view() into the single
    call a presentation layer needs: (view, None) on success, or (None, error) on failure
    -- same two-outcome shape as GenerationResult, minus the PlanPropose/target_kcal
    domain objects a caller like app.py has no business knowing about.
    """
    result = plan_generator.generate_daily_plan(profile, day)
    if result.error:
        return None, result.error
    assert result.plan is not None
    assert result.target_kcal is not None
    return build_plan_view(result.plan, result.target_kcal, degraded=result.degraded), None


def build_plan_view(plan: PlanPropose, target_kcal: float, degraded: bool = False) -> dict:
    """Group `plan.foods` by meal (fixed order, FR labels) and enrich each with kcal
    computed from a fresh get_nutrition_tool lookup. Never raises: a food whose lookup
    fails is kept with kcal=0 and a "warn" status rather than dropped.

    `degraded` (from GenerationResult.degraded, set by core.agent.graph's G7 retry
    loop when it exhausts MAX_ATTEMPTS) surfaces as a "warn" guardrail entry rather
    than silently showing a non-conforming plan.
    """
    items_by_meal: dict[MealType, list[dict]] = {meal: [] for meal in MEAL_ORDER}
    total_kcal = 0.0
    total_protein_g = 0.0

    for food in plan.foods:
        item, kcal, protein_g = _build_item(food)
        items_by_meal[food.meal].append(item)
        total_kcal += kcal
        total_protein_g += protein_g

    meals = [
        {
            "name": MEAL_LABELS_FR[meal],
            "kcal": round(sum(item["kcal"] for item in items)),
            "items": items,
        }
        for meal in MEAL_ORDER
        if (items := items_by_meal[meal])
    ]

    guardrails = (
        [
            {
                "status": "warn",
                "message": "Plan non conforme après 2 tentatives — vérifiez le total et les aliments exclus.",
            }
        ]
        if degraded
        else []
    )

    return {
        "target_kcal": target_kcal,
        "total_kcal": round(total_kcal),
        "total_protein_g": round(total_protein_g),
        "meals": meals,
        "guardrails": guardrails,
    }


def _build_item(food) -> tuple[dict, float, float]:
    """One food -> (display item, kcal, protein_g). On a failed lookup, kcal/protein_g
    are 0 and the item is flagged "warn" rather than raising or being dropped.
    """
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
