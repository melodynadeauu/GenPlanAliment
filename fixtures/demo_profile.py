"""Default profile values, seeded into session_state on first run. Editable
afterward via the sidebar's profile form (ui.components.sidebar_profile)."""

DEMO_PROFILE = {
    "age": 45,
    # floats to match core.models.Profile and the sidebar's number_input bounds
    "weight_kg": 100.0,
    "height_cm": 196.0,
    "goal": "Weight loss",  # matches ui.adapters._GOAL_LABEL_TO_GOAL
}
