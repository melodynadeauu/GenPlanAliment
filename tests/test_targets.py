"""Tests for core.nutrition.targets."""
import pytest

from core.nutrition import compute_target_kcal, constants
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


def test_weight_loss_deficit_capped_at_500_when_tdee_is_high():
    # TDEE 2966 -> naive deficit 500 is < 25% of TDEE (741.5), so 500 applies unchanged.
    target = compute_target_kcal(2966.0, Goal.WEIGHT_LOSS)
    assert target == pytest.approx(2966.0 - 500.0)


def test_weight_loss_deficit_capped_at_25_percent_when_tdee_is_low():
    # TDEE 1800 -> 25% is 450, which is < the flat 500 deficit, so 450 applies instead
    # (and the result, 1350, still clears the calorie floor).
    target = compute_target_kcal(1800.0, Goal.WEIGHT_LOSS)
    assert target == pytest.approx(1800.0 - 450.0)


def test_weight_loss_target_never_drops_below_calorie_floor():
    # TDEE 1300 -> would-be target after capped deficit is below the floor, floor wins.
    target = compute_target_kcal(1300.0, Goal.WEIGHT_LOSS)
    assert target == pytest.approx(constants.CALORIE_FLOOR_KCAL)


def test_maintenance_and_muscle_gain_unaffected_by_floor_logic():
    assert compute_target_kcal(1000.0, Goal.MAINTENANCE) == pytest.approx(1000.0)
    assert compute_target_kcal(1000.0, Goal.MUSCLE_GAIN) == pytest.approx(1300.0)
