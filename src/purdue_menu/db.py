"""SQLite database for preference tracking and meal logging."""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional

DB_PATH = Path(__file__).parent.parent.parent / "data" / "preferences.db"


def get_connection() -> sqlite3.Connection:
    """Get a database connection, creating tables if needed."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _ensure_tables(conn)
    return conn


def _ensure_tables(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY,
            item_name TEXT NOT NULL,
            rating INTEGER CHECK(rating BETWEEN 1 AND 5),
            location TEXT,
            meal_type TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS meal_logs (
            id INTEGER PRIMARY KEY,
            item_name TEXT,
            location TEXT,
            meal_type TEXT,
            mood TEXT,
            hunger_level INTEGER,
            notes TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS preferences (
            id INTEGER PRIMARY KEY,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(key, value)
        );
    """)
    conn.commit()


# --- Ratings ---

def add_rating(item_name: str, rating: int, location: Optional[str] = None, meal_type: Optional[str] = None) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO ratings (item_name, rating, location, meal_type) VALUES (?, ?, ?, ?)",
        (item_name, rating, location, meal_type),
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return row_id


def get_ratings(limit: int = 50) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT item_name, rating, location, meal_type, timestamp FROM ratings ORDER BY timestamp DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_item_avg_rating(item_name: str) -> Optional[float]:
    conn = get_connection()
    row = conn.execute(
        "SELECT AVG(rating) as avg_rating FROM ratings WHERE LOWER(item_name) = LOWER(?)",
        (item_name,),
    ).fetchone()
    conn.close()
    return row["avg_rating"] if row and row["avg_rating"] else None


def get_all_rated_items() -> dict[str, float]:
    """Return {item_name_lower: avg_rating} for all rated items."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT LOWER(item_name) as name, AVG(rating) as avg FROM ratings GROUP BY LOWER(item_name)"
    ).fetchall()
    conn.close()
    return {r["name"]: r["avg"] for r in rows}


# --- Meal Logs ---

def log_meal(
    item_name: str,
    location: Optional[str] = None,
    meal_type: Optional[str] = None,
    mood: Optional[str] = None,
    hunger_level: Optional[int] = None,
    notes: Optional[str] = None,
) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO meal_logs (item_name, location, meal_type, mood, hunger_level, notes) VALUES (?, ?, ?, ?, ?, ?)",
        (item_name, location, meal_type, mood, hunger_level, notes),
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return row_id


def get_meal_history(limit: int = 20) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM meal_logs ORDER BY timestamp DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_location_frequency() -> dict[str, int]:
    """How often each location appears in meal logs."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT location, COUNT(*) as count FROM meal_logs WHERE location IS NOT NULL GROUP BY location ORDER BY count DESC"
    ).fetchall()
    conn.close()
    return {r["location"]: r["count"] for r in rows}


def get_mood_items(mood: str) -> list[str]:
    """Items eaten when in a specific mood."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT item_name FROM meal_logs WHERE LOWER(mood) = LOWER(?) AND item_name IS NOT NULL",
        (mood,),
    ).fetchall()
    conn.close()
    return [r["item_name"] for r in rows]


# --- Preferences ---

def set_preference(key: str, value: str):
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO preferences (key, value, timestamp) VALUES (?, ?, ?)",
        (key, value, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def remove_preference(key: str, value: Optional[str] = None):
    conn = get_connection()
    if value:
        conn.execute("DELETE FROM preferences WHERE key = ? AND value = ?", (key, value))
    else:
        conn.execute("DELETE FROM preferences WHERE key = ?", (key,))
    conn.commit()
    conn.close()


def get_preferences() -> dict[str, list[str]]:
    """Return all preferences grouped by key."""
    conn = get_connection()
    rows = conn.execute("SELECT key, value FROM preferences ORDER BY key").fetchall()
    conn.close()
    result: dict[str, list[str]] = {}
    for r in rows:
        result.setdefault(r["key"], []).append(r["value"])
    return result


def get_preference_values(key: str) -> list[str]:
    conn = get_connection()
    rows = conn.execute("SELECT value FROM preferences WHERE key = ?", (key,)).fetchall()
    conn.close()
    return [r["value"] for r in rows]
