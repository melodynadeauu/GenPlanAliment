"""SQLite-backed cache for USDA FoodData Central API responses (search + nutrition).

Permanent cache: once a query or fdc_id is cached, it stays cached. Each set_ call
commits immediately (write-through, same guarantee the old JSON cache made) -- but as a
point write on one row, not a read-modify-write of the whole cache. The old
data/usda/usda_cache.json read and rewrote its entire content on every single get/set,
which scaled with total cache size (3.4MB for 48 entries, growing forever); see
data/usda/migrate_json_cache_to_sqlite.py for the one-time migration of that file's data
into this store.

Nutrition rows store only the four macros data.usda.nutrients.extract_macros knows about,
not USDA's full foodNutrients panel (50-100+ entries per food, most never used) -- see
data.usda.client.get_nutrition for how a row cached before a macro field existed here
gets silently backfilled with one live call instead of requiring a manual cache wipe.
"""
import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "usda_cache.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS search_cache (
    query TEXT PRIMARY KEY,
    results_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS nutrition_cache (
    fdc_id TEXT PRIMARY KEY,
    found INTEGER NOT NULL,
    food_json TEXT
);
"""


def connect() -> sqlite3.Connection:
    """Open a connection to usda_cache.db, ensuring both tables exist."""
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(_SCHEMA)
    return conn


def get_cached_search(query: str) -> list | None:
    """Return cached search results for `query` (normalized), or None if never cached.
    Distinguishes "never cached" (None) from "cached, found nothing" ([]) -- the latter
    still counts as a hit, so a confirmed-empty query never re-hits the network."""
    key = query.strip().lower()
    conn = connect()
    try:
        row = conn.execute("SELECT results_json FROM search_cache WHERE query = ?", (key,)).fetchone()
    finally:
        conn.close()
    return None if row is None else json.loads(row[0])


def set_cached_search(query: str, results: list) -> None:
    """Cache `results` for `query` (normalized) and commit immediately."""
    key = query.strip().lower()
    conn = connect()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO search_cache (query, results_json) VALUES (?, ?)",
            (key, json.dumps(results, ensure_ascii=False)),
        )
        conn.commit()
    finally:
        conn.close()


def get_cached_nutrition(fdc_id: str) -> dict | None:
    """Return the cached outcome for `fdc_id`, or None if never cached:
    - {"found": False} -- a confirmed not_found was cached (no live call on a hit)
    - {"found": True, "food": {...}} -- the trimmed food dict as data.usda.client cached it
    """
    conn = connect()
    try:
        row = conn.execute(
            "SELECT found, food_json FROM nutrition_cache WHERE fdc_id = ?", (str(fdc_id),)
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    found, food_json = row
    return {"found": True, "food": json.loads(food_json)} if found else {"found": False}


def set_cached_nutrition_found(fdc_id: str, food: dict) -> None:
    """Cache `food` (already trimmed to fdc_id/description/macros_per_100g) for `fdc_id`
    and commit immediately. Overwrites any previous row for the same fdc_id -- including
    a stale not_found or a row missing a macro field added since it was cached."""
    conn = connect()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO nutrition_cache (fdc_id, found, food_json) VALUES (?, 1, ?)",
            (str(fdc_id), json.dumps(food, ensure_ascii=False)),
        )
        conn.commit()
    finally:
        conn.close()


def set_cached_nutrition_not_found(fdc_id: str) -> None:
    """Cache a confirmed not_found for `fdc_id` and commit immediately."""
    conn = connect()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO nutrition_cache (fdc_id, found, food_json) VALUES (?, 0, NULL)",
            (str(fdc_id),),
        )
        conn.commit()
    finally:
        conn.close()
