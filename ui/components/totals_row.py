"""Four stat cards: target kcal, actual kcal, protein, meal count."""

import streamlit as st


def render_totals_row(plan: dict | None) -> None:
    """Render the totals row with 4 stat cards. Shows dashes if no plan yet."""
    col1, col2, col3, col4 = st.columns(4)

    if plan is None:
        target_kcal = "—"
        actual_kcal = "—"
        protein_g = "—"
        meal_count = "—"
    else:
        target_kcal = plan.get("target_kcal", "—")
        actual_kcal = plan.get("total_kcal", "—")
        protein_g = plan.get("total_protein_g", "—")
        meal_count = len(plan.get("meals", []))

    with col1:
        st.markdown(
            f'<div class="stat-card"><div class="stat-card-value">{target_kcal}</div>'
            '<div class="stat-card-label">target kcal</div></div>',
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f'<div class="stat-card"><div class="stat-card-value">{actual_kcal}</div>'
            '<div class="stat-card-label">actual kcal</div></div>',
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            f'<div class="stat-card"><div class="stat-card-value">{protein_g}</div>'
            '<div class="stat-card-label">protein (g)</div></div>',
            unsafe_allow_html=True,
        )

    with col4:
        st.markdown(
            f'<div class="stat-card"><div class="stat-card-value">{meal_count}</div>'
            '<div class="stat-card-label">meals</div></div>',
            unsafe_allow_html=True,
        )
