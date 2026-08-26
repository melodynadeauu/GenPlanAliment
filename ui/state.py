"""session_state schema for the app."""

import streamlit as st

KEY_SELECTED_DAY = "selected_day"
KEY_ACTIVE_PREF_TAB = "active_pref_tab"
KEY_PREF_FILTER = "pref_filter_query"
KEY_GENERATED_PLAN = "generated_plan"
KEY_IS_GENERATING = "is_generating"

DEFAULTS = {
    KEY_SELECTED_DAY: "mercredi",
    KEY_ACTIVE_PREF_TAB: "likes",
    KEY_PREF_FILTER: "",
    KEY_GENERATED_PLAN: None,
    KEY_IS_GENERATING: False,
}


def init_state() -> None:
    """Populate any missing session_state keys with their defaults.

    Idempotent — safe to call multiple times.
    Called once at the top of app.py.
    """
    for key, default in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default
