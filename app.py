"""Streamlit entry point. Wires components together — no business logic here."""

import streamlit as st

from ui.layout import configure_page
from ui.state import (
    init_state,
    KEY_SELECTED_DAY,
    KEY_GENERATED_PLAN,
)
from ui.components.top_bar import render_top_bar
from ui.components.sidebar_profile import render_profile_section
from ui.components.sidebar_preferences import render_preferences_section
from ui.components.totals_row import render_totals_row
from ui.components.meal_plan import render_meal_plan
from ui.components.guardrails_bar import render_guardrails_bar

from fixtures.demo_profile import DEMO_PROFILE
from fixtures.demo_preferences import DEMO_LIKES, DEMO_DISLIKES
from fixtures.demo_week import DEMO_WEEK
from fixtures.demo_plan import DEMO_PLAN


def main() -> None:
    """Main app orchestrator.

    Flow:
    1. Configure page & CSS
    2. Initialize session state
    3. Render top bar (day selector + generate button)
    4. If generate button clicked: store DEMO_PLAN in session state
    5. Render sidebar (profile + preferences)
    6. Render main content (totals + meal plan + guardrails)
    """
    # Setup
    configure_page()
    init_state()

    # Top bar: day selector + generate button
    selected_day, generate_clicked = render_top_bar(
        week=DEMO_WEEK,
        selected_day=st.session_state[KEY_SELECTED_DAY],
    )
    st.session_state[KEY_SELECTED_DAY] = selected_day

    # Generate button handler: write to session state (Rule D3: no blocking calls here)
    if generate_clicked:
        # TODO(agent): replace DEMO_PLAN with core.agent.generate_plan(...)
        st.session_state[KEY_GENERATED_PLAN] = DEMO_PLAN

    # Sidebar
    with st.sidebar:
        render_profile_section(DEMO_PROFILE)
        st.divider()
        render_preferences_section(DEMO_LIKES, DEMO_DISLIKES)

    # Main content
    plan = st.session_state[KEY_GENERATED_PLAN]
    render_totals_row(plan)
    render_meal_plan(plan)
    render_guardrails_bar(plan)


if __name__ == "__main__":
    main()
