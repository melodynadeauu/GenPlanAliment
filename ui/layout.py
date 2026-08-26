"""Page configuration and global styling for the Streamlit app."""

import streamlit as st
from ui.theme import build_global_css


def configure_page() -> None:
    """Set page config and inject global CSS.

    Call once at the top of app.py before any other Streamlit code.
    """
    st.set_page_config(
        page_title="Agent Meal Prep",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(f"<style>{build_global_css()}</style>", unsafe_allow_html=True)
