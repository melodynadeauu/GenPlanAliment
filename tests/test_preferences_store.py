"""Tests for data.preferences.store: JSON-backed food preferences (likes/dislikes)."""
import json

import pytest

from data.preferences import store as preferences_store


@pytest.fixture(autouse=True)
def isolated_preferences_path(tmp_path, monkeypatch):
    """Redirect PREFERENCES_PATH to a throwaway file so tests never touch the real JSON."""
    monkeypatch.setattr(preferences_store, "PREFERENCES_PATH", tmp_path / "food_preferences.json")


def test_save_preferences_then_load_preferences_round_trips():
    preferences_store.save_preferences({"likes": ["chicken"], "dislikes": ["olives"]})

    assert preferences_store.load_preferences() == {"likes": ["chicken"], "dislikes": ["olives"]}


def test_save_preferences_overwrites_existing_file():
    preferences_store.save_preferences({"likes": ["chicken"], "dislikes": []})
    preferences_store.save_preferences({"likes": ["salmon"], "dislikes": ["olives"]})

    assert preferences_store.load_preferences() == {"likes": ["salmon"], "dislikes": ["olives"]}


def test_save_preferences_writes_readable_utf8_json():
    preferences_store.save_preferences({"likes": ["épinards"], "dislikes": []})

    raw = preferences_store.PREFERENCES_PATH.read_text(encoding="utf-8")
    assert "épinards" in raw  # not escaped as \uXXXX
    assert json.loads(raw) == {"likes": ["épinards"], "dislikes": []}
