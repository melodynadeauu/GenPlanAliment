"""Guardrail: block obviously non-food terms from entering the preferences list.

Checks a new preference term against USDA FoodData Central. Complements
guardrails.sanitize_preference_items, which only strips characters and says
nothing about content -- both still run (defense in depth).
"""
from data.usda import client as usda_client


def is_known_food(term: str) -> bool:
    """True unless USDA confirms `term` matches no food. Fails open on any
    other outcome (rate limit, timeout, API error) -- an unavailable USDA API
    must never block preference edits.
    """
    result = usda_client.search_food(term, usda_client.USDA_API_KEY)
    return result.error != "not_found"


def find_unknown_new_items(previous_items: list[str], new_items: list[str]) -> list[str]:
    """Newly added entries (absent from `previous_items`) that USDA doesn't
    recognize. Already-saved items are never re-validated.
    """
    added = [item for item in new_items if item not in previous_items]
    return [item for item in added if not is_known_food(item)]
