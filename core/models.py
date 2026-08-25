from dataclasses import dataclass

from core.types import Goal, Intensity

# A single activity entry can't outlast a day.
MAX_ACTIVITY_DURATION_MINUTES = 1440


@dataclass(frozen=True)
class Profile:
    """The user parameters that drive the calorie calculation."""

    age_years: int
    weight_kg: float
    height_cm: float
    goal: Goal


@dataclass(frozen=True)
class ActivityEntry:
    """One scheduled activity, translated from a raw data row."""

    activity: str
    duration_minutes: int
    intensity: Intensity

    def __post_init__(self) -> None:
        if self.duration_minutes > MAX_ACTIVITY_DURATION_MINUTES:
            raise ValueError(
                f"duration_minutes ({self.duration_minutes}) exceeds "
                f"MAX_ACTIVITY_DURATION_MINUTES ({MAX_ACTIVITY_DURATION_MINUTES}, 24h)."
            )

    @classmethod
    def from_row(cls, row: dict) -> "ActivityEntry":
        """Build an ActivityEntry from a data.activity.store.get_activities() row."""
        return cls(
            activity=row["activity"],
            duration_minutes=row["duration_minutes"],
            intensity=Intensity(row["intensity"]),
        )
