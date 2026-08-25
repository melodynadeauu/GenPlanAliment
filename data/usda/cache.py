"""Local JSON cache for USDA FoodData Central API responses (search + nutrition).

Permanent cache : once a query or fdc_id is cached, it stays cached.
Every set_ call writes through to disk immediately.
"""
import json
from pathlib import Path

CACHE_PATH = Path(__file__).resolve().parent / "usda_cache.json"


def load_cache() -> dict:
    """Load the USDA cache from disk, creating an empty one if missing."""
    if not CACHE_PATH.exists():
        save_cache({})
    with open(CACHE_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_cache(cache: dict) -> None:
    """Write the USDA cache to disk."""
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def get_cached_search(cache: dict, query: str) -> list | None:
    """Return cached search results for `query`, or None if not cached."""
    key = query.strip().lower()
    return cache.get("search", {}).get(key)


def set_cached_search(cache: dict, query: str, results: list) -> None:
    """Cache `results` for `query` (normalized) and write through to disk."""
    key = query.strip().lower()
    cache.setdefault("search", {})[key] = results
    save_cache(cache)


def get_cached_nutrition(cache: dict, fdc_id: str) -> dict | None:
    """Return cached nutrients for `fdc_id`, or None if not cached."""
    return cache.get("nutrition", {}).get(str(fdc_id))


def set_cached_nutrition(cache: dict, fdc_id: str, nutrients: dict) -> None:
    """Cache `nutrients` for `fdc_id` and write through to disk."""
    cache.setdefault("nutrition", {})[str(fdc_id)] = nutrients
    save_cache(cache)
