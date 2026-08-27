"""The calorie target, shown as the arithmetic that produced it.

Every step here is computed by ui.energy from the same pure functions
core.agent.plan_generator uses, so the chain is the real derivation and not a
decorative restatement of it -- and it updates the moment a day or a profile
field changes, before any plan exists.
"""

import streamlit as st

from core.models import Profile
from fixtures.demo_week import display_for
from ui.energy import GOAL_LABEL, compute_energy


def _step(label: str, value: str, sub: str = "", css_class: str = "") -> str:
    sub_html = f'<div class="am-step-sub">{sub}</div>' if sub else ""
    return (
        f'<div class="am-step {css_class}">'
        f'<div class="am-step-lab">{label}</div>'
        f'<div class="am-step-val">{value}</div>'
        f"{sub_html}"
        "</div>"
    )


def _arrow(symbol: str, css_class: str = "") -> str:
    return f'<div class="am-arrow {css_class}">{symbol}</div>'


def render_energy_chain(profile: Profile, day_label: str, rows: list[dict]) -> float:
    """Render the BMR → activity → TDEE → goal → target chain.

    Returns the target kcal, so the caller can compare a generated plan against it.
    """
    energy = compute_energy(profile, rows)

    if rows:
        # The chain has the page's full width, so this is where every session
        # that went into the burn gets named -- the day card only has room for
        # how many there are.
        burn_sub = "".join(
            f'<span class="am-step-part">'
            f'{display_for(row["activity"])} · {row["duration_minutes"]} min</span>'
            for row in rows
        )
    else:
        burn_sub = "Rest day"

    goal_label = GOAL_LABEL.get(profile.goal.value, profile.goal.value)
    adjustment = energy["adjustment"]
    adjustment_text = f"{abs(adjustment):,.0f}".replace(",", " ")
    adjustment_class = "am-minus" if adjustment < 0 else "am-plus"

    st.markdown(
        '<div class="am-label">How this target is calculated'
        "<span>Updates as you change the day or your profile</span></div>"
        '<div class="am-chain">'
        + _step(
            "Body at rest",
            f"{energy['base']:,.0f}".replace(",", " "),
            f"{profile.age_years} y · {profile.weight_kg:.0f} kg · {profile.height_cm:.0f} cm",
        )
        + _arrow("+", "am-plus")
        + _step(
            f"{day_label.title()} training",
            f"+{energy['burn']:,.0f}".replace(",", " ") if rows else "+0",
            burn_sub,
        )
        + _arrow("=")
        + _step(
            "Burned per day",
            f"{energy['tdee']:,.0f}".replace(",", " "),
            "Total daily energy expenditure",
        )
        + _arrow("−" if adjustment < 0 else "+", adjustment_class)
        + _step(
            f"Goal · {goal_label}",
            adjustment_text,
            "Safety-capped deficit" if adjustment < 0 else "Surplus",
        )
        + _step(
            "Daily target",
            f"{energy['target']:,.0f} kcal".replace(",", " "),
            css_class="am-step-target",
        )
        + "</div>",
        unsafe_allow_html=True,
    )

    return energy["target"]
