"""Inline SVG icon set.

One drawn family instead of emoji: 16px box, 1.5px stroke, round caps, no fill,
`currentColor` throughout -- so an icon inherits whatever colour its row already
uses (ink on a paper card, white on the selected day card) with no extra rules.

Keep every path to plain geometry. These are marks, not pictures.
"""

_BOX = (
    '<svg class="am-i" viewBox="0 0 24 24" width="{size}" height="{size}" '
    'fill="none" stroke="currentColor" stroke-width="1.6" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{body}</svg>'
)

_PATHS = {
    # --- training ---------------------------------------------------------
    "dumbbell": '<path d="M4 9v6M7 7v10M17 7v10M20 9v6M7 12h10"/>',
    "kettlebell": '<path d="M9 8a3 3 0 0 1 6 0"/>'
                  '<path d="M15 8c2.4 1.3 3.5 3.5 3.5 6a4 4 0 0 1-4 4h-5a4 4 0 0 1-4-4c0-2.5 1.1-4.7 3.5-6"/>',
    "footsteps": '<rect x="4" y="4" width="5" height="9" rx="2.5"/>'
                 '<rect x="15" y="11" width="5" height="9" rx="2.5"/>',
    "sprint": '<path d="M3 8h7M3 12h10M3 16h6"/><path d="M15 7l5 5-5 5"/>',
    "stretch": '<path d="M5 19c0-7 4-11 8-11"/><circle cx="17" cy="6" r="2.5"/>'
               '<path d="M13 8h4"/>',
    "ball": '<circle cx="12" cy="12" r="8.5"/>'
            '<path d="M12 7.5l4 2.9-1.5 4.7h-5L8 10.4z"/>'
            '<path d="M12 3.5v4M19.6 9.6l-3.6 1M16.5 15.1l2.3 3.1M7.5 15.1l-2.3 3.1M4.4 9.6l3.6 1"/>',
    "bike": '<circle cx="6" cy="17" r="3.5"/><circle cx="18" cy="17" r="3.5"/>'
            '<path d="M6 17l4-8h5l3 8M9 9h4"/>',
    "moon": '<path d="M19 14.5A7.5 7.5 0 0 1 9.5 5a7.5 7.5 0 1 0 9.5 9.5z"/>',
    # --- meals ------------------------------------------------------------
    "cup": '<path d="M4 9h12v6a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4z"/>'
           '<path d="M16 11h2a2.5 2.5 0 0 1 0 5h-2"/><path d="M8 3v3M12 3v3"/>',
    "bowl": '<path d="M3.5 11h17a8.5 8.5 0 0 1-17 0z"/><path d="M9 7.5c0-1.5 3-1.5 3-3"/>'
            '<path d="M14 7.5c0-1.5 2-1.5 2-2.5"/>',
    "plate": '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="4"/>',
    "apple": '<path d="M12 8.5c-3.5-2.5-8 .5-7 5s4.5 7 7 5c2.5 2 6-.5 7-5s-3.5-7.5-7-5z"/>'
             '<path d="M12 8.5V5M12 5c0-1.5 1.5-2.5 3-2.5"/>',
    # --- inputs and pipeline ----------------------------------------------
    "check": '<path d="M4 12.5l5 5L20 6.5"/>',
    "block": '<circle cx="12" cy="12" r="8.5"/><path d="M6 18L18 6"/>',
    "person": '<circle cx="12" cy="8" r="3.5"/><path d="M4.5 20a7.5 7.5 0 0 1 15 0"/>',
    "target": '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="3.5"/>'
              '<path d="M12 .5v3M12 20.5v3M.5 12h3M20.5 12h3"/>',
    "chip": '<rect x="6.5" y="6.5" width="11" height="11" rx="2"/>'
            '<path d="M10 3v3.5M14 3v3.5M10 17.5V21M14 17.5V21M3 10h3.5M3 14h3.5'
            'M17.5 10H21M17.5 14H21"/>',
    "arrow": '<path d="M4 12h15M14 7l5 5-5 5"/>',
    "chevron-down": '<path d="M6 9l6 6 6-6"/>',
    "chevron-up": '<path d="M6 15l6-6 6 6"/>',
}

# Compendium activity name -> icon key. Anything unmapped falls back to a
# neutral mark rather than an empty slot.
ACTIVITY_ICONS = {
    "upper body strength training": "dumbbell",
    "lower body strength training": "kettlebell",
    "walk": "footsteps",
    "running": "sprint",
    "stretching": "stretch",
    "soccer": "ball",
    "bike ride": "bike",
}

MEAL_ICONS = {
    "Breakfast": "cup",
    "Lunch": "bowl",
    "Dinner": "plate",
    "Snack": "apple",
}


def icon(name: str, size: int = 16) -> str:
    """Return the inline `<svg>` for `name`, or an empty string if unknown."""
    body = _PATHS.get(name)
    if body is None:
        return ""
    return _BOX.format(size=size, body=body)


def activity_icon(activity: str, size: int = 16) -> str:
    """Icon for a compendium activity name; `dumbbell` when unmapped."""
    return icon(ACTIVITY_ICONS.get(activity, "dumbbell"), size)


def meal_icon(meal_name: str, size: int = 16) -> str:
    """Icon for a meal name; `plate` when unmapped."""
    return icon(MEAL_ICONS.get(meal_name, "plate"), size)
