"""Pydantic schemas for the agent's structured output: the shape an LLM must fill in
when proposing a meal plan, validated at the boundary instead of trusted as-is.
"""
from pydantic import BaseModel, Field


class PlanFood(BaseModel):
    """One food item in a proposed plan."""

    description: str
    fdc_id: str
    grams: float = Field(
        description=(
            "The actual portion consumed, in grams. Independent of the 100g scale that "
            "core.tools.usda_tool.get_nutrition_tool's macros_per_100g is expressed in -- "
        )
    )


class PlanPropose(BaseModel):
    """A proposed meal plan: the list of foods that make it up."""

    foods: list[PlanFood]
