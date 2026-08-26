"""Streamlit entry point. Wires components together — no business logic here."""

import streamlit as st

from core.agent import plan_view
from ui import adapters
from ui.layout import configure_page
from ui.state import (
    init_state,
    KEY_SELECTED_DAY,
    KEY_GENERATED_PLAN,
    KEY_PROFILE_AGE,
    KEY_PROFILE_WEIGHT,
    KEY_PROFILE_HEIGHT,
    KEY_PROFILE_GOAL,
)
from ui.components.top_bar import render_top_bar
from ui.components.sidebar_profile import render_profile_section
from ui.components.sidebar_preferences import render_preferences_section
from ui.components.totals_row import render_totals_row
from ui.components.meal_plan import render_meal_plan
from ui.components.guardrails_bar import render_guardrails_bar

from fixtures.demo_plan import DEMO_PLAN
from fixtures.demo_week import DEMO_WEEK

# Error codes GenerationResult.error can carry (see core/agent/llm_adapter.py), each
# with a message a UI user can act on. Mirrors main.py's ERROR_MESSAGES.
ERROR_MESSAGES = {
    "rate_limited": "The LLM provider rate-limited the request. Wait a bit and try again.",
    "timeout": "The LLM provider timed out (or errored transiently) and retries were exhausted.",
    "api_error": "Could not reach the LLM provider (connection or setup error). Check "
    "LLM_PROVIDER and the matching API key in .env.",
    "invalid_output": "The LLM never produced a valid plan (bad tool call or output "
    "that failed PlanPropose validation), even after the forced final attempt.",
}


def main() -> None:
    """Main app orchestrator.

    Flow:
    1. Configure page & CSS
    2. Initialize session state
    3. Render top bar (day selector + generate button)
    4. If generate button clicked: call plan_view.generate_daily_plan_view and store
       the view (or show an error) in session state
    5. Render sidebar (profile + preferences)
    6. Render main content (totals + meal plan + guardrails)
    """
    # Setup
    configure_page()
    init_state()

    # Top bar: day selector + generate button + demo button
    selected_day, generate_clicked, demo_clicked = render_top_bar(
        week=DEMO_WEEK,
        selected_day=st.session_state[KEY_SELECTED_DAY],
    )
    st.session_state[KEY_SELECTED_DAY] = selected_day

    # Demo mode handler (D1): loads the pre-generated fixture, no LLM/network call --
    # the fallback when the LLM quota is exhausted mid-demo.
    if demo_clicked:
        st.session_state[KEY_GENERATED_PLAN] = DEMO_PLAN

    # Generate button handler
    if generate_clicked:
        profile_dict = {
            "age": st.session_state[KEY_PROFILE_AGE],
            "weight_kg": st.session_state[KEY_PROFILE_WEIGHT],
            "height_cm": st.session_state[KEY_PROFILE_HEIGHT],
            "goal": st.session_state[KEY_PROFILE_GOAL],
        }
        profile = adapters.profile_from_dict(profile_dict)
        day = adapters.weekday_from_ui_day(selected_day)

        with st.spinner("Génération du plan…"):
            view, error = plan_view.generate_daily_plan_view(profile, day)

        if error:
            st.error(ERROR_MESSAGES.get(error, error))
        else:
            st.session_state[KEY_GENERATED_PLAN] = view

    # Sidebar
    with st.sidebar:
        render_profile_section()
        st.divider()
        render_preferences_section()

    # Main content
    plan = st.session_state[KEY_GENERATED_PLAN]
    render_totals_row(plan)
    render_meal_plan(plan)
    render_guardrails_bar(plan)


if __name__ == "__main__":
    main()
