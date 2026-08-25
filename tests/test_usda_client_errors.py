"""Tests for data.usda.client error handling: retries, backoff, and error codes.

All requests.get calls and time.sleep are faked -- no real network, no real waiting.
"""
import json

import pytest
import requests

from data.usda import cache as usda_cache
from data.usda import client as usda_client


@pytest.fixture(autouse=True)
def isolated_cache_path(tmp_path, monkeypatch):
    """Redirect CACHE_PATH to a throwaway file so tests never touch the real cache."""
    monkeypatch.setattr(usda_cache, "CACHE_PATH", tmp_path / "usda_cache.json")


@pytest.fixture(autouse=True)
def no_real_sleep(monkeypatch):
    """Record backoff delays instead of actually sleeping through them."""
    sleeps = []
    monkeypatch.setattr(usda_client.time, "sleep", lambda seconds: sleeps.append(seconds))
    return sleeps


class FakeResponse:
    def __init__(self, json_data=None, status_code=200, headers=None, malformed=False):
        self._json_data = json_data
        self.status_code = status_code
        self.headers = headers or {}
        self._malformed = malformed

    def json(self):
        if self._malformed:
            raise json.JSONDecodeError("Expecting value", "", 0)
        return self._json_data


def make_fake_get_sequence(items, calls):
    """items: list of FakeResponse or Exception instances, consumed per call (repeats the last)."""

    def fake_get(url, params=None, timeout=None):
        calls.append({"url": url, "params": params, "timeout": timeout})
        item = items[min(len(calls) - 1, len(items) - 1)]
        if isinstance(item, Exception):
            raise item
        return item

    return fake_get


SUCCESS_SEARCH = FakeResponse({"foods": [{"fdcId": 1, "description": "Apple"}]})


# --- Timeout / ConnectionError / 5xx -> retry 1s/2s (2 retries max = 3 attempts), then "timeout" ---


def test_timeout_exhausts_retries_and_returns_timeout_error(monkeypatch, no_real_sleep):
    calls = []
    monkeypatch.setattr(
        usda_client.requests, "get", make_fake_get_sequence([requests.Timeout()], calls)
    )

    result = usda_client.search_food("apple", "FAKE_KEY")

    assert result == usda_client.FoodLookupResult(None, "timeout")
    assert len(calls) == 3  # 1 initial attempt + 2 retries
    assert no_real_sleep == [1, 2]


def test_connection_error_exhausts_retries_and_returns_timeout_error(monkeypatch, no_real_sleep):
    calls = []
    monkeypatch.setattr(
        usda_client.requests, "get", make_fake_get_sequence([requests.ConnectionError()], calls)
    )

    result = usda_client.get_nutrition("1", "FAKE_KEY")

    assert result == usda_client.FoodLookupResult(None, "timeout")
    assert len(calls) == 3
    assert no_real_sleep == [1, 2]


def test_5xx_exhausts_retries_and_returns_timeout_error(monkeypatch, no_real_sleep):
    calls = []
    monkeypatch.setattr(
        usda_client.requests,
        "get",
        make_fake_get_sequence([FakeResponse(status_code=503)], calls),
    )

    result = usda_client.search_food("apple", "FAKE_KEY")

    assert result == usda_client.FoodLookupResult(None, "timeout")
    assert len(calls) == 3
    assert no_real_sleep == [1, 2]


def test_timeout_then_success_recovers_without_exhausting_retries(monkeypatch, no_real_sleep):
    calls = []
    monkeypatch.setattr(
        usda_client.requests,
        "get",
        make_fake_get_sequence([requests.Timeout(), requests.Timeout(), SUCCESS_SEARCH], calls),
    )

    result = usda_client.search_food("apple", "FAKE_KEY")

    assert result.error is None
    assert result.food == [{"fdc_id": 1, "description": "Apple"}]
    assert len(calls) == 3
    assert no_real_sleep == [1, 2]


# --- 429 -> retry, Retry-After header if present else 2s/8s (2 retries max = 3 attempts), then "rate_limited" ---


def test_429_exhausts_retries_and_returns_rate_limited_error(monkeypatch, no_real_sleep):
    calls = []
    monkeypatch.setattr(
        usda_client.requests,
        "get",
        make_fake_get_sequence([FakeResponse(status_code=429)], calls),
    )

    result = usda_client.search_food("apple", "FAKE_KEY")

    assert result == usda_client.FoodLookupResult(None, "rate_limited")
    assert len(calls) == 3
    assert no_real_sleep == [2, 8]


def test_429_respects_retry_after_header(monkeypatch, no_real_sleep):
    calls = []
    monkeypatch.setattr(
        usda_client.requests,
        "get",
        make_fake_get_sequence(
            [FakeResponse(status_code=429, headers={"Retry-After": "5"}), SUCCESS_SEARCH], calls
        ),
    )

    result = usda_client.search_food("apple", "FAKE_KEY")

    assert result.error is None
    assert len(calls) == 2
    assert no_real_sleep == [5.0]


# --- 404 / empty results -> immediate "not_found", no retry ---


def test_404_returns_not_found_immediately(monkeypatch, no_real_sleep):
    calls = []
    monkeypatch.setattr(
        usda_client.requests,
        "get",
        make_fake_get_sequence([FakeResponse(status_code=404)], calls),
    )

    result = usda_client.search_food("apple", "FAKE_KEY")

    assert result == usda_client.FoodLookupResult(None, "not_found")
    assert len(calls) == 1
    assert no_real_sleep == []


def test_404_returns_not_found_immediately_for_get_nutrition(monkeypatch, no_real_sleep):
    calls = []
    monkeypatch.setattr(
        usda_client.requests,
        "get",
        make_fake_get_sequence([FakeResponse(status_code=404)], calls),
    )

    result = usda_client.get_nutrition("1", "FAKE_KEY")

    assert result == usda_client.FoodLookupResult(None, "not_found")
    assert len(calls) == 1
    assert no_real_sleep == []


# --- Malformed JSON -> immediate "api_error", no retry, nothing cached ---


def test_malformed_json_returns_api_error_immediately(monkeypatch, no_real_sleep):
    calls = []
    monkeypatch.setattr(
        usda_client.requests,
        "get",
        make_fake_get_sequence([FakeResponse(malformed=True)], calls),
    )

    result = usda_client.search_food("apple", "FAKE_KEY")

    assert result == usda_client.FoodLookupResult(None, "api_error")
    assert len(calls) == 1
    assert no_real_sleep == []

    cache = usda_cache.load_cache()
    assert usda_cache.get_cached_search(cache, "apple") is None


# --- Never raises ---


def test_search_food_never_raises_on_repeated_failures(monkeypatch, no_real_sleep):
    calls = []
    monkeypatch.setattr(
        usda_client.requests, "get", make_fake_get_sequence([requests.ConnectionError()], calls)
    )

    result = usda_client.search_food("apple", "FAKE_KEY")  # must not raise

    assert result.food is None
    assert result.error == "timeout"
