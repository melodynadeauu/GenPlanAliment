"""Deterministic nutrition core: no I/O, no LLM, no UI."""
from core.nutrition.energy import (
    compute_bmr,
    compute_exercise_expenditure,
    compute_sedentary_base,
    compute_tdee,
)

__all__ = [
    "compute_bmr",
    "compute_exercise_expenditure",
    "compute_sedentary_base",
    "compute_tdee",
]
