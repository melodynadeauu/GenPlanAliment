"""Read access to the weekly activity calendar stored in meal_prep.db."""
import sqlite3
from pathlib import Path

from core.types import Weekday

DB_PATH = Path(__file__).resolve().parent / "meal_prep.db"

_DAY_VALUES = ", ".join(f"'{day.value}'" for day in Weekday)

_SCHEMA = f"""
CREATE TABLE IF NOT EXISTS activity_calendar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    day TEXT NOT NULL CHECK (day IN ({_DAY_VALUES})),
    activity TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL CHECK (duration_minutes > 0),
    intensity INTEGER NOT NULL CHECK (intensity BETWEEN 1 AND 10)
);
"""


def connect():
    """Open a connection to meal_prep.db, ensuring activity_calendar exists."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(_SCHEMA)
    return conn


def get_activities(day: str):
    """Return the list of activity rows for `day` as dicts (empty if none)."""
    day = Weekday(day.strip().lower())

    conn = connect()
    try:
        rows = conn.execute(
            "SELECT * FROM activity_calendar WHERE day = ?", (day.value,)
        ).fetchall()
    finally:
        conn.close()

    return [dict(row) for row in rows]
