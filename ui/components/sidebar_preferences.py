"""Sidebar section: editable food preferences (likes/dislikes), backed by
data/preferences/food_preferences.json.
"""

import streamlit as st

from data.preferences import store as preferences_store
from ui.state import KEY_ACTIVE_PREF_TAB

_TAB_LABELS = {"likes": "Likes", "dislikes": "Dislikes"}


# Callback to update active preference tab immediately on click
def _on_pref_tab_click(tab_name: str) -> None:
    """Update active preference tab in session state when tab button is clicked."""
    st.session_state[KEY_ACTIVE_PREF_TAB] = tab_name


def render_preferences_section() -> None:
    """Render the segmented tab + editable chip list (add/remove) for the active tab.

    Reads preferences fresh from the JSON file on every run and, if the user adds or
    removes an item, saves the change back immediately -- so the next plan generation
    (core.agent.plan_generator, which also reads the JSON file) picks it up.

    Reads/writes session_state:
        - KEY_ACTIVE_PREF_TAB: "likes" or "dislikes"
    """
    st.markdown("### Preferences")

    prefs = preferences_store.load_preferences()
    likes = prefs["likes"]
    dislikes = prefs["dislikes"]

    active_tab = st.session_state.get(KEY_ACTIVE_PREF_TAB, "likes")

    tab_col1, tab_col2 = st.columns(2)
    with tab_col1:
        # Show "Likes" tab with primary style if active, secondary if not
        # Use callback to update selection immediately on first click
        button_type = "primary" if active_tab == "likes" else "secondary"
        st.button(
            f"Likes ({len(likes)})",
            width="stretch",
            type=button_type,
            on_click=_on_pref_tab_click,
            args=("likes",)
        )
    with tab_col2:
        # Show "Dislikes" tab with primary style if active, secondary if not
        # Use callback to update selection immediately on first click
        button_type = "primary" if active_tab == "dislikes" else "secondary"
        st.button(
            f"Dislikes ({len(dislikes)})",
            width="stretch",
            type=button_type,
            on_click=_on_pref_tab_click,
            args=("dislikes",)
        )

    # Reread session state after button click
    active_tab = st.session_state.get(KEY_ACTIVE_PREF_TAB, "likes")
    active_items = likes if active_tab == "likes" else dislikes

    st.markdown("#### Foods")
    selected = st.multiselect(
        _TAB_LABELS[active_tab],
        options=active_items,
        default=active_items,
        accept_new_options=True,
        label_visibility="collapsed",
        placeholder="Choose or add a food",
        key=f"pref_{active_tab}_multiselect",
    )

    if selected != active_items:
        if active_tab == "likes":
            preferences_store.save_preferences({"likes": selected, "dislikes": dislikes})
        else:
            preferences_store.save_preferences({"likes": likes, "dislikes": selected})
