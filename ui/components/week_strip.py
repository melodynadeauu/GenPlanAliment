"""The training week: seven day cards, each showing the day's activity and what
it burns. This is the row that makes the product legible at a glance -- the plan
follows the training, so the training has to be on screen.
"""

import streamlit as st

from core.models import Profile
from fixtures.demo_week import display_for
from ui.energy import exercise_kcal, load_day_activities
from ui.icons import activity_icon, icon
from ui.state import KEY_SELECTED_DAY, KEY_WEEK_EXPANDED

_FULL_DAY = {
    "monday": "Monday", "tuesday": "Tuesday", "wednesday": "Wednesday",
    "thursday": "Thursday", "friday": "Friday", "saturday": "Saturday",
    "sunday": "Sunday",
}


def _on_day_click(day_name: str) -> None:
    """Select a day on click (callback, so the first click already lands)."""
    st.session_state[KEY_SELECTED_DAY] = day_name


def _toggle_week_expand() -> None:
    st.session_state[KEY_WEEK_EXPANDED] = not st.session_state.get(KEY_WEEK_EXPANDED, False)


def _card_html(label: str, glyph: str, short: str, meta: str, burn_text: str,
               selected: bool, expanded: bool) -> str:
    """The card's own box, so its last line can never render outside its border."""
    collapsed = "" if expanded else " am-day-collapsed"
    inner = f'<div class="am-day-name">{label}</div>'
    if expanded:
        inner += (
            f'<div class="am-day-act">{glyph}{short}</div>'
            f'<div class="am-day-meta">{meta}</div>'
            f'<div class="am-day-burn">{burn_text}</div>'
        )
    return (
        f'<div class="am-day{" am-day-on" if selected else ""}{collapsed}">'
        f"{inner}"
        "</div>"
    )


def render_week_strip(week: list[dict], profile: Profile, disabled: bool = False) -> str:
    """Render the seven day cards and return the selected day name.

    Args:
        week: fixtures.demo_week.DEMO_WEEK rows (fallback when the DB is empty).
        profile: used only to price each day's activity in kcal.
        disabled: True while a plan is generating -- the day buttons and the
            expand/collapse toggle are disabled so a click can't fire a rerun
            that cancels the in-flight generation.
    """
    expanded = st.session_state.get(KEY_WEEK_EXPANDED, False)
    toggle_glyph = icon("chevron-up", 14) if expanded else icon("chevron-down", 14)

    with st.container(key="week_strip_header"):
        label_col, toggle_col = st.columns([11, 1], vertical_alignment="center")
        with label_col:
            st.markdown(
                '<div class="am-label">Training week'
                "<span>Pick the day you want a plan for</span></div>",
                unsafe_allow_html=True,
            )
        with toggle_col:
            with st.container(key="week_expand_toggle"):
                st.markdown(
                    f'<div class="am-week-toggle-icon">{toggle_glyph}</div>',
                    unsafe_allow_html=True,
                )
                st.button(
                    "Toggle training week details",
                    key="week_expand_btn",
                    on_click=_toggle_week_expand,
                    disabled=disabled,
                )

    columns = st.columns(7, gap="small")
    for column, entry in zip(columns, week):
        day_name = entry["day"]
        rows = load_day_activities(day_name, week)
        burn = round(exercise_kcal(rows, profile.weight_kg))

        if rows:
            # A day can hold several sessions. The kcal below sums all of them,
            # so naming only the first one leaves a total that does not add up
            # to anything on screen -- say how many there are instead, and let
            # the energy chain name them.
            lead = max(rows, key=lambda row: exercise_kcal([row], profile.weight_kg))
            glyph = activity_icon(lead["activity"])
            if len(rows) == 1:
                short, _ = display_for(lead["activity"])
                detail = lead["intensity"]
            else:
                short = f"{len(rows)} sessions"
                detail = ", ".join(display_for(row["activity"])[0] for row in rows)
            total_minutes = sum(row["duration_minutes"] for row in rows)
            meta = (
                f"{total_minutes} min"
                f'<span class="am-day-int"> · {detail}</span>'
            )
            burn_text = f"+{burn} kcal"
        else:
            short, glyph, meta, burn_text = "Rest day", icon("moon"), "No session", "No burn"

        is_selected = day_name == st.session_state[KEY_SELECTED_DAY]
        full_day = _FULL_DAY.get(day_name, day_name.capitalize())

        with column:
            with st.container(key=f"daycard-{day_name}"):
                st.markdown(
                    _card_html(
                        entry["label"], glyph, short, meta, burn_text,
                        is_selected, expanded,
                    ),
                    unsafe_allow_html=True,
                )
                # Every session, always -- a narrow window drops the detail
                # from the visible meta line, and this is the only place it is
                # otherwise available.
                if rows:
                    sessions = "; ".join(
                        f"{display_for(row['activity'])[0]}, "
                        f"{row['duration_minutes']} min, {row['intensity']} intensity"
                        for row in rows
                    )
                    spoken = f"{full_day} — {sessions}"
                else:
                    spoken = f"{full_day} — rest day"
                st.button(
                    spoken,
                    key=f"day_btn_{day_name}",
                    width="stretch",
                    on_click=_on_day_click,
                    args=(day_name,),
                    disabled=disabled,
                )

    return st.session_state[KEY_SELECTED_DAY]
