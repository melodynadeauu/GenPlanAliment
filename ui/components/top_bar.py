"""Top bar: brand mark, day selector, activity summary, generate button."""

import streamlit as st

from data.activity import store as activity_store
from core.types import Weekday
from ui.state import KEY_SELECTED_DAY

# Callback to update selected day immediately on click
def _on_day_click(day_name: str) -> None:
    """Update selected day in session state when day button is clicked."""
    st.session_state[KEY_SELECTED_DAY] = day_name


def render_top_bar(week: list[dict], selected_day: str) -> tuple[str, bool, bool]:
    """Render the fixed top bar.

    Args:
        week: List of day dicts with keys: day, label, activity, duration_min, intensity
        selected_day: Currently selected day name (e.g. "wednesday")

    Returns:
        (new_selected_day, generate_clicked, demo_clicked): updated day, generate
        button state, and demo button state (D1: quota fallback -- reloads
        fixtures.demo_plan.DEMO_PLAN with no LLM/network call).
    """
    col1, col2, col3, col4 = st.columns([1, 4, 2, 1.5])

    with col1:
        st.markdown("## AgentMeal")

    # Day selector with highlighting for selected day
    with col2:
        st.markdown("**Selected day**")
        day_labels = [day_entry["label"] for day_entry in week]
        day_names = [day_entry["day"] for day_entry in week]

        day_cols = st.columns(7)
        for day_col, label, day_name in zip(day_cols, day_labels, day_names):
            with day_col:
                # Highlight the selected day with primary button style
                # Use callback to update selection immediately on first click
                button_type = "primary" if day_name == st.session_state[KEY_SELECTED_DAY] else "secondary"
                st.button(
                    label,
                    key=f"day_btn_{day_name}",
                    width="stretch",
                    type=button_type,
                    on_click=_on_day_click,
                    args=(day_name,)
                )

        selected_day = st.session_state[KEY_SELECTED_DAY]

    # Activity summary for the selected day (loaded from database)
    with col3:
        # Load activities from database for the selected day
        try:
            activities = activity_store.get_activities(selected_day)
            if activities:
                # Use the first activity from the database
                activity_data = activities[0]
                activity = activity_data.get("activity", "—")
                duration = activity_data.get("duration_minutes", 0)
                intensity = activity_data.get("intensity")
                intensity_text = f" · {intensity} intensity" if intensity else ""
                st.markdown(f"**Activity:** {activity} · {duration} min{intensity_text}")
            else:
                st.markdown("**Activity:** —")
        except Exception:
            # Fallback to fixture data if database lookup fails
            selected_day_entry = next((d for d in week if d["day"] == selected_day), None)
            if selected_day_entry:
                activity = selected_day_entry.get("activity", "—")
                duration = selected_day_entry.get("duration_min", 0)
                intensity = selected_day_entry.get("intensity")
                intensity_text = f" · {intensity} intensity" if intensity else ""
                st.markdown(f"**Activity:** {activity} · {duration} min{intensity_text}")

    # Buttons column: Generate plan (primary) and Demo plan (secondary) stacked vertically
    with col4:
        generate_clicked = st.button(
            "Generate plan", type="primary", key="generate_plan_btn", width="stretch"
        )
        demo_clicked = st.button(
            "Demo plan",
            key="demo_plan_btn",
            width="stretch",
            help="Reload a plan that was already generated, no LLM call.",
        )

    return selected_day, generate_clicked, demo_clicked
