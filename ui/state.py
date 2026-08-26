"""session_state schema for the app."""

import streamlit as st

from fixtures.demo_profile import DEMO_PROFILE

KEY_SELECTED_DAY = "selected_day"
KEY_ACTIVE_PREF_TAB = "active_pref_tab"
KEY_PREF_FILTER = "pref_filter_query"
KEY_GENERATED_PLAN = "generated_plan"
KEY_IS_GENERATING = "is_generating"
KEY_PROFILE_AGE = "profile_age"
KEY_PROFILE_WEIGHT = "profile_weight"
KEY_PROFILE_HEIGHT = "profile_height"
KEY_PROFILE_GOAL = "profile_goal"

DEFAULTS = {
    KEY_SELECTED_DAY: "mercredi",
    KEY_ACTIVE_PREF_TAB: "likes",
    KEY_PREF_FILTER: "",
    KEY_GENERATED_PLAN: None,
    KEY_IS_GENERATING: False,
    # Profile fields seed from DEMO_PROFILE on first run, then live entirely in
    # session_state — the user can edit them from there on (see sidebar_profile.py).
    KEY_PROFILE_AGE: DEMO_PROFILE["age"],
    KEY_PROFILE_WEIGHT: DEMO_PROFILE["weight_kg"],
    KEY_PROFILE_HEIGHT: DEMO_PROFILE["height_cm"],
    KEY_PROFILE_GOAL: DEMO_PROFILE["goal"],
}


def init_state() -> None:
    """Populate any missing session_state keys with their defaults.

    Idempotent — safe to call multiple times.
    Called once at the top of app.py.
    """
    for key, default in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default
