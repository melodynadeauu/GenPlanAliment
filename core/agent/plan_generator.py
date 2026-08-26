"""Orchestrates one daily plan generation: load the day's activities and
preferences, run the deterministic calorie pipeline, build the prompts, and hand off
to llm_adapter.generate(). No error handling here -- llm_adapter.generate() already
never raises and encodes any failure in GenerationResult.error; main.py decides what
to display for success vs. error.
"""
from core.agent import llm_adapter, prompts
from core.agent.llm_adapter import GenerationResult
from core.models import ActivityEntry, Profile
from core.nutrition import (
    compute_bmr,
    compute_exercise_expenditure,
    compute_sedentary_base,
    compute_target_kcal,
    compute_tdee,
)
from core.tools.usda_tool import get_nutrition_tool, search_food_tool
from data.activity import store as activity_store
from data.preferences import store as preferences_store


def generate_daily_plan(profile: Profile, day: str) -> GenerationResult:
    """Generate a meal plan for `profile` on `day`.

    Loads today's activities and food preferences, computes the calorie target via
    the deterministic pipeline (BMR -> sedentary base -> + exercise -> TDEE -> goal
    adjustment), builds the system/user prompts, and returns whatever
    llm_adapter.generate() returns, unchanged.
    """
    activities = activity_store.get_activities(day)
    prefs = preferences_store.load_preferences()

    bmr = compute_bmr(profile)
    sedentary_base = compute_sedentary_base(bmr)
    exercise_kcal = compute_exercise_expenditure(
        [ActivityEntry.from_row(row) for row in activities], profile.weight_kg
    )
    tdee = compute_tdee(sedentary_base, exercise_kcal)
    target_kcal = compute_target_kcal(tdee, profile.goal)

    system_prompt = prompts.build_system_prompt()
    user_prompt = prompts.build_user_prompt(target_kcal, activities, prefs["likes"], prefs["dislikes"])

    return llm_adapter.generate(system_prompt, user_prompt, tools=[search_food_tool, get_nutrition_tool])
