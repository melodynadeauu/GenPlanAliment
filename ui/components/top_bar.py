"""Masthead: wordmark, one-line explanation of the product, and the two actions."""

import streamlit as st


def render_masthead(disabled: bool = False) -> tuple[bool, bool]:
    """Render the fixed masthead row.

    Args:
        disabled: True while a plan is generating -- both buttons are disabled so a
            click can't fire a rerun that cancels the in-flight generation.

    Returns:
        (generate_clicked, demo_clicked) -- demo reloads fixtures.demo_plan.DEMO_PLAN
        with no network call (D1: the fallback when the quota runs out mid-demo).
    """
    row = st.container(key="masthead")
    with row:
        brand, gen_col, demo_col = st.columns([5.5, 1.2, 1.2], vertical_alignment="center")

        with brand:
            st.markdown(
                '<div class="am-word">Agent<em>MealPrep</em></div>',
                unsafe_allow_html=True,
            )

        with gen_col:
            generate_clicked = st.button(
                "Generate plan",
                type="primary",
                key="generate_plan_btn",
                width="stretch",
                help="Builds meals for the selected day from your profile, activity and preferences.",
                disabled=disabled,
            )

        with demo_col:
            demo_clicked = st.button(
                "Demo plan",
                key="demo_plan_btn",
                width="stretch",
                help="Loads a ready-made example plan, without generating one.",
                disabled=disabled,
            )

    return generate_clicked, demo_clicked
