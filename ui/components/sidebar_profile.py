"""Sidebar section: profile fields (age, weight, height, goal)."""

import streamlit as st


def render_profile_section(profile: dict) -> None:
    """Render read-only-styled profile fields.

    Args:
        profile: Dict with keys: age, weight_kg, height_cm, goal

    Note: Values are hardcoded from fixtures for now. Future: persist to session_state.
    """
    st.markdown("### Profil")

    col1, col2 = st.columns(2)

    with col1:
        st.number_input(
            "Âge (ans)",
            value=profile["age"],
            disabled=True,
            key="profile_age",
        )
        st.number_input(
            "Poids (kg)",
            value=profile["weight_kg"],
            disabled=True,
            key="profile_weight",
        )

    with col2:
        st.number_input(
            "Taille (cm)",
            value=profile["height_cm"],
            disabled=True,
            key="profile_height",
        )
        st.selectbox(
            "Objectif",
            options=["Perte de poids", "Prise de muscle", "Maintien"],
            index=0,  # Default to "Perte de poids"
            disabled=True,
            key="profile_goal",
        )
