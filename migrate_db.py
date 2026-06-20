"""
One-off migration script for EventHub.

Run this ONCE if you have an existing event_management.db created before
the category / price_rupees / payment_status / payment_ref columns existed.
It safely adds any missing columns without touching your existing data.

Usage:
    python migrate_db.py

Safe to run multiple times — it only adds a column if it's not already
there.
"""

import sqlite3

DB_PATH = "event_management.db"


def column_exists(conn, table, column):
    cols = {row[1] for row in conn.execute(
        f"PRAGMA table_info({table})").fetchall()}
    return column in cols


def main():
    conn = sqlite3.connect(DB_PATH)
    try:
        added = []

        if not column_exists(conn, "events", "category"):
            conn.execute(
                "ALTER TABLE events ADD COLUMN category TEXT NOT NULL DEFAULT 'Workshops'"
            )
            added.append("events.category")

        if not column_exists(conn, "events", "price_rupees"):
            conn.execute(
                "ALTER TABLE events ADD COLUMN price_rupees REAL NOT NULL DEFAULT 0"
            )
            added.append("events.price_rupees")

        if not column_exists(conn, "registrations", "payment_status"):
            conn.execute(
                "ALTER TABLE registrations ADD COLUMN payment_status "
                "TEXT NOT NULL DEFAULT 'not_required'"
            )
            added.append("registrations.payment_status")

        if not column_exists(conn, "registrations", "payment_ref"):
            conn.execute(
                "ALTER TABLE registrations ADD COLUMN payment_ref TEXT")
            added.append("registrations.payment_ref")

        # reviews table might not exist at all on very old DBs
        conn.execute(
            """CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                event_id INTEGER NOT NULL,
                rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, event_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
            )"""
        )

        conn.commit()

        if added:
            print("Migration complete. Added columns:")
            for a in added:
                print(f"  - {a}")
        else:
            print("Nothing to migrate — your database already has all required columns.")
        print("Made sure the 'reviews' table exists too.")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
