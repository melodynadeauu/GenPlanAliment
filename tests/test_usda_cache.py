"""Tests for data.usda.cache."""
import json

import pytest

from data.usda import cache as usda_cache


@pytest.fixture(autouse=True)
def isolated_cache_path(tmp_path, monkeypatch):
    """Redirect CACHE_PATH to a throwaway file so tests never touch the real cache."""
    monkeypatch.setattr(usda_cache, "CACHE_PATH", tmp_path / "usda_cache.json")
    return usda_cache.CACHE_PATH


def test_load_cache_creates_file_with_empty_dict_when_missing(isolated_cache_path):
    assert not isolated_cache_path.exists()

    result = usda_cache.load_cache()

    assert result == {}
    assert isolated_cache_path.exists()
    assert json.loads(isolated_cache_path.read_text(encoding="utf-8")) == {}


def test_load_cache_reads_existing_content(isolated_cache_path):
    isolated_cache_path.write_text(
        json.dumps({"search": {"apple": ["fdc1"]}, "nutrition": {}}),
        encoding="utf-8",
    )

    result = usda_cache.load_cache()

    assert result == {"search": {"apple": ["fdc1"]}, "nutrition": {}}


def test_save_cache_writes_dict_to_disk(isolated_cache_path):
    usda_cache.save_cache({"search": {"apple": ["fdc1"]}, "nutrition": {}})

    assert json.loads(isolated_cache_path.read_text(encoding="utf-8")) == {
        "search": {"apple": ["fdc1"]},
        "nutrition": {},
    }


def test_get_cached_search_returns_none_when_absent():
    cache = {}
    assert usda_cache.get_cached_search(cache, "apple") is None


def test_set_then_get_cached_search_round_trips():
    cache = {}
    usda_cache.set_cached_search(cache, "apple", [{"fdcId": "1"}])

    assert usda_cache.get_cached_search(cache, "apple") == [{"fdcId": "1"}]


def test_get_cached_search_normalizes_query_case_and_whitespace():
    cache = {}
    usda_cache.set_cached_search(cache, "  Apple  ", [{"fdcId": "1"}])

    assert usda_cache.get_cached_search(cache, "apple") == [{"fdcId": "1"}]
    assert usda_cache.get_cached_search(cache, "APPLE") == [{"fdcId": "1"}]


def test_set_cached_search_writes_through_to_disk(isolated_cache_path):
    cache = usda_cache.load_cache()

    usda_cache.set_cached_search(cache, "apple", [{"fdcId": "1"}])

    on_disk = json.loads(isolated_cache_path.read_text(encoding="utf-8"))
    assert on_disk["search"]["apple"] == [{"fdcId": "1"}]


def test_get_cached_nutrition_returns_none_when_absent():
    cache = {}
    assert usda_cache.get_cached_nutrition(cache, "12345") is None


def test_set_then_get_cached_nutrition_round_trips():
    cache = {}
    usda_cache.set_cached_nutrition(cache, "12345", {"protein": 1.2})

    assert usda_cache.get_cached_nutrition(cache, "12345") == {"protein": 1.2}


def test_set_cached_nutrition_writes_through_to_disk(isolated_cache_path):
    cache = usda_cache.load_cache()

    usda_cache.set_cached_nutrition(cache, "12345", {"protein": 1.2})

    on_disk = json.loads(isolated_cache_path.read_text(encoding="utf-8"))
    assert on_disk["nutrition"]["12345"] == {"protein": 1.2}
