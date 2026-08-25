"""Access to food preferences stored in food_preferences.json."""
import json
from pathlib import Path

PREFERENCES_PATH = Path(__file__).resolve().parent / "food_preferences.json"


def load_preferences():
    """Load food preferences from the JSON file."""
    with open(PREFERENCES_PATH, encoding="utf-8") as f:
        return json.load(f)
