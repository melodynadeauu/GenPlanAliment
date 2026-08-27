"""Sidebar section: editable food preferences (likes/dislikes), backed by
data/preferences/food_preferences.json.
"""

import streamlit as st

from core.agent import preference_validation
from data.preferences import store as preferences_store
from ui.state import KEY_ACTIVE_PREF_TAB
from ui.theme import pref_tag_css

_TAB_LABELS = {"likes": "Likes", "dislikes": "Dislikes"}
_ERROR_KEY = "pref_error"


def _on_pref_tab_click(tab_name: str) -> None:
    """Switch the active tab on click (callback, so the first click already lands)."""
    st.session_state[KEY_ACTIVE_PREF_TAB] = tab_name


def _widget_key(tab: str) -> str:
    return f"pref_{tab}_multiselect"


def _mounted_key(tab: str) -> str:
    return f"pref_{tab}_mounted"


def _on_items_changed(tab: str, likes: list[str], dislikes: list[str]) -> None:
    """Validate then persist the edited list; only called by an actual user edit.

    An unknown food or a like/dislike overlap blocks the save, and the reason
    goes to _ERROR_KEY (a callback can't render directly).
    """
    selected = list(st.session_state[_widget_key(tab)])
    previous = likes if tab == "likes" else dislikes

    unknown = preference_validation.find_unknown_new_items(previous, selected)
    if unknown:
        terms = ", ".join(f"« {item} »" for item in unknown)
        st.session_state[_ERROR_KEY] = (
            f"{terms} not recognized as a USDA food. Try a simpler or more generic name."
        )
        return

    if tab == "likes":
        updated = {"likes": selected, "dislikes": dislikes}
    else:
        updated = {"likes": likes, "dislikes": selected}

    try:
        preferences_store.save_preferences(updated)
    except ValueError as error:
        st.session_state[_ERROR_KEY] = str(error)
        return

    st.session_state[_ERROR_KEY] = None


def render_preferences_section(disabled: bool = False) -> None:
    """Render the segmented tab + editable chip list (add/remove) for the active tab.

    Reads preferences fresh from the JSON file each run; an edit saves immediately.

    Args:
        disabled: disable the tab buttons and the chip editor.

    Reads/writes session_state:
        - KEY_ACTIVE_PREF_TAB: "likes" or "dislikes"
        - pref_<tab>_multiselect: the chips currently shown for that tab
    """
    st.markdown('<div class="am-label">Food preferences</div>', unsafe_allow_html=True)

    prefs = preferences_store.load_preferences()
    likes = prefs["likes"]
    dislikes = prefs["dislikes"]

    active_tab = st.session_state.get(KEY_ACTIVE_PREF_TAB, "likes")

    tab_col1, tab_col2 = st.columns(2)
    with tab_col1:
        st.button(
            f"Likes · {len(likes)}",
            width="stretch",
            type="primary" if active_tab == "likes" else "secondary",
            on_click=_on_pref_tab_click,
            args=("likes",),
            disabled=disabled,
        )
    with tab_col2:
        st.button(
            f"Dislikes · {len(dislikes)}",
            width="stretch",
            type="primary" if active_tab == "dislikes" else "secondary",
            on_click=_on_pref_tab_click,
            args=("dislikes",),
            disabled=disabled,
        )

    # Re-read: the callback above has already run for this rerun.
    active_tab = st.session_state.get(KEY_ACTIVE_PREF_TAB, "likes")
    active_items = likes if active_tab == "likes" else dislikes

    st.markdown(f"<style>{pref_tag_css(active_tab)}</style>", unsafe_allow_html=True)

    # Re-seed on every *mount*: switching tabs unmounts the other multiselect,
    # and Streamlit resets it to an empty default. A `key not in session_state`
    # guard would miss that (the key still exists, now empty), so track mount
    # state instead and reload from the file each time a tab is remounted.
    key = _widget_key(active_tab)
    other_tab = "dislikes" if active_tab == "likes" else "likes"
    if not st.session_state.get(_mounted_key(active_tab)):
        st.session_state[key] = list(active_items)
    st.session_state[_mounted_key(active_tab)] = True
    st.session_state[_mounted_key(other_tab)] = False

    st.multiselect(
        _TAB_LABELS[active_tab],
        options=sorted(set(active_items) | set(st.session_state[key])),
        accept_new_options=True,
        label_visibility="collapsed",
        placeholder="Choose or add a food",
        key=key,
        on_change=_on_items_changed,
        args=(active_tab, likes, dislikes),
        disabled=disabled,
    )

    # st.error in an on_change callback renders nothing; the message travels
    # through session_state instead.
    error = st.session_state.get(_ERROR_KEY)
    if error:
        st.error(error)
