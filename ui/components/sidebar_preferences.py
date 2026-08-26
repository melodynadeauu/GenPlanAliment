"""Sidebar section: scalable food preferences (likes/dislikes)."""

import streamlit as st
from ui.state import KEY_ACTIVE_PREF_TAB, KEY_PREF_FILTER


def render_preferences_section(likes: list[str], dislikes: list[str]) -> None:
    """Render the segmented tab + search filter + scrollable chip list.

    Args:
        likes: List of preferred foods
        dislikes: List of avoided foods

    Reads/writes session_state:
        - KEY_ACTIVE_PREF_TAB: "likes" or "dislikes"
        - KEY_PREF_FILTER: Search query (substring match, case-insensitive)
    """
    st.markdown("### Préférences")

    active_tab = st.session_state.get(KEY_ACTIVE_PREF_TAB, "likes")

    tab_col1, tab_col2 = st.columns(2)
    with tab_col1:
        if st.button(f"J'aime ({len(likes)})", use_container_width=True):
            st.session_state[KEY_ACTIVE_PREF_TAB] = "likes"
    with tab_col2:
        if st.button(f"Je n'aime pas ({len(dislikes)})", use_container_width=True):
            st.session_state[KEY_ACTIVE_PREF_TAB] = "dislikes"

    # Reread session state after button click
    active_tab = st.session_state.get(KEY_ACTIVE_PREF_TAB, "likes")

    # Search filter
    filter_query = st.text_input(
        "Chercher",
        value=st.session_state.get(KEY_PREF_FILTER, ""),
        key=f"pref_filter_input",
    )
    st.session_state[KEY_PREF_FILTER] = filter_query

    # Determine which list to display and filter
    if active_tab == "likes":
        items_to_show = likes
        chip_class = "chip-accent"
    else:
        items_to_show = dislikes
        chip_class = "chip-danger"

    # Filter items by search query (substring, case-insensitive)
    filter_query_lower = (filter_query or "").lower()
    filtered_items = [
        item for item in items_to_show
        if filter_query_lower in item.lower()
    ]

    # Render chips in scrollable container
    st.markdown("#### Aliments")
    with st.container(height=160, border=False):
        chip_html = ""
        for item in filtered_items:
            chip_html += f'<span class="chip {chip_class}">{item}</span>'

        if chip_html:
            st.markdown(chip_html, unsafe_allow_html=True)
        else:
            st.markdown(
                f"*Aucun aliment trouvé pour « {filter_query} »*"
                if filter_query
                else "*Aucun aliment*"
            )
