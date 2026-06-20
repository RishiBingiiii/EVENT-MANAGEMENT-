"""
Data access layer for the Event Management System.

Everything is stored in a local SQLite file (event_management.db), which is
created automatically the first time the app runs. No external database
server is needed.
"""

import sqlite3
from contextlib import contextmanager

from auth import hash_password, verify_password

DB_PATH = "event_management.db"


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


CATEGORIES = ["Workshops", "Tech Events", "Sports", "Cultural"]


def init_db():
    """Create tables if they don't exist yet, and seed a default admin."""
    with get_connection() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                email TEXT,
                role TEXT NOT NULL DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                event_date TEXT NOT NULL,
                event_time TEXT,
                location TEXT,
                capacity INTEGER DEFAULT 0,
                category TEXT NOT NULL DEFAULT 'Workshops',
                price_rupees REAL NOT NULL DEFAULT 0,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES users(id)
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                event_id INTEGER NOT NULL,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                payment_status TEXT NOT NULL DEFAULT 'not_required',
                payment_ref TEXT,
                UNIQUE(user_id, event_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
            )"""
        )
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

        # Lightweight migration for DBs created before these columns existed
        existing_cols = {
            row["name"] for row in conn.execute("PRAGMA table_info(events)").fetchall()
        }
        if "category" not in existing_cols:
            conn.execute(
                "ALTER TABLE events ADD COLUMN category TEXT NOT NULL DEFAULT 'Workshops'"
            )
        if "price_rupees" not in existing_cols:
            conn.execute(
                "ALTER TABLE events ADD COLUMN price_rupees REAL NOT NULL DEFAULT 0"
            )
        reg_cols = {
            row["name"] for row in conn.execute("PRAGMA table_info(registrations)").fetchall()
        }
        if "payment_status" not in reg_cols:
            conn.execute(
                "ALTER TABLE registrations ADD COLUMN payment_status TEXT NOT NULL DEFAULT 'not_required'"
            )
        if "payment_ref" not in reg_cols:
            conn.execute(
                "ALTER TABLE registrations ADD COLUMN payment_ref TEXT")

        existing_admin = conn.execute(
            "SELECT id FROM users WHERE role = 'admin' LIMIT 1"
        ).fetchone()
        if not existing_admin:
            conn.execute(
                "INSERT INTO users (username, password_hash, full_name, role) "
                "VALUES (?, ?, ?, ?)",
                ("admin", hash_password("admin123"), "Administrator", "admin"),
            )


# ---------------------------------------------------------------- Users ----

def create_user(username, password, full_name, email, role="user"):
    """Create a new account. Returns (success, message)."""
    if not username or not password:
        return False, "Username and password are required."
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO users (username, password_hash, full_name, email, role) "
                "VALUES (?, ?, ?, ?, ?)",
                (username, hash_password(password), full_name, email, role),
            )
        return True, "Account created successfully."
    except sqlite3.IntegrityError:
        return False, "That username is already taken."


def authenticate_user(username, password):
    """Return the user row (as a dict) if credentials are correct, else None."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
    if row and verify_password(password, row["password_hash"]):
        return dict(row)
    return None


# --------------------------------------------------------------- Events ----

def create_event(
    title, description, event_date, event_time, location, capacity, created_by,
    category="Workshops", price_rupees=0,
):
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO events
               (title, description, event_date, event_time, location, capacity,
                category, price_rupees, created_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (title, description, event_date, event_time, location, capacity,
             category, price_rupees, created_by),
        )


def update_event(
    event_id, title, description, event_date, event_time, location, capacity,
    category="Workshops", price_rupees=0,
):
    with get_connection() as conn:
        conn.execute(
            """UPDATE events
               SET title = ?, description = ?, event_date = ?, event_time = ?,
                   location = ?, capacity = ?, category = ?, price_rupees = ?
               WHERE id = ?""",
            (title, description, event_date, event_time, location, capacity,
             category, price_rupees, event_id),
        )


def delete_event(event_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM events WHERE id = ?", (event_id,))


def get_all_events(category=None):
    with get_connection() as conn:
        if category and category != "All":
            rows = conn.execute(
                "SELECT * FROM events WHERE category = ? ORDER BY event_date, event_time",
                (category,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM events ORDER BY event_date, event_time"
            ).fetchall()
    return [dict(r) for r in rows]


def get_upcoming_events(category=None):
    """Events whose date is today or later, optionally filtered by category."""
    from datetime import date as _date
    today = str(_date.today())
    with get_connection() as conn:
        if category and category != "All":
            rows = conn.execute(
                """SELECT * FROM events WHERE event_date >= ? AND category = ?
                   ORDER BY event_date, event_time""",
                (today, category),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM events WHERE event_date >= ? ORDER BY event_date, event_time",
                (today,),
            ).fetchall()
    return [dict(r) for r in rows]


def get_event(event_id):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    return dict(row) if row else None


def get_registration_count(event_id):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM registrations WHERE event_id = ?", (event_id,)
        ).fetchone()
    return row["c"]


# ------------------------------------------------------------ Registrations

def register_for_event(user_id, event_id, payment_status="not_required", payment_ref=None):
    """Register a user for an event. Returns (success, message).

    payment_status: 'not_required' for free events, or 'paid' once a (stub)
    payment has gone through for a priced event.
    """
    event = get_event(event_id)
    if event is None:
        return False, "Event not found."
    if get_user_registration(user_id, event_id):
        return False, "You're already registered for this event."
    if event["capacity"] and get_registration_count(event_id) >= event["capacity"]:
        return False, "This event is full."
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO registrations (user_id, event_id, payment_status, payment_ref) "
            "VALUES (?, ?, ?, ?)",
            (user_id, event_id, payment_status, payment_ref),
        )
    return True, "You're registered!"


def cancel_registration(user_id, event_id):
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM registrations WHERE user_id = ? AND event_id = ?",
            (user_id, event_id),
        )


def get_user_registration(user_id, event_id):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM registrations WHERE user_id = ? AND event_id = ?",
            (user_id, event_id),
        ).fetchone()
    return dict(row) if row else None


def get_user_registrations(user_id):
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT r.id AS registration_id, r.registered_at,
                      r.payment_status, r.payment_ref, e.*
               FROM registrations r
               JOIN events e ON r.event_id = e.id
               WHERE r.user_id = ?
               ORDER BY e.event_date, e.event_time""",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_event_registrations(event_id):
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT u.username, u.full_name, u.email, r.registered_at,
                      r.payment_status, r.payment_ref
               FROM registrations r
               JOIN users u ON r.user_id = u.id
               WHERE r.event_id = ?
               ORDER BY r.registered_at""",
            (event_id,),
        ).fetchall()
    return [dict(r) for r in rows]


# ----------------------------------------------------------------- Reviews -

def has_attended(user_id, event_id):
    """A user can only review events whose date has already passed and that
    they were registered for."""
    from datetime import date as _date
    reg = get_user_registration(user_id, event_id)
    if not reg:
        return False
    event = get_event(event_id)
    if not event:
        return False
    return event["event_date"] <= str(_date.today())


def add_or_update_review(user_id, event_id, rating, comment):
    """Create or update (upsert) a user's review for an event."""
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO reviews (user_id, event_id, rating, comment)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(user_id, event_id)
               DO UPDATE SET rating = excluded.rating, comment = excluded.comment,
                              created_at = CURRENT_TIMESTAMP""",
            (user_id, event_id, rating, comment),
        )


def get_user_review(user_id, event_id):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM reviews WHERE user_id = ? AND event_id = ?",
            (user_id, event_id),
        ).fetchone()
    return dict(row) if row else None


def get_event_reviews(event_id):
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT rv.*, u.username, u.full_name
               FROM reviews rv JOIN users u ON rv.user_id = u.id
               WHERE rv.event_id = ?
               ORDER BY rv.created_at DESC""",
            (event_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_event_rating_summary(event_id):
    """Returns (average_rating_or_None, review_count)."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT AVG(rating) AS avg_r, COUNT(*) AS c FROM reviews WHERE event_id = ?",
            (event_id,),
        ).fetchone()
    avg_r = round(row["avg_r"], 1) if row["avg_r"] is not None else None
    return avg_r, row["c"]


def get_all_rating_summaries():
    """Returns {event_id: (avg_rating, count)} for every event that has reviews."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT event_id, AVG(rating) AS avg_r, COUNT(*) AS c "
            "FROM reviews GROUP BY event_id"
        ).fetchall()
    return {r["event_id"]: (round(r["avg_r"], 1), r["c"]) for r in rows}


# ----------------------------------------------------------- Recommendations

def get_recommended_events(user_id, limit=4):
    """Rule-based 'You may like' recommendations.

    Looks at the categories of events the user has already registered for,
    then suggests other *upcoming* events in those same categories that the
    user hasn't already registered for — ranked by soonest first.

    If the user has no registration history yet, falls back to the soonest
    upcoming events overall (so the section never looks empty/broken).
    """
    from datetime import date as _date
    today = str(_date.today())
    with get_connection() as conn:
        past_categories = [
            r["category"]
            for r in conn.execute(
                """SELECT DISTINCT e.category
                   FROM registrations r JOIN events e ON r.event_id = e.id
                   WHERE r.user_id = ?""",
                (user_id,),
            ).fetchall()
        ]

        if past_categories:
            placeholders = ",".join("?" for _ in past_categories)
            rows = conn.execute(
                f"""SELECT * FROM events
                    WHERE category IN ({placeholders})
                      AND event_date >= ?
                      AND id NOT IN (
                          SELECT event_id FROM registrations WHERE user_id = ?
                      )
                    ORDER BY event_date, event_time
                    LIMIT ?""",
                (*past_categories, today, user_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT * FROM events
                   WHERE event_date >= ?
                     AND id NOT IN (
                         SELECT event_id FROM registrations WHERE user_id = ?
                     )
                   ORDER BY event_date, event_time
                   LIMIT ?""",
                (today, user_id, limit),
            ).fetchall()
    return [dict(r) for r in rows]
