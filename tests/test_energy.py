"""Tests for core.nutrition.energy."""
import pytest

from core.models import ActivityEntry, Profile
from core.nutrition import compute_bmr, compute_exercise_expenditure, compute_sedentary_base, compute_tdee
from core.types import Goal, Intensity


def test_bmr_matches_case_study_profile():
    """45 years, 100 kg, 196 cm -> about 1922 kcal/day."""
    profile = Profile(age_years=45, weight_kg=100, height_cm=196, goal=Goal.WEIGHT_LOSS)

    bmr = compute_bmr(profile)

    assert bmr == pytest.approx(1922.0, abs=0.5)


def test_rest_day_has_zero_exercise():
    """No activity scheduled -> zero exercise kcal, TDEE == sedentary base."""
    profile = Profile(age_years=45, weight_kg=100, height_cm=196, goal=Goal.WEIGHT_LOSS)
    sedentary_base = compute_sedentary_base(compute_bmr(profile))

    exercise_kcal = compute_exercise_expenditure([], profile.weight_kg)

    assert exercise_kcal == 0.0
    assert compute_tdee(sedentary_base, exercise_kcal) == pytest.approx(sedentary_base, abs=0.5)


def test_activity_burn_matches_met_formula():
    """kcal/min = (MET x 3.5 x weight_kg) / 200; total = kcal/min x duration.

    Source: https://howdyhealth.tamu.edu/use-metabolic-equivalents-mets-to-calculate-calories-burned/
    """
    activities = [ActivityEntry(activity="walk", duration_minutes=60, intensity=Intensity.MODERATE)]

    exercise_kcal = compute_exercise_expenditure(activities, weight_kg=100)

    # walk / MODERATE -> MET 3.8
    kcal_per_minute = (3.8 * 3.5 * 100) / 200
    assert exercise_kcal == pytest.approx(kcal_per_minute * 60)


def test_multiple_activities_are_summed():
    """Two activities the same day -> their kcal add up."""
    activities = [
        ActivityEntry(activity="walk", duration_minutes=30, intensity=Intensity.LOW),
        ActivityEntry(activity="running", duration_minutes=30, intensity=Intensity.MODERATE),
    ]

    exercise_kcal = compute_exercise_expenditure(activities, weight_kg=100)

    walk_kcal = ((2.8 * 3.5 * 100) / 200) * 30
    run_kcal = ((10.5 * 3.5 * 100) / 200) * 30
    assert exercise_kcal == pytest.approx(walk_kcal + run_kcal)


def test_activity_over_24_hours_is_rejected():
    """An activity entry longer than 24h can't be constructed."""
    with pytest.raises(ValueError):
        ActivityEntry(activity="running", duration_minutes=1441, intensity=Intensity.LOW)
