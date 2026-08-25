from core.models import Profile
from core.nutrition import constants


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
