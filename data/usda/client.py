"""USDA FoodData Central client: search + nutrition, backed by the local cache."""
import requests

from data.usda.cache import (
    get_cached_nutrition,
    get_cached_search,
    load_cache,
    set_cached_nutrition,
    set_cached_search,
)

SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
FOOD_URL = "https://api.nal.usda.gov/fdc/v1/food"
TIMEOUT_SECONDS = 5


def search_food(query: str, api_key: str) -> list[dict] | None:
    """Search USDA foods for `query`, via the cache first. None if no results."""
    cache = load_cache()
    results = get_cached_search(cache, query)

    if results is None:
        response = requests.get(
            SEARCH_URL,
            params={"query": query, "api_key": api_key},
            timeout=TIMEOUT_SECONDS,
        )
        data = response.json()
        results = [
            {"fdc_id": food["fdcId"], "description": food["description"]}
            for food in data.get("foods", [])
        ]
        set_cached_search(cache, query, results)

    return results or None


def get_nutrition(fdc_id: str, api_key: str) -> dict | None:
    """fdc_id, description and full foodNutrients entries for `fdc_id`, via the cache first."""
    cache = load_cache()
    food = get_cached_nutrition(cache, fdc_id)

    if food is None:
        response = requests.get(
            f"{FOOD_URL}/{fdc_id}",
            params={"api_key": api_key},
            timeout=TIMEOUT_SECONDS,
        )
        data = response.json()
        food = {
            "fdc_id": data.get("fdcId"),
            "description": data.get("description"),
            "foodNutrients": data.get("foodNutrients", []),
        }
        set_cached_nutrition(cache, fdc_id, food)

    if not food["foodNutrients"]:
        return None

    return food
