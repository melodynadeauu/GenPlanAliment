"""Pydantic schemas for the agent's structured output: the shape an LLM must fill in
when proposing a meal plan, validated at the boundary instead of trusted as-is.
"""
from pydantic import BaseModel, Field, field_validator
import core.types as types


class PlanFood(BaseModel):
    """One food item in a proposed plan."""

    description: str
    fdc_id: str
    meal: types.MealType = Field(description="Which meal this food belongs to.")
    grams: float = Field(
        description=(
            "The actual portion consumed, in grams. Independent of the 100g scale that "
            "core.tools.usda_tool.get_nutrition_tool's macros_per_100g is expressed in -- "
            "not itself a unit to convert, it's the multiplier applied to that per-100g figure."
        )
    )

    @field_validator("fdc_id", mode="before")
    @classmethod
    def _coerce_fdc_id_to_str(cls, value):
        """Defend against the LLM echoing USDA's integer fdcId (see data/usda/client.py)
        back unquoted -- pydantic v2 doesn't coerce int/float -> str by default. Some models
        (e.g. gemini-3.5-flash-lite, verified live on 2026-08-25) echo it as a float
        (171287.0) instead of an int, so the ".0" must be dropped too, not just stringified.
        """
        if isinstance(value, int):
            return str(value)
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return value


class PlanPropose(BaseModel):
    """A proposed meal plan: the list of foods that make it up."""

    foods: list[PlanFood]
