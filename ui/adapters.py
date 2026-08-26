"""Small pure translations between UI-facing values and the domain types
core.agent.plan_generator expects.
"""
from core.models import Profile
from core.types import Goal, Weekday

# The sidebar's goal selectbox (ui.components.sidebar_profile) stores its value as
# the display label shown to the user, not the Goal enum value.
_GOAL_LABEL_TO_GOAL = {
    "Weight loss": Goal.WEIGHT_LOSS,
    "Muscle gain": Goal.MUSCLE_GAIN,
    "Maintenance": Goal.MAINTENANCE,
}


def weekday_from_ui_day(day: str) -> str:
    """Validate a UI day name against Weekday and return its value -- the day keys
    used across the UI (ui.components.top_bar, fixtures.demo_week) are already the
    English Weekday values, so this just confirms `day` is a real one.
    """
    try:
        return Weekday(day).value
    except ValueError:
        raise ValueError(f"Unknown UI day name: {day!r}") from None


def profile_from_dict(profile: dict) -> Profile:
    """Build a core.models.Profile from a profile dict shaped like
    fixtures.demo_profile.DEMO_PROFILE (age, weight_kg, height_cm, goal label) --
    in practice the current values from the sidebar's profile fields.
    """
    try:
        goal = _GOAL_LABEL_TO_GOAL[profile["goal"]]
    except KeyError:
        raise ValueError(f"Unknown goal label: {profile['goal']!r}") from None

    return Profile(
        age_years=profile["age"],
        weight_kg=profile["weight_kg"],
        height_cm=profile["height_cm"],
        goal=goal,
    )
