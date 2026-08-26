"""Four stat cards: target kcal, actual kcal, protein, meal count."""

import streamlit as st


def render_totals_row(plan: dict | None) -> None:
    """Render the totals row with 4 stat cards.

    Args:
        plan: Generated meal plan dict or None (before first generation)

    If plan is None, shows placeholder dashes in all cards.
    """
    col1, col2, col3, col4 = st.columns(4)

    # Extract values from plan or use placeholder
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

    # Stat card 1: Target kcal
    with col1:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-card-value">{target_kcal}</div>
                <div class="stat-card-label">kcal cible</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Stat card 2: Actual kcal
    with col2:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-card-value">{actual_kcal}</div>
                <div class="stat-card-label">kcal réel</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Stat card 3: Protein
    with col3:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-card-value">{protein_g}</div>
                <div class="stat-card-label">protéines (g)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Stat card 4: Meal count
    with col4:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-card-value">{meal_count}</div>
                <div class="stat-card-label">repas</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
