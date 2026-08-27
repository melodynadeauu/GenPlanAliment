"""Footer: medical disclaimer and the data sources behind the numbers."""

import streamlit as st


def render_footer() -> None:
    """Render the disclaimer and source credits."""
    st.markdown(
        '<div class="am-foot">'
        "<span><b>Not medical advice.</b> Consult a healthcare professional before "
        "changing your diet.</span>"
        "<span>Nutrition: <b>USDA FoodData Central</b></span>"
        "<span>Calorie burn: <b>Adult Compendium of Physical Activities</b> (MET)</span>"
        "<span>Energy: <b>Mifflin-St Jeor</b> · deficit capped at 25% of TDEE, floor 1200 kcal</span>"
        "</div>",
        unsafe_allow_html=True,
    )


# Kept so existing callers/imports keep working.
def render_guardrails_bar(plan: dict | None = None) -> None:
    """Deprecated alias for render_footer."""
    _ = plan
    render_footer()
