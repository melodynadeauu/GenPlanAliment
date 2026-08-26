"""Fixed footer: guardrail badges + medical disclaimer."""

import streamlit as st


def render_guardrails_bar(plan: dict | None) -> None:
    """Render guardrail badges and medical disclaimer.

    Args:
        plan: Generated meal plan dict or None

    Renders nothing but the disclaimer if plan is None.
    """
    if plan is not None:
        st.markdown("### Guardrails")

        guardrails = plan.get("guardrails", [])
        if guardrails:
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

    st.markdown(
        "---\n"
        "**Disclaimer:** This is not medical advice. "
        "Consult a healthcare professional before changing your diet."
    )
