"""Tests for core.nutrition.energy."""
import pytest

from core.models import Profile
from core.nutrition import compute_bmr
from core.types import Goal


def test_bmr_matches_case_study_profile():
    """45 years, 100 kg, 196 cm -> about 1922 kcal/day."""
    profile = Profile(age_years=45, weight_kg=100, height_cm=196, goal=Goal.WEIGHT_LOSS)

    bmr = compute_bmr(profile)

    assert bmr == pytest.approx(1922.0, abs=0.5)
