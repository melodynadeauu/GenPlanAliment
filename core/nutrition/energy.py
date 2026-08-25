from typing import Sequence

from core.models import ActivityEntry, Profile
from core.nutrition import constants
from data.activity.met_table import get_met


def compute_bmr(profile: Profile) -> float:
    """Return the basal metabolic rate in kcal/day (Mifflin-St Jeor, 1990).

    Uses a sex-neutral constant.
    """
    return (
        constants.MIFFLIN_WEIGHT_COEF * profile.weight_kg
        + constants.MIFFLIN_HEIGHT_COEF * profile.height_cm
        - constants.MIFFLIN_AGE_COEF * profile.age_years
        + constants.MIFFLIN_SEX_NEUTRAL_CONSTANT
    )


def compute_sedentary_base(bmr_kcal: float) -> float:
    """Sedentary energy base: BMR x SEDENTARY_ACTIVITY_FACTOR."""
    return bmr_kcal * constants.SEDENTARY_ACTIVITY_FACTOR


def compute_activity_burn(activity: ActivityEntry, weight_kg: float) -> float:
    """kcal burned by one activity: (MET x KCAL_PER_MINUTE_MET_COEF x weight_kg
    / KCAL_PER_MINUTE_DIVISOR) x duration_minutes.

    Source: https://howdyhealth.tamu.edu/use-metabolic-equivalents-mets-to-calculate-calories-burned/
    """
    met = get_met(activity.activity, activity.intensity)
    kcal_per_minute = (met * constants.KCAL_PER_MINUTE_MET_COEF * weight_kg) / constants.KCAL_PER_MINUTE_DIVISOR
    return kcal_per_minute * activity.duration_minutes


def compute_exercise_expenditure(activities: Sequence[ActivityEntry], weight_kg: float) -> float:
    """Sum every activity of the day."""
    return sum(compute_activity_burn(activity, weight_kg) for activity in activities)


def compute_tdee(sedentary_base_kcal: float, exercise_kcal: float) -> float:
    """Total daily energy expenditure: sedentary base + exercise."""
    return sedentary_base_kcal + exercise_kcal
