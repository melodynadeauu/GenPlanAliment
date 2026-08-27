"""What the preferences sidebar is allowed to write to food_preferences.json.

Each tab saves its own list; an empty list only reaches the file when the
user actually cleared every chip.

These do NOT reproduce the bug that motivated them (a real browser resets an
unmounted multiselect to empty, which used to overwrite the file) -- AppTest
keeps widget state across a round trip in a way a browser doesn't. The fix
was verified in the browser, not here.
"""

import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from data.preferences import store as preferences_store

LIKES = ["chicken", "salmon", "eggs"]
DISLIKES = ["beets", "Brussels"]


@pytest.fixture
def preferences_file(tmp_path, monkeypatch):
    """Point the store at a throwaway file seeded with a known list."""
    path = tmp_path / "food_preferences.json"
    path.write_text(json.dumps({"likes": LIKES, "dislikes": DISLIKES}), encoding="utf-8")
    monkeypatch.setattr(preferences_store, "PREFERENCES_PATH", path)
    return path


def _stored(path):
    return json.loads(path.read_text(encoding="utf-8"))


APP_PATH = str(Path(__file__).resolve().parent.parent / "app.py")


def _run_app():
    app = AppTest.from_file(APP_PATH, default_timeout=30)
    app.run()
    return app


def _tab_button(app, label_starts_with):
    for button in app.sidebar.button:
        if button.label.startswith(label_starts_with):
            return button
    raise AssertionError(f"no sidebar button starting with {label_starts_with!r}")


def test_tab_round_trip_keeps_the_stored_likes(preferences_file):
    """likes -> dislikes -> likes must come back with every chip, and not save."""
    app = _run_app()
    assert app.sidebar.multiselect[0].value == LIKES

    _tab_button(app, "Dislikes").click().run()
    assert app.sidebar.multiselect[0].value == DISLIKES

    _tab_button(app, "Likes").click().run()
    assert app.sidebar.multiselect[0].value == LIKES
    assert _stored(preferences_file) == {"likes": LIKES, "dislikes": DISLIKES}


def test_an_edit_after_a_tab_round_trip_saves_the_edit_not_an_empty_list(preferences_file):
    """The edit that used to wipe the file now writes exactly what the user left."""
    app = _run_app()
    _tab_button(app, "Dislikes").click().run()
    _tab_button(app, "Likes").click().run()

    kept = LIKES[:-1]
    app.sidebar.multiselect[0].set_value(kept).run()

    assert _stored(preferences_file) == {"likes": kept, "dislikes": DISLIKES}


def test_editing_dislikes_leaves_the_likes_alone(preferences_file):
    """Each tab saves its own list without carrying a stale copy of the other."""
    app = _run_app()
    _tab_button(app, "Dislikes").click().run()

    app.sidebar.multiselect[0].set_value(["beets"]).run()

    assert _stored(preferences_file) == {"likes": LIKES, "dislikes": ["beets"]}


def test_clearing_every_chip_is_still_honoured(preferences_file):
    """An empty list is only wrong when the user did not ask for it."""
    app = _run_app()

    app.sidebar.multiselect[0].set_value([]).run()

    assert _stored(preferences_file) == {"likes": [], "dislikes": DISLIKES}
