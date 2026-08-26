"""Sidebar section: profile fields (age, weight, height, goal)."""

import streamlit as st

from ui.state import (
    KEY_PROFILE_AGE,
    KEY_PROFILE_GOAL,
    KEY_PROFILE_HEIGHT,
    KEY_PROFILE_WEIGHT,
)

_GOAL_OPTIONS = ["Weight loss", "Muscle gain", "Maintenance"]


def render_profile_section() -> None:
    """Render the editable profile fields.

    Each field binds directly to its session_state key (seeded from
    fixtures.demo_profile.DEMO_PROFILE by ui.state.init_state) so edits persist
    across reruns -- see ui.adapters.profile_from_dict for reading them back.
    """
    st.markdown("### Profile")

    col1, col2 = st.columns(2)

    with col1:
        st.number_input("Age (years)", min_value=1, max_value=120, key=KEY_PROFILE_AGE)
        st.number_input("Weight (kg)", min_value=20.0, max_value=300.0, key=KEY_PROFILE_WEIGHT)

    with col2:
        st.number_input("Height (cm)", min_value=50.0, max_value=250.0, key=KEY_PROFILE_HEIGHT)
        st.selectbox("Goal", options=_GOAL_OPTIONS, key=KEY_PROFILE_GOAL)
