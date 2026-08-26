"""Default profile values, seeded into session_state on first run. The user
can then edit them via the sidebar's profile form (ui.components.sidebar_profile).
"""

DEMO_PROFILE = {
    "age": 45,
    # weight_kg/height_cm are floats to match core.models.Profile's field types
    # and the sidebar's number_input min_value/max_value (see sidebar_profile.py).
    "weight_kg": 100.0,
    "height_cm": 196.0,
    "goal": "Perte de poids",  # French label, shown as-is
}
