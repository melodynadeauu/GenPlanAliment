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
