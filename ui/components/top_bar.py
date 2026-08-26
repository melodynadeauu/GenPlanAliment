"""Top bar: brand mark, day selector, activity summary, generate button."""

import streamlit as st


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
    col1, col2, col3, col4, col5 = st.columns([1, 4, 2, 1.5, 1.5])

    with col1:
        st.markdown("## AgentMeal")

    # Day selector
    with col2:
        st.markdown("**Selected day**")
        day_labels = [day_entry["label"] for day_entry in week]
        day_names = [day_entry["day"] for day_entry in week]

        day_cols = st.columns(7)
        new_selected_day = selected_day
        for day_col, label, day_name in zip(day_cols, day_labels, day_names):
            with day_col:
                if st.button(label, key=f"day_btn_{day_name}", width="stretch"):
                    new_selected_day = day_name

        selected_day = new_selected_day

    # Activity summary for the selected day
    with col3:
        selected_day_entry = next((d for d in week if d["day"] == selected_day), None)
        if selected_day_entry:
            activity = selected_day_entry.get("activity", "—")
            duration = selected_day_entry.get("duration_min", 0)
            intensity = selected_day_entry.get("intensity")
            intensity_text = f" · {intensity} intensity" if intensity else ""
            st.markdown(f"**Activity:** {activity} · {duration} min{intensity_text}")

    with col4:
        generate_clicked = st.button(
            "Generate plan", type="primary", key="generate_plan_btn", width="stretch"
        )

    # Demo mode button (D1): reload a pre-generated plan, no LLM call, no network --
    # the fallback when the LLM quota is exhausted mid-demo.
    with col5:
        demo_clicked = st.button(
            "Demo plan",
            key="demo_plan_btn",
            width="stretch",
            help="Reload a plan that was already generated, no LLM call.",
        )

    return selected_day, generate_clicked, demo_clicked
