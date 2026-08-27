"""Weekly activity calendar fallback -- mirrors the rows seeded into
data/activity/meal_prep.db by data.activity.seed_activity_calendar, so the UI
shows the same week whether or not the database has been seeded.

Row keys match data.activity.store.get_activities() (activity, duration_minutes,
intensity) plus the display-only `label`, `short` and `icon`.
"""

DEMO_WEEK = [
    {
        "day": "monday", "label": "MON", "icon": "🏋",
        "activity": "upper body strength training", "short": "Upper body",
        "duration_minutes": 60, "intensity": "moderate",
    },
    {
        "day": "tuesday", "label": "TUE", "icon": "🚶",
        "activity": "walk", "short": "Walk",
        "duration_minutes": 30, "intensity": "moderate",
    },
    {
        "day": "wednesday", "label": "WED", "icon": "🦵",
        "activity": "lower body strength training", "short": "Lower body",
        "duration_minutes": 60, "intensity": "moderate",
    },
    {
        "day": "thursday", "label": "THU", "icon": "🧘",
        "activity": "stretching", "short": "Stretching",
        "duration_minutes": 15, "intensity": "low",
    },
    {
        "day": "friday", "label": "FRI", "icon": "🏃",
        "activity": "running", "short": "Running",
        "duration_minutes": 45, "intensity": "high",
    },
    {
        "day": "saturday", "label": "SAT", "icon": "⚽",
        "activity": "soccer", "short": "Soccer",
        "duration_minutes": 90, "intensity": "high",
    },
    {
        "day": "sunday", "label": "SUN", "icon": "🚴",
        "activity": "bike ride", "short": "Bike ride",
        "duration_minutes": 40, "intensity": "low",
    },
]

# Display name + icon for an activity coming out of the database, which stores
# the long compendium-style name only.
ACTIVITY_DISPLAY = {
    "upper body strength training": ("Upper body", "🏋"),
    "lower body strength training": ("Lower body", "🦵"),
    "walk": ("Walk", "🚶"),
    "running": ("Running", "🏃"),
    "stretching": ("Stretching", "🧘"),
    "soccer": ("Soccer", "⚽"),
    "bike ride": ("Bike ride", "🚴"),
}


def display_for(activity: str) -> tuple[str, str]:
    """(short label, icon) for `activity`; a title-cased fallback if unknown."""
    return ACTIVITY_DISPLAY.get(activity, (activity.capitalize(), "•"))
