"""Streamlit entry point. Wires components together — no business logic here.

Page order mirrors the product's own logic, top to bottom:
    fixed masthead → training week → calorie target → the plan.
"""

import streamlit as st

from core.agent import plan_view
from ui import adapters
from ui.energy import load_day_activities
from ui.layout import configure_page
from ui.state import (
    init_state,
    KEY_SELECTED_DAY,
    KEY_GENERATED_PLAN,
    KEY_PLAN_DAY,
    KEY_IS_GENERATING,
    KEY_GENERATING_DAY,
    KEY_GENERATION_ERROR,
    KEY_PROFILE_AGE,
    KEY_PROFILE_WEIGHT,
    KEY_PROFILE_HEIGHT,
    KEY_PROFILE_GOAL,
)
from ui.components.top_bar import render_masthead
from ui.components.week_strip import render_week_strip
from ui.components.energy_chain import render_energy_chain
from ui.components.sidebar_profile import render_profile_section
from ui.components.sidebar_preferences import render_preferences_section
from ui.components.totals_row import render_plan_summary
from ui.components.meal_plan import render_meal_plan
from ui.components.guardrails_bar import render_footer

from fixtures.demo_plan import DEMO_PLAN
from fixtures.demo_week import DEMO_WEEK

# Error codes GenerationResult.error can carry (see core/agent/llm_adapter.py), each
# with a message a UI user can act on. Mirrors main.py's ERROR_MESSAGES.
ERROR_MESSAGES = {
    "rate_limited": "Too many requests right now. Wait a bit and try again, or press "
    "Demo plan to show a ready-made one.",
    "timeout": "The request timed out and the retries were used up. Try again.",
    "api_error": "Could not reach the plan service (connection or setup error). Check "
    "LLM_PROVIDER and the matching API key in .env.",
    "invalid_output": "No valid plan came back, even after the final attempt. Try again, "
    "or press Demo plan.",
}


def _current_profile():
    """Build a core Profile from the sidebar's current values."""
    return adapters.profile_from_dict(
        {
            "age": st.session_state[KEY_PROFILE_AGE],
            "weight_kg": st.session_state[KEY_PROFILE_WEIGHT],
            "height_cm": st.session_state[KEY_PROFILE_HEIGHT],
            "goal": st.session_state[KEY_PROFILE_GOAL],
        }
    )


def main() -> None:
    """App entry point: sidebar inputs, then the day's target and its plan."""
    configure_page()
    init_state()

    # Widgets that could fire a rerun mid-generation (and cancel the in-flight
    # LLM call) are rendered disabled for as long as this flag is set. See the
    # `is_generating` block below for the two-rerun sequence this drives.
    is_generating = st.session_state[KEY_IS_GENERATING]

    with st.sidebar:
        render_profile_section(disabled=is_generating)
        st.divider()
        render_preferences_section(disabled=is_generating)

    profile = _current_profile()

    generate_clicked, demo_clicked = render_masthead(disabled=is_generating)
    selected_day = render_week_strip(DEMO_WEEK, profile, disabled=is_generating)
    st.session_state[KEY_SELECTED_DAY] = selected_day

    day_entry = next((d for d in DEMO_WEEK if d["day"] == selected_day), DEMO_WEEK[0])
    activity_rows = load_day_activities(selected_day, DEMO_WEEK)
    target_kcal = render_energy_chain(profile, day_entry["label"], activity_rows)

    # D1 (quota fallback): loads the pre-generated fixture, no LLM/network call.
    if demo_clicked and not is_generating:
        st.session_state[KEY_GENERATED_PLAN] = DEMO_PLAN
        st.session_state[KEY_PLAN_DAY] = DEMO_PLAN.get("day", selected_day)

    if generate_clicked and not is_generating:
        # Don't generate inline: the widgets above have already rendered enabled
        # for this run, so disabling them now wouldn't reach the browser until
        # after the (blocking) generation call finishes. Flip the flag, snapshot
        # the day, and rerun -- the *next* run renders everything disabled
        # before the actual generation starts.
        st.session_state[KEY_IS_GENERATING] = True
        st.session_state[KEY_GENERATING_DAY] = selected_day
        st.rerun()

    if is_generating:
        generating_day = st.session_state[KEY_GENERATING_DAY]
        generating_entry = next(
            (d for d in DEMO_WEEK if d["day"] == generating_day), day_entry
        )
        day = adapters.weekday_from_ui_day(generating_day)
        with st.spinner(f"Building {generating_entry['label'].title()}'s meals — "
                        f"searching USDA foods and checking guardrails…"):
            view, error = plan_view.generate_daily_plan_view(profile, day)

        if error:
            st.session_state[KEY_GENERATION_ERROR] = error
        else:
            st.session_state[KEY_GENERATED_PLAN] = view
            st.session_state[KEY_PLAN_DAY] = generating_day
            st.session_state[KEY_GENERATION_ERROR] = None

        st.session_state[KEY_IS_GENERATING] = False
        st.session_state[KEY_GENERATING_DAY] = None
        st.rerun()

    generation_error = st.session_state[KEY_GENERATION_ERROR]
    if generation_error:
        st.error(ERROR_MESSAGES.get(generation_error, generation_error))
        st.session_state[KEY_GENERATION_ERROR] = None

    st.markdown('<div class="am-rule"></div>', unsafe_allow_html=True)

    plan = st.session_state[KEY_GENERATED_PLAN]
    plan_day = st.session_state[KEY_PLAN_DAY]
    render_plan_summary(
        plan,
        target_kcal,
        plan_day_label=plan_day.capitalize() if plan_day else None,
        selected_day_label=selected_day.capitalize(),
    )
    render_meal_plan(plan)
    render_footer()


if __name__ == "__main__":
    main()
