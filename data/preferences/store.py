"""Access to food preferences stored in food_preferences.json."""
import json
from pathlib import Path

PREFERENCES_PATH = Path(__file__).resolve().parent / "food_preferences.json"


def _find_overlapping_preferences(preferences: dict) -> set[str]:
    """Return foods that appear in both preference categories."""
    likes = {food.strip().casefold() for food in preferences.get("likes", [])}
    dislikes = {food.strip().casefold() for food in preferences.get("dislikes", [])}
    return likes & dislikes


def load_preferences():
    """Load food preferences from the JSON file."""
    with open(PREFERENCES_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_preferences(preferences: dict) -> None:
    """Persist food preferences (keys: likes, dislikes) to the JSON file, overwriting it."""
    overlapping = _find_overlapping_preferences(preferences)
    if overlapping:
        foods = ", ".join(sorted(overlapping))
        raise ValueError(f"A food cannot be both liked and disliked: {foods}")

    with open(PREFERENCES_PATH, "w", encoding="utf-8") as f:
        json.dump(preferences, f, indent=2, ensure_ascii=False)
        f.write("\n")
