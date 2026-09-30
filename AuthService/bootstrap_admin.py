"""
Makes an existing account an admin. This is the *only* way to create the
first admin now — there's no admin code you can register with over the
network anymore, on purpose. Run this with actual access to the server
(SSH session, EC2 console, `docker compose exec`, etc.), not something
reachable over HTTP.

Usage (from inside AuthService/ locally, or via `docker compose exec auth
python bootstrap_admin.py <username>` when deployed):

    python bootstrap_admin.py <username>

Once you have one admin, use the app itself to promote/revoke others —
log in as an admin, go to the Users page, and use the promote/revoke button
next to any account.
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from app.config import settings  # noqa: E402


def resolve_db_path() -> Path:
    """Reads the actual configured DB path instead of guessing — local dev
    uses ./auth.db by default, Docker uses ./data/auth.db (see .env), and
    hardcoding either one would silently point at the wrong file in the
    other environment."""
    url = settings.DATABASE_URL
    if not url.startswith("sqlite:///"):
        print(f"This script only supports SQLite. DATABASE_URL is: {url}")
        sys.exit(1)
    return Path(__file__).parent / url.removeprefix("sqlite:///")


DB_PATH = resolve_db_path()


def main():
    if len(sys.argv) != 2:
        print("Usage: python bootstrap_admin.py <username>")
        sys.exit(1)

    username = sys.argv[1]

    if not DB_PATH.exists():
        print(f"No database found at {DB_PATH}. Register the account first "
              f"(run the server, sign up normally), then run this again.")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    row = cur.execute("SELECT id, is_admin FROM users WHERE username = ?", (username,)).fetchone()
    if row is None:
        print(f'No user named "{username}" found. Register that account first, then run this again.')
        conn.close()
        sys.exit(1)

    user_id, is_admin = row
    if is_admin:
        print(f'"{username}" is already an admin — nothing to do.')
        conn.close()
        return

    cur.execute("UPDATE users SET is_admin = 1 WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    print(f'Done — "{username}" is now an admin. Log in and check the Users page.')


if __name__ == "__main__":
    main()
