"""USDA FoodData Central client: search + nutrition, backed by the local cache."""
import json
import os
import time
from dataclasses import dataclass

import requests
from dotenv import load_dotenv

from data.usda.cache import (
    get_cached_nutrition,
    get_cached_search,
    set_cached_nutrition_found,
    set_cached_nutrition_not_found,
    set_cached_search,
)
from data.usda.nutrients import MACRO_FIELDS, extract_macros

SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
FOOD_URL = "https://api.nal.usda.gov/fdc/v1/food"
TIMEOUT_SECONDS = 5


def _require_api_key(value: str | None) -> str:
    """Raise a clear error if `value` is missing/empty; otherwise return it as-is."""
    if not value:
        raise RuntimeError(
            "USDA_API_KEY is absent or empty. Define it in a .env file at the root of the project "
            "(see .env.example)."
        )
    return value


load_dotenv()
USDA_API_KEY = _require_api_key(os.getenv("USDA_API_KEY"))


# MAX_RETRIES retries after the initial attempt; each list holds one delay per retry.
RETRY_DELAYS_SECONDS = [1, 2]
RATE_LIMIT_DELAYS_SECONDS = [2, 8]
MAX_RETRIES = 2


@dataclass(frozen=True)
class FoodLookupResult:
    """Outcome of a USDA lookup: either `food` (search results or a nutrition record) on
    success, or `error` (one of "not_found", "rate_limited", "timeout", "api_error") on
    failure -- never both."""

    food: dict | list[dict] | None
    error: str | None


def _retry_after_seconds(response) -> float | None:
    """Parse the Retry-After header as seconds, or None if absent/unparseable."""
    value = response.headers.get("Retry-After")
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _fetch_json(url: str, params: dict) -> tuple[dict | None, str | None]:
    """GET `url` as JSON, retrying transient failures. Never raises: returns
    (data, None) on success or (None, error_code) on failure, where error_code is
    one of "not_found", "rate_limited", "timeout", "api_error".
    """
    attempt = 0
    while True:
        try:
            response = requests.get(url, params=params, timeout=TIMEOUT_SECONDS)
        except (requests.Timeout, requests.ConnectionError):
            if attempt >= MAX_RETRIES:
                return None, "timeout"
            time.sleep(RETRY_DELAYS_SECONDS[attempt])
            attempt += 1
            continue

        status = response.status_code

        if status == 404:
            return None, "not_found"

        if status == 429:
            if attempt >= MAX_RETRIES:
                return None, "rate_limited"
            delay = _retry_after_seconds(response)
            if delay is None:
                delay = RATE_LIMIT_DELAYS_SECONDS[attempt]
            time.sleep(delay)
            attempt += 1
            continue

        if 500 <= status < 600:
            if attempt >= MAX_RETRIES:
                return None, "timeout"
            time.sleep(RETRY_DELAYS_SECONDS[attempt])
            attempt += 1
            continue

        if status != 200:
            return None, "api_error"

        try:
            return response.json(), None
        except json.JSONDecodeError:
            return None, "api_error"


def search_food(query: str, api_key: str) -> FoodLookupResult:
    """Search USDA foods for `query`, via the cache first."""
    cached = get_cached_search(query)

    if cached is not None:
        return FoodLookupResult(cached, None) if cached else FoodLookupResult(None, "not_found")

    data, error = _fetch_json(SEARCH_URL, {"query": query, "api_key": api_key})
    if error is not None:
        return FoodLookupResult(None, error)
    assert data is not None

    results = [
        {"fdc_id": food["fdcId"], "description": food["description"]}
        for food in data.get("foods", [])
    ]
    set_cached_search(query, results)

    return FoodLookupResult(results, None) if results else FoodLookupResult(None, "not_found")


def _is_stale(macros: dict) -> bool:
    """Stale if it predates a MACRO_FIELDS addition, or has kcal == 0.0 while
    another macro is non-zero (the old parser only read nutrient "208"). Either
    case gets one live refetch."""
    if not (set(MACRO_FIELDS.values()) <= macros.keys()):
        return True
    other_macros_present = any(
        macros[field] for field in ("protein_g", "fat_g", "carbs_g") if field in macros
    )
    return macros.get("kcal", 0.0) == 0.0 and other_macros_present


def get_nutrition(fdc_id: str, api_key: str) -> FoodLookupResult:
    """fdc_id, description and macros_per_100g for `fdc_id`, via the cache
    first. A stale cached row (see _is_stale) is refetched live and the cache
    self-heals.
    """
    cached = get_cached_nutrition(fdc_id)

    if cached is not None:
        if not cached["found"]:
            return FoodLookupResult(None, "not_found")
        if not _is_stale(cached["food"]["macros_per_100g"]):
            return FoodLookupResult(cached["food"], None)
        # else: stale (missing field, or zero-kcal with other macros present) -- refresh live

    data, error = _fetch_json(f"{FOOD_URL}/{fdc_id}", {"api_key": api_key})
    if error is not None:
        return FoodLookupResult(None, error)
    assert data is not None

    food_nutrients = data.get("foodNutrients", [])
    if not food_nutrients:
        set_cached_nutrition_not_found(fdc_id)
        return FoodLookupResult(None, "not_found")

    food = {
        "fdc_id": data.get("fdcId"),
        "description": data.get("description"),
        "macros_per_100g": extract_macros(food_nutrients),
    }
    set_cached_nutrition_found(fdc_id, food)

    return FoodLookupResult(food, None)
