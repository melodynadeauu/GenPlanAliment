import streamlit as st


def render_meal_plan(plan: dict | None) -> None:
    """Render meals in a container.

    Args:
        plan: Generated meal plan dict or None

    If plan is None, shows empty state message.
    """
    st.markdown("### Plan de repas")

    if plan is None:
        st.info("Aucun plan généré — cliquez sur *Générer le plan*.")
        return

    with st.container(border=False):
        for meal in plan.get("meals", []):
            meal_name = meal.get("name", "Repas")
            meal_kcal = meal.get("kcal", 0)

            # Meal header
            st.markdown(f"**{meal_name}** · {meal_kcal} kcal")

            # Meal items
            for item in meal.get("items", []):
                food_name = item.get("food", "Aliment")
                grams = item.get("grams", 0)
                kcal = item.get("kcal", 0)
                source = item.get("source", "")
                source_status = item.get("source_status", "ok")

                if source_status == "ok":
                    badge_class = "badge-ok"
                else:
                    badge_class = "badge-warn"

                # Render item row with details aligned to the right
                item_html = f"""
                <div style="padding: 0.5rem 0; border-bottom: 1px solid #d7e0dd; display: flex; justify-content: space-between; align-items: center;">
                    <div>{food_name}</div>
                    <div style="font-size: 0.875rem; color: #71817c; text-align: right;">
                        {grams}g · {kcal} kcal · <span class="{badge_class}">{source}</span>
                    </div>
                </div>
                """
                st.markdown(item_html, unsafe_allow_html=True)

            st.markdown("")  # Spacing between meals
