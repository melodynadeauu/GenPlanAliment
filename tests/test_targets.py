"""Tests for core.nutrition.targets."""
import pytest

from core.nutrition import compute_target_kcal
from core.types import Goal


def test_weight_loss_target_is_tdee_minus_deficit():
    """WEIGHT_LOSS -> TDEE - 500 kcal (Mayo Clinic)."""
    assert compute_target_kcal(2500.0, Goal.WEIGHT_LOSS) == pytest.approx(2000.0)


def test_maintenance_target_equals_tdee():
    """MAINTENANCE -> no adjustment."""
    assert compute_target_kcal(2500.0, Goal.MAINTENANCE) == pytest.approx(2500.0)


def test_muscle_gain_target_is_tdee_plus_surplus():
    """MUSCLE_GAIN -> TDEE + 300 kcal (Built With Science)."""
    assert compute_target_kcal(2500.0, Goal.MUSCLE_GAIN) == pytest.approx(2800.0)
