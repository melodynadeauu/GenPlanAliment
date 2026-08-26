"""Tests for core.agent.schemas: the structured output shape an LLM must fill in."""
import pytest
from pydantic import ValidationError

from core.agent.schemas import PlanFood, PlanPropose


def test_plan_food_holds_description_fdc_id_and_grams():
    food = PlanFood(description="CHICKEN GRAVY, CHICKEN", fdc_id="2620254", grams=150.0)

    assert food.description == "CHICKEN GRAVY, CHICKEN"
    assert food.fdc_id == "2620254"
    assert food.grams == 150.0


def test_plan_food_requires_all_three_fields():
    with pytest.raises(ValidationError):
        PlanFood(description="CHICKEN GRAVY, CHICKEN", fdc_id="2620254")  # pyright: ignore[reportCallIssue]


def test_plan_propose_holds_a_list_of_plan_food():
    propose = PlanPropose(
        foods=[
            PlanFood(description="CHICKEN GRAVY, CHICKEN", fdc_id="2620254", grams=150.0),
            PlanFood(description="Apple, raw", fdc_id="1750340", grams=182.0),
        ]
    )

    assert len(propose.foods) == 2
    assert all(isinstance(food, PlanFood) for food in propose.foods)


def test_plan_propose_accepts_empty_food_list():
    assert PlanPropose(foods=[]).foods == []


def test_plan_food_coerces_int_fdc_id_to_str():
    food = PlanFood(description="x", fdc_id=2620254, grams=100.0)  # pyright: ignore[reportArgumentType]

    assert food.fdc_id == "2620254"
    assert isinstance(food.fdc_id, str)


def test_plan_food_leaves_string_fdc_id_unchanged():
    food = PlanFood(description="x", fdc_id="2620254", grams=100.0)

    assert food.fdc_id == "2620254"


def test_plan_food_coerces_float_fdc_id_to_str():
    """Verified live against gemini-3.5-flash-lite on 2026-08-25: it echoes fdc_id back as
    a float (171287.0), not an int -- the ".0" must be dropped, not just stringified."""
    food = PlanFood(description="x", fdc_id=171287.0, grams=100.0)  # pyright: ignore[reportArgumentType]

    assert food.fdc_id == "171287"
    assert isinstance(food.fdc_id, str)
