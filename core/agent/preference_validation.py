"""Guardrail: block obviously non-food terms from entering the preferences list.

Complements guardrails.sanitize_preference_items (G6), which only strips
injection-relevant characters and says nothing about content. This checks a
newly added preference term against USDA FoodData Central -- an additional
layer, not a replacement: sanitize_preference_items still runs downstream on
whatever ends up saved here (defense in depth), since a substring match can
still miss a term that was reformulated after this check.

Never delegated to the LLM: like the other guardrails in this module, the
accept/reject decision is a deterministic Python call.
"""
from data.usda import client as usda_client


def is_known_food(term: str) -> bool:
    """True unless USDA confirms `term` matches no food ("not_found").

    Fails open on every other outcome (rate limited, timeout, api error): an
    unavailable USDA API must never block preference edits. Only a search
    that actually completed and returned zero results rejects the term.
    """
    result = usda_client.search_food(term, usda_client.USDA_API_KEY)
    return result.error != "not_found"


def find_unknown_new_items(previous_items: list[str], new_items: list[str]) -> list[str]:
    """Return the entries of `new_items` that are newly added (absent from
    `previous_items`) and that USDA does not recognize as food.

    Only newly added items are checked -- items already saved are never
    re-validated, so an existing preference can't start failing retroactively
    (e.g. if USDA is temporarily down when the page happens to reload).
    """
    added = [item for item in new_items if item not in previous_items]
    return [item for item in added if not is_known_food(item)]
