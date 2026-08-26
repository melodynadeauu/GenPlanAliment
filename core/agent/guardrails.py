"""Deterministic, Python-only checks applied to a resolved plan before it can reach
the user (Dossier de défense G2/G6). Never delegates an exclusion or a sanitization
decision to the LLM -- see D6/D9.
"""
import re

from core.agent.schemas import PlanFood

# G6: strip anything that isn't plain food-name text before it goes into a prompt --
# the preferences JSON is user-editable from the UI, so it's an injection surface.
_MAX_ITEM_LENGTH = 60
_DISALLOWED_CHARS = re.compile(r"[\r\n\"'{}<>]")


def find_disliked_foods(foods: list[PlanFood], dislikes: list[str]) -> list[PlanFood]:
    """Return every food in `foods` whose description contains (case-insensitively)
    any entry of `dislikes`. Never delegated to the LLM: a plan that violates this is
    caught here regardless of what the prompt asked for.
    """
    lowered_dislikes = [d.lower() for d in dislikes if d]
    return [
        food
        for food in foods
        if any(dislike in food.description.lower() for dislike in lowered_dislikes)
    ]


def sanitize_preference_items(items: list[str]) -> list[str]:
    """Clean user-editable preference strings before they're interpolated into an LLM
    prompt (G6): strip control/quote/bracket characters that could break out of the
    intended "list of food names" context, collapse whitespace, cap length, and drop
    anything that becomes empty as a result.
    """
    cleaned = []
    for item in items:
        stripped = _DISALLOWED_CHARS.sub(" ", item).strip()
        stripped = " ".join(stripped.split())[:_MAX_ITEM_LENGTH]
        if stripped:
            cleaned.append(stripped)
    return cleaned
