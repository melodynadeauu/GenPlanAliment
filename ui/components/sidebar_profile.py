"""Sidebar section: profile fields (age, weight, height, goal)."""

import streamlit as st

from ui.state import (
    KEY_PROFILE_AGE,
    KEY_PROFILE_GOAL,
    KEY_PROFILE_HEIGHT,
    KEY_PROFILE_WEIGHT,
)

_GOAL_OPTIONS = ["Perte de poids", "Prise de muscle", "Maintien"]


def render_profile_section() -> None:
    """Render the editable profile fields.

    Each field binds directly to its session_state key (seeded from
    fixtures.demo_profile.DEMO_PROFILE by ui.state.init_state) so edits persist
    across reruns. Read the current profile back from st.session_state — see
    ui.adapters.profile_from_dict.
    """
    st.markdown("### Profil")

    col1, col2 = st.columns(2)

    with col1:
        st.number_input(
            "Âge (ans)",
            min_value=1,
            max_value=120,
            key=KEY_PROFILE_AGE,
        )
        st.number_input(
            "Poids (kg)",
            min_value=20.0,
            max_value=300.0,
            key=KEY_PROFILE_WEIGHT,
        )

    with col2:
        st.number_input(
            "Taille (cm)",
            min_value=50.0,
            max_value=250.0,
            key=KEY_PROFILE_HEIGHT,
        )
        st.selectbox(
            "Objectif",
            options=_GOAL_OPTIONS,
            key=KEY_PROFILE_GOAL,
        )
