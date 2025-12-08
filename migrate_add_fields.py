"""Lightweight migration helper for local SQLite database.
Adds missing columns to the member table if they are absent.
Safe to run multiple times; uses PRAGMA table_info to detect columns.
"""
import os
import sqlite3
from contextlib import closing

# SQLite database path (local dev fallback)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "gym.db")

# Columns to ensure on member table
COLUMNS = {
    "monthly_price": "REAL",
    "cnic": "TEXT",
    "address": "TEXT",
    "gender": "TEXT",
    "date_of_birth": "DATE",
    "notes": "TEXT",
}


def column_exists(cur: sqlite3.Cursor, table: str, column: str) -> bool:
    cur.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())


def ensure_columns():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}. Nothing to migrate.")
        return

    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.cursor()
        cur.execute("PRAGMA foreign_keys=OFF;")
        for col_name, col_type in COLUMNS.items():
            if column_exists(cur, "member", col_name):
                print(f"Column already exists: {col_name}")
                continue
            try:
                cur.execute(f"ALTER TABLE member ADD COLUMN {col_name} {col_type}")
                print(f"Added column: {col_name} ({col_type})")
            except sqlite3.OperationalError as exc:
                print(f"Could not add {col_name}: {exc}")
        conn.commit()
    print("Migration complete. You may restart the Flask app.")


if __name__ == "__main__":
    ensure_columns()
