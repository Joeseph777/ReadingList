"""
One-off migration for people upgrading an existing auth.db that predates the
admin-role feature. SQLAlchemy's create_all() only creates tables that don't
exist yet — it never alters existing tables — so an old database is missing
the new `is_admin` column and every login/profile/friends call 500s with
"no such column: users.is_admin".

Safe to run more than once. Run it from inside AuthService/, with the server
stopped:

    python migrate_add_admin.py

What it does:
  1. Adds the `is_admin` column to `users` if it isn't already there.
  2. If nobody is currently marked admin, promotes whichever account has the
     lowest id (i.e. your original/oldest account) to admin, so you always
     have someone who can manage users afterward.
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent / "auth.db"


def main():
    if not DB_PATH.exists():
        print(f"No database found at {DB_PATH} — nothing to migrate. "
              f"(A fresh auth.db will be created correctly when you next run the server.)")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    columns = [row[1] for row in cur.execute("PRAGMA table_info(users)")]

    if "is_admin" not in columns:
        print("Adding is_admin column to users table...")
        cur.execute("ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0")
        conn.commit()
        print("Done.")
    else:
        print("is_admin column already exists — no schema change needed.")

    cur.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1")
    admin_count = cur.fetchone()[0]

    if admin_count == 0:
        row = cur.execute("SELECT id, username FROM users ORDER BY id LIMIT 1").fetchone()
        if row is None:
            print("No users in the database yet — nothing to promote. "
                  "The first person to register from now on will become admin automatically.")
        else:
            user_id, username = row
            cur.execute("UPDATE users SET is_admin = 1 WHERE id = ?", (user_id,))
            conn.commit()
            print(f'Promoted "{username}" (id {user_id}) to admin, since no one was marked admin yet.')
    else:
        print(f"{admin_count} admin account(s) already exist — leaving as is.")

    conn.close()
    print("Migration complete. You can start the server normally now.")


if __name__ == "__main__":
    main()
