"""Prompt text for the LLM: fixed instructions (build_system_prompt) plus
per-request facts (build_user_prompt). Pure string-building, kept separate
from core.agent.llm_adapter.
"""


def build_system_prompt() -> str:
    """Fixed instructions establishing the LLM's role, its tool-calling contract, and
    how it must end the conversation."""
    return (
        "You are an assistant that generates a daily meal plan. "
        "The plan must meet a given calorie target and strictly exclude any "
        "food items listed in the user's dislikes.\n"
        "\n"
        "For each food item you consider adding to the plan:\n"
        "1. Use search_food_tool to find its fdc_id -- never guess a "
        "fdc_id, it must always come from a search_food_tool result.\n"
        "2. Use get_nutrition_tool with this fdc_id to get its "
        "macros_per_100g before including the food in the plan.\n"
        "\n"
        "3. Assign the food to one of these meals: breakfast, lunch, dinner, snack.\n"
        "\n"
        "Distribute foods across all four meals -- don't put everything in one meal.\n"
        "Adjust the `grams` field of each food item in the plan so that the total "
        "kcal of all foods approaches the calorie target, within a "
        "tolerance of ±10% around the target.\n"
        "\n"
        "Before calling submit_plan, call compute_plan_total with your draft foods "
        "to check the true total kcal. Don't rely on your own arithmetic. If it's "
        "off target, adjust the grams and check again.\n"
        "\n"
        "This is not medical advice and you are not a medical professional. Never "
        "suggest medical treatment, diagnose a condition, or recommend a calorie "
        "target different from the one given -- the target is fixed and provided "
        "to you, not something you decide.\n"
        "\n"
        "You must OBLIGATORILY end by calling the submit_plan tool with the complete plan "
        "-- never respond in plain text."
    )


def build_user_prompt(
    target_kcal: float,
    activities: list[dict],
    likes: list[str],
    dislikes: list[str],
) -> str:
    """The concrete facts for this request: rounded kcal target, today's activities, and the likes/dislikes to steer food choices."""
    if activities:
        activities_block = "\n".join(
            f"- {activity['activity']} : {activity['duration_minutes']} min, "
            f"intensity {activity['intensity']}"
            for activity in activities
        )
    else:
        activities_block = "no activities planned"

    likes_block = ", ".join(likes) if likes else "none"
    dislikes_block = ", ".join(dislikes) if dislikes else "none"

    return (
        f"target calorie for the day: {round(target_kcal)} kcal.\n"
        "\n"
        "Activities planned for today:\n"
        f"{activities_block}\n"
        "\n"
        f"foods to favor (likes) : {likes_block}.\n"
        f"foods to exclude strictly (dislikes) : {dislikes_block}."
    )
