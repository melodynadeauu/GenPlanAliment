"""Small pure translations between UI-facing values (French day labels, the
profile fixture dict) and the domain types core.agent.plan_generator expects.
"""
from core.models import Profile
from core.types import Goal, Weekday

# ui.components.top_bar / fixtures.demo_week key their days in French; the domain
# layer (core.types.Weekday, data.activity.store) uses English day names.
_UI_DAY_TO_WEEKDAY = {
    "lundi": Weekday.MONDAY,
    "mardi": Weekday.TUESDAY,
    "mercredi": Weekday.WEDNESDAY,
    "jeudi": Weekday.THURSDAY,
    "vendredi": Weekday.FRIDAY,
    "samedi": Weekday.SATURDAY,
    "dimanche": Weekday.SUNDAY,
}

# The sidebar's goal selectbox (see ui.components.sidebar_profile) stores its
# value as the French label shown to the user, not the Goal enum value.
_GOAL_LABEL_TO_GOAL = {
    "Perte de poids": Goal.WEIGHT_LOSS,
    "Prise de muscle": Goal.MUSCLE_GAIN,
    "Maintien": Goal.MAINTENANCE,
}

def weekday_from_ui_day(day: str) -> str:
    """Translate a French UI day name (e.g. "mercredi") to the English day
    string plan_generator.generate_daily_plan expects (e.g. "wednesday").
    """
    try:
        return _UI_DAY_TO_WEEKDAY[day].value
    except KeyError:
        raise ValueError(f"Unknown UI day name: {day!r}") from None


def profile_from_dict(profile: dict) -> Profile:
    """Build a core.models.Profile from a profile dict shaped like
    fixtures.demo_profile.DEMO_PROFILE (age, weight_kg, height_cm, goal label) —
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
