"""Seed sample users into the database for local development.

Run: python scripts/seed_users.py

This script uses `app.database.get_db()` to obtain a connection.
It will insert sample users if they do not already exist (by email).
"""

import sys
import pathlib
import uuid
import traceback

# Ensure project root is on sys.path so `app` package can be imported when
# running this script directly (e.g. `python scripts/seed_users.py`).
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.database import get_db
from mysql.connector import Error

SAMPLES = [
    {"user_id": "u_test_1", "first_name": "Test", "email": "test1@example.com"},
    {"user_id": "u_test_2", "first_name": "Eman", "email": "eman@example.com"},
    {"user_id": "u_john", "first_name": "John", "email": "john@example.com"},
]


def upsert_sample_users():
    conn = None
    try:
        conn = get_db()
        cur = conn.cursor()
        for u in SAMPLES:
            # check by email first
            cur.execute("SELECT user_id FROM users WHERE LOWER(TRIM(email)) = %s LIMIT 1", (u["email"].lower().strip(),))
            r = cur.fetchone()
            if r:
                print(f"User with email {u['email']} already exists (id={r[0]})")
                continue

            # try insert; if user_id conflicts, fall back to inserting without explicit id
            try:
                cur.execute("INSERT INTO users (user_id, first_name, email, is_active) VALUES (%s, %s, %s, %s)",
                            (u["user_id"], u["first_name"], u["email"], 1))
                print(f"Inserted user {u['first_name']} as {u['user_id']}")
            except Error as e:
                # If inserting with explicit user_id failed, try generating a unique id and insert explicitly.
                inserted = False
                for _ in range(5):
                    gen_id = f"{u['user_id']}_{uuid.uuid4().hex[:4]}"
                    try:
                        cur.execute(
                            "INSERT INTO users (user_id, first_name, email, is_active) VALUES (%s, %s, %s, %s)",
                            (gen_id, u["first_name"], u["email"], 1),
                        )
                        print(f"Inserted user {u['first_name']} as {gen_id}")
                        inserted = True
                        break
                    except Error:
                        continue
                if not inserted:
                    print(f"Failed to insert {u['email']}: {e}")
                    traceback.print_exc()
        conn.commit()
    except Exception as e:
        print(f"Database error: {e}")
        traceback.print_exc()
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            if conn:
                conn.close()
        except Exception:
            pass


if __name__ == '__main__':
    upsert_sample_users()
