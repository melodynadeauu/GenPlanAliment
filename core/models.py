from dataclasses import dataclass

from core.types import Goal


@dataclass(frozen=True)
class Profile:
    """The user parameters that drive the calorie calculation."""

    age_years: int
    weight_kg: float
    height_cm: float
    goal: Goal
