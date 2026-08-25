"""MET (Metabolic Equivalent of Task) values for the activities tracked in
`activity_calendar`, broken down by intensity level.

Source: Adult Compendium of Physical Activities
        https://pacompendium.com/adult-compendium/

Each entry gives the compendium activity `code` and its `met` value for the
matching intensity. Activity names match the `activity` column values used
in `activity_calendar` / `ACTIVITY_WEEK`.
"""
import warnings

from core.types import Intensity

MET_SOURCE = "https://pacompendium.com/adult-compendium/"

ACTIVITY_MET = {
    "bike ride": {
        Intensity.LOW: {"code": "01020", "met": 6.8},
        Intensity.MODERATE: {"code": "01030", "met": 8.0},
        Intensity.HIGH: {"code": "01040", "met": 10.0},
    },
    "soccer": {
        Intensity.LOW: {"code": "15615", "met": 3.5},
        Intensity.MODERATE: {"code": "15610", "met": 7.0},
        Intensity.HIGH: {"code": "15605", "met": 9.5},
    },
    "running": {
        Intensity.LOW: {"code": "12028", "met": 6.5},
        Intensity.MODERATE: {"code": "12060", "met": 10.5},
        Intensity.HIGH: {"code": "12120", "met": 14.8},
    },
    "stretching": {
        Intensity.LOW: {"code": "02101", "met": 2.3},
        Intensity.MODERATE: {"code": "02101", "met": 2.3},
        Intensity.HIGH: {"code": "02101", "met": 2.3},
    },
    "lower body strength training": {
        Intensity.LOW: {"code": "02054", "met": 3.5},
        Intensity.MODERATE: {"code": "02052", "met": 5.0},
        Intensity.HIGH: {"code": "02050", "met": 6.0},
    },
    "upper body strength training": {
        Intensity.LOW: {"code": "02054", "met": 3.5},
        Intensity.MODERATE: {"code": "02052", "met": 5.0},
        Intensity.HIGH: {"code": "02050", "met": 6.0},
    },
    "walk": {
        Intensity.LOW: {"code": "17152", "met": 2.8},
        Intensity.MODERATE: {"code": "17190", "met": 3.8},
        Intensity.HIGH: {"code": "17220", "met": 5.5},
    },
}

# Generic estimate used when an activity has no compendium entry above.
# Not sourced from the compendium - just a rough low/moderate/high fallback.
_UNKNOWN_ACTIVITY_MET = {
    Intensity.LOW: 3,
    Intensity.MODERATE: 5,
    Intensity.HIGH: 7,
}


def get_met(activity: str, intensity: Intensity) -> float:
    """Return the MET value for `activity` at `intensity`.

    If `activity` has no entry in ACTIVITY_MET, emits a warning and returns
    a generic fallback MET instead.

    Raises ValueError if `intensity` isn't a valid Intensity.
    """
    intensity = Intensity(intensity)

    if activity not in ACTIVITY_MET:
        warnings.warn(
            f"No MET data for activity '{activity}'; using fallback MET "
            f"value for intensity '{intensity.value}'.",
            stacklevel=2,
        )
        return _UNKNOWN_ACTIVITY_MET[intensity]

    return ACTIVITY_MET[activity][intensity]["met"]
