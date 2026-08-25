"""USDA FoodData Central client: search + nutrition, backed by the local cache."""
import json
import time
from dataclasses import dataclass

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


# 3 tentatives max = 1 initial attempt + MAX_RETRIES retries. Each list has one delay per retry.
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
    """GET `url` as JSON, retrying transient failures per the client's retry policy.

    Returns (data, None) on success, or (None, error_code) on failure. Never raises.
    error_code is one of "not_found", "rate_limited", "timeout", "api_error".
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
    cache = load_cache()
    cached = get_cached_search(cache, query)

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
    set_cached_search(cache, query, results)

    return FoodLookupResult(results, None) if results else FoodLookupResult(None, "not_found")


def get_nutrition(fdc_id: str, api_key: str) -> FoodLookupResult:
    """fdc_id, description and full foodNutrients entries for `fdc_id`, via the cache first."""
    cache = load_cache()
    cached = get_cached_nutrition(cache, fdc_id)

    if cached is not None:
        if cached["foodNutrients"]:
            return FoodLookupResult(cached, None)
        return FoodLookupResult(None, "not_found")

    data, error = _fetch_json(f"{FOOD_URL}/{fdc_id}", {"api_key": api_key})
    if error is not None:
        return FoodLookupResult(None, error)
    assert data is not None

    food = {
        "fdc_id": data.get("fdcId"),
        "description": data.get("description"),
        "foodNutrients": data.get("foodNutrients", []),
    }
    set_cached_nutrition(cache, fdc_id, food)

    return FoodLookupResult(food, None) if food["foodNutrients"] else FoodLookupResult(None, "not_found")
