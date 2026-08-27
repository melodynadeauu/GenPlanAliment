from core.nutrition import constants
from core.types import Goal

_GOAL_ADJUSTMENT_KCAL = {
    Goal.MAINTENANCE: constants.MAINTENANCE_ADJUSTMENT_KCAL,
    Goal.MUSCLE_GAIN: constants.MUSCLE_GAIN_SURPLUS_KCAL,
}


def compute_target_kcal(tdee_kcal: float, goal: Goal) -> float:
    """Daily calorie target.

    MAINTENANCE / MUSCLE_GAIN: TDEE + the fixed adjustment for `goal`.
    WEIGHT_LOSS: deficit capped at min(WEIGHT_LOSS_DEFICIT_KCAL,
    MAX_DEFICIT_FRACTION_OF_TDEE * tdee_kcal), then floored at CALORIE_FLOOR_KCAL.
    """
    if goal == Goal.WEIGHT_LOSS:
        deficit = min(
            constants.WEIGHT_LOSS_DEFICIT_KCAL,
            constants.MAX_DEFICIT_FRACTION_OF_TDEE * tdee_kcal,
        )
        return max(tdee_kcal - deficit, constants.CALORIE_FLOOR_KCAL)
    return tdee_kcal + _GOAL_ADJUSTMENT_KCAL[goal]
