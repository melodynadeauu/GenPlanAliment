"""Page configuration and global styling for the Streamlit app."""

import streamlit as st

from ui.theme import GOOGLE_FONTS_URL, build_global_css


def configure_page() -> None:
    """Set page config, preload the webfonts and inject global CSS.

    Call once at the top of app.py before any other Streamlit code. The font
    <link> tags go in first: an @import alone is unreliable inside a Streamlit
    style block, and a missed font is the difference between the design and a
    default-sans fallback.
    """
    st.set_page_config(
        page_title="AgentMealPrep — activity-aware meal planning",
        page_icon="🥗",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        f'<link rel="stylesheet" href="{GOOGLE_FONTS_URL}">',
        unsafe_allow_html=True,
    )
    st.markdown(f"<style>{build_global_css()}</style>", unsafe_allow_html=True)
