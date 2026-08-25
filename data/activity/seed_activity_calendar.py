"""
Seed meal_prep.db with the weekly activity calendar.

The table itself is created by store.connect(); this script only inserts
the initial rows, and only if the table is empty.

Usage (from the project root):
    python -m data.activity.seed_activity_calendar
"""
from core.types import Intensity, Weekday
from .store import DB_PATH, connect

ACTIVITY_WEEK = [
    (Weekday.MONDAY.value, "upper body strength training", 60, Intensity.MODERATE.value),
    (Weekday.TUESDAY.value, "walk", 30, Intensity.MODERATE.value),
    (Weekday.WEDNESDAY.value, "lower body strength training", 60, Intensity.MODERATE.value),
    (Weekday.THURSDAY.value, "stretching", 15, Intensity.LOW.value),
    (Weekday.FRIDAY.value, "running", 45, Intensity.HIGH.value),
    (Weekday.SATURDAY.value, "soccer", 90, Intensity.HIGH.value),
    (Weekday.SUNDAY.value, "bike ride", 40, Intensity.LOW.value),
]


def seed():
    conn = connect()
    try:
        count = conn.execute("SELECT COUNT(*) FROM activity_calendar").fetchone()[0]
        if count == 0:
            conn.executemany(
                "INSERT INTO activity_calendar (day, activity, duration_minutes, intensity) "
                "VALUES (?, ?, ?, ?)",
                ACTIVITY_WEEK,
            )
            conn.commit()
            print(f"OK - {DB_PATH.name}: {len(ACTIVITY_WEEK)} days inserted into activity_calendar.")
        else:
            print("Skipped - activity_calendar is already populated.")
    finally:
        conn.close()


if __name__ == "__main__":
    seed()
