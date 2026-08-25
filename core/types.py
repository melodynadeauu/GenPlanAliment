"""Shared domain types used across the data layer and business logic."""
from enum import Enum


class Weekday(str, Enum):
    """A valid day of the week, in schedule order."""

    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class Intensity(str, Enum):
    """Perceived intensity level of an activity."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class Goal(str, Enum):
    """The user's nutrition objective."""

    WEIGHT_LOSS = "weight_loss"
    MAINTENANCE = "maintenance"
    MUSCLE_GAIN = "muscle_gain"
