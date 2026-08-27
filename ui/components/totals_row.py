"""Plan summary: planned kcal against the target, plus the safety notes."""

import streamlit as st

from ui.icons import icon

# Guardrail messages come from the agent in engineering terms; a demo audience
# needs the consequence, not the retry count.
_HUMAN_MESSAGES = {
    "Plan non-compliant after 2 attempts": (
        "Could not land inside the calorie window after 2 tries — this is the "
        "closest attempt. Check the total before using it."
    ),
}


def humanize(message: str) -> str:
    """Rewrite a known engineering guardrail message in plain language."""
    for prefix, replacement in _HUMAN_MESSAGES.items():
        if message.startswith(prefix):
            return replacement
    return message


def _kcal(value: float) -> str:
    """Thin-space thousands, no decimals -- how every figure on the page reads."""
    return f"{value:,.0f}".replace(",", " ")


def render_plan_summary(
    plan: dict | None,
    target_kcal: float,
    plan_day_label: str | None = None,
    selected_day_label: str | None = None,
) -> None:
    """Render planned-vs-target with a meter, or nothing when there is no plan.

    The empty case belongs to the meal plan's empty state, which explains the
    pipeline -- two "nothing here yet" boxes stacked would just be noise.
    """
    if plan is None:
        return

    planned = plan.get("total_kcal", 0)
    protein = plan.get("total_protein_g", 0)
    target = plan.get("target_kcal") or target_kcal or 0
    item_count = sum(len(meal.get("items", [])) for meal in plan.get("meals", []))
    day_note = f" · {plan_day_label}" if plan_day_label else ""

    gap = planned - target
    within_window = abs(gap) <= max(target * 0.05, 50)
    fill_ratio = min(1.0, (planned / target) if target else 0)
    over_class = "am-meter-over" if planned > target else ""

    chip_class = "am-chip-ok" if within_window else "am-chip-warn"
    chip_text = "on target" if within_window else f"{gap:+.0f} kcal off target"
    gap_label = "left to fill" if gap < 0 else "over target"

    st.markdown(
        '<div class="am-sum">'
        '<div class="am-sum-top">'
        f'<span class="am-sum-big">{_kcal(planned)}</span>'
        f'<span class="am-sum-of">kcal planned of {_kcal(target)} target{day_note}</span>'
        f'<span class="am-sum-chip {chip_class}">{chip_text}</span>'
        "</div>"
        f'<div class="am-meter"><div class="am-meter-fill {over_class}" '
        f'style="transform:scaleX({fill_ratio:.3f})"></div></div>'
        '<div class="am-sum-foot">'
        f"<span>protein <b>{protein} g</b></span>"
        f"<span>meals <b>{len(plan.get('meals', []))}</b></span>"
        f"<span>items <b>{item_count}</b></span>"
        f"<span>{gap_label} <b>{_kcal(abs(gap))} kcal</b></span>"
        "</div></div>",
        unsafe_allow_html=True,
    )

    # A plan belongs to the day it was built for; switching days must not look
    # like the plan followed along.
    if plan_day_label and selected_day_label and plan_day_label != selected_day_label:
        st.markdown(
            f'<div class="am-note">{icon("block", 15)}<span>This plan was built for '
            f"<b>{plan_day_label}</b>. Press <b>Generate plan</b> to rebuild it for "
            f"{selected_day_label}.</span></div>",
            unsafe_allow_html=True,
        )

    for guardrail in plan.get("guardrails", []):
        if guardrail.get("status") == "warn":
            st.markdown(
                f'<div class="am-note">{icon("block", 15)}'
                f'<span>{humanize(guardrail.get("message", ""))}</span></div>',
                unsafe_allow_html=True,
            )
