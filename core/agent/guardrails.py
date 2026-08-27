"""Deterministic checks applied to a resolved plan before it reaches the user.
Never delegates these decisions to the LLM.
"""
import re

from core.agent.schemas import PlanFood

# Preferences JSON is user-editable, so it's a prompt-injection surface.
_MAX_ITEM_LENGTH = 60
_DISALLOWED_CHARS = re.compile(r"[\r\n\"'{}<>]")


def find_disliked_foods(foods: list[PlanFood], dislikes: list[str]) -> list[PlanFood]:
    """Foods whose description contains (case-insensitively) any dislike entry."""
    lowered_dislikes = [d.lower() for d in dislikes if d]
    return [
        food
        for food in foods
        if any(dislike in food.description.lower() for dislike in lowered_dislikes)
    ]


def sanitize_preference_items(items: list[str]) -> list[str]:
    """Strip control/quote/bracket characters, collapse whitespace, cap length, and
    drop empties -- before interpolating into a prompt.
    """
    cleaned = []
    for item in items:
        stripped = _DISALLOWED_CHARS.sub(" ", item).strip()
        stripped = " ".join(stripped.split())[:_MAX_ITEM_LENGTH]
        if stripped:
            cleaned.append(stripped)
    return cleaned
