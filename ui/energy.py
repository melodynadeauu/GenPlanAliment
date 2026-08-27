"""The calorie pipeline, previewed for the UI before any LLM call: the same
pure functions core.agent.plan_generator runs, so the target shows the moment
a day is selected. Read-only, no LLM, no network.
"""
from core.models import ActivityEntry, Profile
from core.nutrition import (
    compute_bmr,
    compute_exercise_expenditure,
    compute_sedentary_base,
    compute_target_kcal,
    compute_tdee,
)
from data.activity import store as activity_store

GOAL_LABEL = {
    "weight_loss": "Weight loss",
    "muscle_gain": "Muscle gain",
    "maintenance": "Maintenance",
}


def load_day_activities(day: str, week: list[dict]) -> list[dict]:
    """Activity rows for `day`: the database first, `week` as the fallback
    (keeps the demo working when meal_prep.db hasn't been seeded).
    """
    try:
        rows = activity_store.get_activities(day)
    except Exception:
        rows = []

    if rows:
        return rows

    entry = next((d for d in week if d["day"] == day), None)
    if not entry or not entry.get("activity"):
        return []
    return [
        {
            "activity": entry["activity"],
            "duration_minutes": entry["duration_minutes"],
            "intensity": entry["intensity"],
        }
    ]


def exercise_kcal(rows: list[dict], weight_kg: float) -> float:
    """kcal burned by `rows` (MET-based), 0.0 if the day is a rest day."""
    if not rows:
        return 0.0
    entries = [ActivityEntry.from_row(row) for row in rows]
    return compute_exercise_expenditure(entries, weight_kg)


def compute_energy(profile: Profile, rows: list[dict]) -> dict:
    """Every step of the target calculation, for display.

    Returns bmr / base / burn / tdee / adjustment / target, all kcal.
    """
    bmr = compute_bmr(profile)
    base = compute_sedentary_base(bmr)
    burn = exercise_kcal(rows, profile.weight_kg)
    tdee = compute_tdee(base, burn)
    target = compute_target_kcal(tdee, profile.goal)
    return {
        "bmr": bmr,
        "base": base,
        "burn": burn,
        "tdee": tdee,
        "adjustment": target - tdee,
        "target": target,
    }
