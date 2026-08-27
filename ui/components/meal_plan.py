"""The day's meals, as cards in two columns so a full plan fits one screen."""

import streamlit as st


def _meal_card_html(meal: dict) -> str:
    """One meal card: header with its kcal, then a row per food."""
    name = meal.get("name", "Meal")
    rows = []
    for item in meal.get("items", []):
        warn = item.get("source_status") != "ok"
        source = item.get("source", "")
        # Only a failed lookup needs the source shown; a healthy FDC id stays quiet.
        source_html = (
            '<span class="am-src am-src-warn">estimated</span>'
            if warn
            else f'<span class="am-src">{source}</span>'
        )
        rows.append(
            '<div class="am-food">'
            f'<span class="am-food-name">{item.get("food", "Food")}</span>'
            f'<span class="am-food-g">{item.get("grams", 0):g} g</span>'
            f'<span class="am-food-kcal">{item.get("kcal", 0)} kcal</span>'
            f"{source_html}"
            "</div>"
        )

    return (
        '<div class="am-meal">'
        '<div class="am-meal-head">'
        f'<span class="am-meal-name">{name}</span>'
        f'<span class="am-meal-kcal">{meal.get("kcal", 0)} kcal</span>'
        "</div>" + "".join(rows) + "</div>"
    )


def _render_empty_state() -> None:
    """Explain what to do when no plan has been generated yet."""
    st.markdown(
        '<div class="am-empty">'
        '<div class="am-empty-h">No plan for this day yet</div>'
        '<p class="am-empty-p">Profile & preferences in the sidebar, pick the day above, then press <b>Generate plan</b>.</p>'
        "</div>",
        unsafe_allow_html=True,
    )


def render_meal_plan(plan: dict | None) -> None:
    """Render the meal cards, or the empty state when nothing is generated."""
    if plan is None:
        _render_empty_state()
        return

    meals = plan.get("meals", [])
    with st.container(key="meal_plan_section"):
        st.markdown(
            f'<div class="am-label am-label-meal">Meal plan<span>{len(meals)} meals · grams and kcal '
            "from USDA FoodData Central</span></div>",
            unsafe_allow_html=True,
        )

        left, right = st.columns(2, gap="medium")
        for index, meal in enumerate(meals):
            target_column = left if index % 2 == 0 else right
            with target_column:
                st.markdown(_meal_card_html(meal), unsafe_allow_html=True)
