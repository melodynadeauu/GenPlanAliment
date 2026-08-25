from core.nutrition import constants
from core.types import Goal

_GOAL_ADJUSTMENT_KCAL = {
    Goal.WEIGHT_LOSS: -constants.WEIGHT_LOSS_DEFICIT_KCAL,
    Goal.MAINTENANCE: constants.MAINTENANCE_ADJUSTMENT_KCAL,
    Goal.MUSCLE_GAIN: constants.MUSCLE_GAIN_SURPLUS_KCAL,
}


def compute_target_kcal(tdee_kcal: float, goal: Goal) -> float:
    """Daily calorie target: TDEE + the adjustment for `goal`."""
    return tdee_kcal + _GOAL_ADJUSTMENT_KCAL[goal]
