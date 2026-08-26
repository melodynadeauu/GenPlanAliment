"""Sidebar section: editable food preferences (likes/dislikes), backed by
data/preferences/food_preferences.json.
"""

import streamlit as st

from data.preferences import store as preferences_store
from ui.state import KEY_ACTIVE_PREF_TAB

_TAB_LABELS = {"likes": "J'aime", "dislikes": "Je n'aime pas"}


def render_preferences_section() -> None:
    """Render the segmented tab + editable chip list (add/remove) for the active tab.

    Reads preferences fresh from the JSON file on every run and, if the user adds or
    removes an item, saves the updated preferences back immediately — so the next
    plan generation (core.agent.plan_generator, which also reads the JSON file) picks
    up the change.

    Reads/writes session_state:
        - KEY_ACTIVE_PREF_TAB: "likes" or "dislikes"
    """
    st.markdown("### Préférences")

    prefs = preferences_store.load_preferences()
    likes = prefs["likes"]
    dislikes = prefs["dislikes"]

    active_tab = st.session_state.get(KEY_ACTIVE_PREF_TAB, "likes")

    tab_col1, tab_col2 = st.columns(2)
    with tab_col1:
        if st.button(f"J'aime ({len(likes)})", width="stretch"):
            st.session_state[KEY_ACTIVE_PREF_TAB] = "likes"
    with tab_col2:
        if st.button(f"Je n'aime pas ({len(dislikes)})", width="stretch"):
            st.session_state[KEY_ACTIVE_PREF_TAB] = "dislikes"

    # Reread session state after button click
    active_tab = st.session_state.get(KEY_ACTIVE_PREF_TAB, "likes")
    active_items = likes if active_tab == "likes" else dislikes

    st.markdown("#### Aliments")
    selected = st.multiselect(
        _TAB_LABELS[active_tab],
        options=active_items,
        default=active_items,
        accept_new_options=True,
        label_visibility="collapsed",
        placeholder="Choisir ou ajouter un aliment",
        key=f"pref_{active_tab}_multiselect",
    )

    if selected != active_items:
        if active_tab == "likes":
            preferences_store.save_preferences({"likes": selected, "dislikes": dislikes})
        else:
            preferences_store.save_preferences({"likes": likes, "dislikes": selected})
