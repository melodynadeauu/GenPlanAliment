"""Top bar: brand mark, day selector, activity summary, generate button."""

import streamlit as st


def render_top_bar(week: list[dict], selected_day: str) -> tuple[str, bool, bool]:
    """Render the fixed top bar.

    Args:
        week: List of day dicts with keys: day, label, activity, duration_min, intensity
        selected_day: Currently selected day name (e.g., "mercredi")

    Returns:
        (new_selected_day, generate_clicked, demo_clicked): Updated day, generate
        button state, and demo button state (D1: filet de sécurité anti-quota --
        recharge fixtures.demo_plan.DEMO_PLAN with no LLM/network call).
    """
    col1, col2, col3, col4, col5 = st.columns([1, 4, 2, 1.5, 1.5])

    # Brand mark
    with col1:
        st.markdown("## AgentMeal")

    # Day selector
    with col2:
        st.markdown("**Jour sélectionné**")
        day_labels = [day_entry["label"] for day_entry in week]
        day_names = [day_entry["day"] for day_entry in week]

        # Create day buttons in a row (simplified approach)
        day_cols = st.columns(7)
        new_selected_day = selected_day
        for i, (day_col, label, day_name) in enumerate(zip(day_cols, day_labels, day_names)):
            with day_col:
                button_key = f"day_btn_{day_name}"
                if st.button(label, key=button_key, use_container_width=True):
                    new_selected_day = day_name

        selected_day = new_selected_day

    # Activity summary for selected day
    with col3:
        selected_day_entry = next(
            (day_entry for day_entry in week if day_entry["day"] == selected_day),
            None,
        )
        if selected_day_entry:
            activity = selected_day_entry.get("activity", "—")
            duration = selected_day_entry.get("duration_min", 0)
            intensity = selected_day_entry.get("intensity", "—")

            if intensity is None:
                intensity_text = ""
            else:
                intensity_text = f" · intensité {intensity}"

            summary = f"{activity} · {duration} min{intensity_text}"
            st.markdown(f"**Activité:** {summary}")

    # Generate button
    with col4:
        generate_clicked = st.button(
            "Générer le plan",
            type="primary",
            key="generate_plan_btn",
            use_container_width=True,
        )

    # Demo mode button (D1): recharge a pre-generated plan, no LLM call, no network --
    # the fallback when the LLM quota is exhausted mid-demo.
    with col5:
        demo_clicked = st.button(
            "Plan de démo",
            key="demo_plan_btn",
            use_container_width=True,
            help="Recharge un plan déjà généré, sans appel LLM.",
        )

    return selected_day, generate_clicked, demo_clicked
