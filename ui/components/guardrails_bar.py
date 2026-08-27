"""Fixed footer: guardrail badges + medical disclaimer."""

import streamlit as st


def render_guardrails_bar(plan: dict | None) -> None:
    """Render guardrail badges and medical disclaimer.

    Args:
        plan: Generated meal plan dict or None

    Renders guardrails section only if there are guardrails to display.
    Always renders the disclaimer.
    """
    # Only render Guardrails section if plan exists and has guardrails
    if plan is not None:
        guardrails = plan.get("guardrails", [])
        if guardrails:
            st.markdown("### Guardrails")
            badge_html = ""
            for guardrail in guardrails:
                status = guardrail.get("status", "ok")
                message = guardrail.get("message", "")

                if status == "ok":
                    badge_class = "badge-ok"
                else:
                    badge_class = "badge-warn"

                badge_html += f'<span class="{badge_class}">{message}</span> '

            st.markdown(badge_html, unsafe_allow_html=True)

    # Always show disclaimer
    st.markdown(
        "---\n"
        "**Disclaimer:** This is not medical advice. "
        "Consult a healthcare professional before changing your diet."
    )
