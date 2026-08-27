"""session_state schema for the app."""

import streamlit as st

from fixtures.demo_profile import DEMO_PROFILE

KEY_SELECTED_DAY = "selected_day"
KEY_ACTIVE_PREF_TAB = "active_pref_tab"
KEY_GENERATED_PLAN = "generated_plan"
KEY_PLAN_DAY = "generated_plan_day"
KEY_IS_GENERATING = "is_generating"
KEY_GENERATING_DAY = "generating_day"
KEY_GENERATION_ERROR = "generation_error"
KEY_PROFILE_AGE = "profile_age"
KEY_PROFILE_WEIGHT = "profile_weight"
KEY_PROFILE_HEIGHT = "profile_height"
KEY_PROFILE_GOAL = "profile_goal"
KEY_WEEK_EXPANDED = "week_strip_expanded"

DEFAULTS = {
    KEY_SELECTED_DAY: "wednesday",
    KEY_ACTIVE_PREF_TAB: "likes",
    KEY_GENERATED_PLAN: None,
    KEY_PLAN_DAY: None,
    KEY_IS_GENERATING: False,
    KEY_GENERATING_DAY: None,
    KEY_GENERATION_ERROR: None,
    KEY_PROFILE_AGE: DEMO_PROFILE["age"],
    KEY_PROFILE_WEIGHT: DEMO_PROFILE["weight_kg"],
    KEY_PROFILE_HEIGHT: DEMO_PROFILE["height_cm"],
    KEY_PROFILE_GOAL: DEMO_PROFILE["goal"],
    KEY_WEEK_EXPANDED: False,
}


def init_state() -> None:
    """Populate any missing session_state keys with their defaults.

    Idempotent: safe to call multiple times.
    Called once at the top of app.py.
    """
    for key, default in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default
