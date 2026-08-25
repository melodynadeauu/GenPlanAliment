"""Tests for data.usda.client. All requests.get calls are faked -- no real network."""
import pytest

from data.usda import cache as usda_cache
from data.usda import client as usda_client


@pytest.fixture(autouse=True)
def isolated_cache_path(tmp_path, monkeypatch):
    """Redirect CACHE_PATH to a throwaway file so tests never touch the real cache."""
    monkeypatch.setattr(usda_cache, "CACHE_PATH", tmp_path / "usda_cache.json")


class FakeResponse:
    def __init__(self, json_data):
        self._json_data = json_data

    def json(self):
        return self._json_data


def make_fake_get(json_data, calls):
    """Return a fake requests.get that records each call and replays `json_data`."""

    def fake_get(url, params=None, timeout=None):
        calls.append({"url": url, "params": params, "timeout": timeout})
        return FakeResponse(json_data)

    return fake_get


# --- search_food ---


def test_search_food_returns_results_and_caches_them(monkeypatch):
    calls = []
    api_response = {
        "foods": [
            {"fdcId": 123456, "description": "Apple, raw"},
            {"fdcId": 789012, "description": "Apple juice"},
        ]
    }
    monkeypatch.setattr(usda_client.requests, "get", make_fake_get(api_response, calls))

    result = usda_client.search_food("apple", "FAKE_KEY")

    assert result == [
        {"fdc_id": 123456, "description": "Apple, raw"},
        {"fdc_id": 789012, "description": "Apple juice"},
    ]
    assert len(calls) == 1
    assert calls[0]["url"] == "https://api.nal.usda.gov/fdc/v1/foods/search"
    assert calls[0]["params"] == {"query": "apple", "api_key": "FAKE_KEY"}
    assert calls[0]["timeout"] == 5

    cache = usda_cache.load_cache()
    assert usda_cache.get_cached_search(cache, "apple") == result


def test_search_food_returns_none_when_no_results(monkeypatch):
    calls = []
    monkeypatch.setattr(usda_client.requests, "get", make_fake_get({"foods": []}, calls))

    result = usda_client.search_food("zzz_nonexistent", "FAKE_KEY")

    assert result is None


def test_search_food_uses_cache_on_second_call(monkeypatch):
    calls = []
    api_response = {"foods": [{"fdcId": 1, "description": "Apple"}]}
    monkeypatch.setattr(usda_client.requests, "get", make_fake_get(api_response, calls))

    usda_client.search_food("apple", "FAKE_KEY")
    usda_client.search_food("  Apple  ", "FAKE_KEY")

    assert len(calls) == 1


# --- get_nutrition ---


FOOD_DETAIL_EXAMPLE = {
    "dataType": "Branded",
    "description": "NUT 'N BERRY MIX",
    "fdcId": 534358,
    "foodNutrients": [
        {
            "number": 303,
            "name": "Iron, Fe",
            "amount": 0.53,
            "unitName": "mg",
            "derivationCode": "LCCD",
            "derivationDescription": "Calculated from a daily value percentage per serving size measure",
        }
    ],
    "publicationDate": "4/1/2019",
    "brandOwner": "Kar Nut Products Company",
    "gtinUpc": "077034085228",
    "ndbNumber": 7954,
    "foodCode": "27415110",
}


def test_get_nutrition_returns_and_caches_fdc_id_description_and_full_food_nutrients(monkeypatch):
    """Cache/return fdc_id, description and the whole foodNutrients entries as-is -- no scaling,
    no collapsing to {name: amount}: units differ per nutrient (mg, g, kcal, ...) and other
    fields (number, derivationCode, derivationDescription, ...) must survive untouched."""
    calls = []
    monkeypatch.setattr(usda_client.requests, "get", make_fake_get(FOOD_DETAIL_EXAMPLE, calls))

    result = usda_client.get_nutrition("534358", "FAKE_KEY")

    expected = {
        "fdc_id": 534358,
        "description": "NUT 'N BERRY MIX",
        "foodNutrients": FOOD_DETAIL_EXAMPLE["foodNutrients"],
    }
    assert result == expected
    assert len(calls) == 1
    assert calls[0]["url"] == "https://api.nal.usda.gov/fdc/v1/food/534358"
    assert calls[0]["params"] == {"api_key": "FAKE_KEY"}
    assert calls[0]["timeout"] == 5

    cache = usda_cache.load_cache()
    assert usda_cache.get_cached_nutrition(cache, "534358") == expected


def test_get_nutrition_uses_cache_on_second_call(monkeypatch):
    calls = []
    monkeypatch.setattr(usda_client.requests, "get", make_fake_get(FOOD_DETAIL_EXAMPLE, calls))

    usda_client.get_nutrition("534358", "FAKE_KEY")
    usda_client.get_nutrition("534358", "FAKE_KEY")

    assert len(calls) == 1


def test_get_nutrition_returns_none_when_no_nutrients(monkeypatch):
    calls = []
    monkeypatch.setattr(
        usda_client.requests,
        "get",
        make_fake_get({"fdcId": 1, "description": "Empty", "foodNutrients": []}, calls),
    )

    result = usda_client.get_nutrition("1", "FAKE_KEY")

    assert result is None
