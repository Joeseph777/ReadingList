# Reading List — Web App

A web frontend for your reading list, backed by the AuthService + LibraryService
API. Replaces the Tkinter desktop app with a browser UI, adds friends and an
admin role, and lets you import your old JSON reading list.

**Want to put this on the internet (e.g. AWS)?** See `DEPLOYMENT.md` for a
full walkthrough — Docker Compose, nginx, HTTPS, the works.

## Security basics added

- **Password strength** — registration requires 8–64 characters, at least
  one digit, one uppercase letter, one lowercase letter, and one special
  character ($ @ # % _ - / \ ! & * + = ? . , ; :). Enforced server-side
  (`AuthService/app/schemas.py`); the register form also shows a live
  checklist as you type, but that's just a convenience — the server is the
  real gate.
- **Rate limiting** — `/auth/login` and `/auth/register` are capped at
  10 requests/minute per IP, to slow down scripted password-guessing.
  Returns `429 Too Many Requests` once tripped.
- **Comment length cap** — 50,000 characters per book's notes. That's
  several times more than any realistic amount of note-taking (even years
  of it), so it shouldn't affect normal use — it's there purely so the
  field can't be used to dump an arbitrarily large payload into the
  database.
- **CORS is now configurable** — `ALLOWED_ORIGINS` in each service's `.env`
  instead of a hardcoded `*`. The Docker Compose setup routes everything
  through nginx on one origin, so you likely won't need to touch this even
  in production — see `DEPLOYMENT.md`.

Not done yet, and worth doing before this handles real strangers' data:
email verification, disposable-email blocking, and a proper password-reset
flow (right now, a forgotten password means an admin has to delete and
recreate that account). None of these block you from running this for
yourself or a small trusted group today.

## What changed in the backend

- **AuthService**
  - Registration is open — no access code required to create a normal
    account.
  - **Admin role**: registering with the correct admin code makes that
    account an admin. Set the code in `AuthService/.env`
    (`ADMIN_ACCESS_CODE`, currently `change-me-admin-code` — change it).
    Leave the "Admin code" field blank on the registration form for a
    normal account; fill it in with the matching code to register as
    admin. Wrong code → registration is rejected outright (403), it does
    not silently fall back to a normal account.
    - `GET /auth/users` — admin-only. Full user list for management.
    - `DELETE /auth/users/{id}` — admin-only. Deletes the account, their
      friendships, and cascades to LibraryService to delete their books too.
      Admins can't delete their own account through this endpoint.
    - `GET /auth/search?q=` — any logged-in user. Search/browse other users
      by username (substring match, capped at 50 results, excludes
      yourself). This is what normal users use to find people to friend —
      they don't get the full `/auth/users` list.
  - **Friends system**, all under `/auth/friends`:
    - `POST /auth/friends/request/{username}` — send a request
    - `POST /auth/friends/{friendship_id}/respond` — `{"action": "accept"}` or `{"action": "decline"}`
    - `DELETE /auth/friends/{friendship_id}` — unfriend or cancel a pending request
    - `GET /auth/friends` — returns your `friends`, `incoming_requests`, and `outgoing_requests`
    - `GET /auth/internal/are-friends?user_a=&user_b=` — unauthenticated, used
      by LibraryService to check friendship before sharing a reading list.
      Only meant to be reachable on your local/trusted network.
  - Fixed a bug where `get_current_user` looked up users by treating the JWT
    as a username, when it's actually the user's numeric id — this silently
    broke `/auth/profile` before.
  - Added CORS so a browser page (running on a different port) can call it.
  - Pinned `bcrypt==4.0.1` in requirements.txt — newer bcrypt releases break
    passlib 1.7.4's hashing and cause registration to fail with a 500.
  - Removed verbose token/payload logging — the server used to print each
    decoded JWT payload to its own console on every request. Harmless (it
    never left your machine) but unnecessary, so it's gone.
  - **Self-healing schema**: both services now compare their database's
    actual columns to the code's models on every startup and automatically
    add anything missing. This means dropping a new version of the app into
    a folder with an old database file just works — no more
    `no such column: ...` errors after an update. Only ever adds columns,
    never touches existing data.
  - New `LIBRARY_SERVICE_URL` setting (`AuthService/.env`) — where it looks
    for LibraryService when cascading a user deletion. Defaults to
    `http://localhost:8001`.

- **LibraryService**
  - Added the missing `PATCH /books/{id}/rating` and
    `PATCH /books/{id}/comments` endpoints (the schemas existed, the routes
    didn't).
  - New `GET /books/friend/{friend_id}` — returns that user's books (with
    ratings and comments), but only if AuthService confirms you're friends.
    Read-only; there's no way to edit a friend's books through the API.
  - New `DELETE /books/internal/by-user/{user_id}` — unauthenticated,
    trusted-network-only. Called by AuthService when an admin deletes a
    user, to clean up that user's books.
  - Added CORS, same reason as above.
  - Removed verbose token/payload logging, same as AuthService.
  - (From before) `reading_level` is computed from `pages_read`/`pages`
    instead of expected as a stored column.
  - `AUTH_SERVICE_URL` setting (`LibraryService/.env`) — where it looks for
    AuthService when verifying friendships. Defaults to `http://localhost:8000`.

## Running it

Open three terminals.

**1. AuthService**
```
cd AuthService
pip install -r requirements.txt
python run.py
```
Runs on `http://localhost:8000`.

**2. LibraryService**
```
cd LibraryService
pip install -r requirements.txt
python run.py
```
Runs on `http://localhost:8001`.

**3. WebApp** (any static file server works)
```
cd WebApp
python -m http.server 5500
```
Then open `http://localhost:5500` in your browser.

If you deploy the services somewhere other than `localhost:8000` /
`localhost:8001`, edit `WebApp/config.js`, and update `AUTH_SERVICE_URL` /
`LIBRARY_SERVICE_URL` in each service's `.env` to match.

**The first account you register does NOT automatically become admin
anymore.** Set `ADMIN_ACCESS_CODE` in `AuthService/.env` before you start
registering people, then use that code in the "Admin code" field when you
register your own account, so you end up with at least one admin.

**Already have an `auth.db` from before a schema change (like the admin-role
update)?** As of this version, you don't need to do anything — both
AuthService and LibraryService now check their database's actual columns
against the code's models every time they start, and automatically add any
that are missing (`>>> Migrated: added column ...` in the startup log if it
happens). This only ever adds columns; it never touches existing data. The
old failure mode (`no such column: users.is_admin` on login/register/etc.)
should no longer be possible — extracting a new zip into the same folder as
an old database and just restarting the server is enough.

If you're on an even older copy that predates this self-healing behavior,
either delete `auth.db` / `library.db` and let them be recreated fresh, or
run the one-off script below once with the server stopped:
```
cd AuthService
python migrate_add_admin.py
```

## Using it

1. Register with a username, email, and password. Leave "Admin code" blank
   for a normal account, or fill it in (matching `ADMIN_ACCESS_CODE` in
   `AuthService/.env`) to register as admin.
2. Log in.
3. Add books, track progress, rate, and leave notes from the **My Books**
   page. Filter by status, search, sort, and switch color themes from the
   sidebar (the same 11 palettes from `ColorPalette.py`). Double-click a
   book to open its notes in a popup — the inline card just shows the
   title, author, progress, and rating.
4. **Import JSON / Export JSON / Export PDF**, next to "+ Add book":
   - **Import JSON** — pick a `reading_list.json` file exported by the old
     desktop app (`ReadingList.py`) or by this web app's own Export JSON.
     Matches books by title + author: existing ones get updated (pages,
     progress, rating, notes), new ones get created. Safe to re-import the
     same file more than once — it won't duplicate anything.
   - **Export JSON** — downloads your list in the exact same format the
     desktop app reads, so you can move a reading list from the web app
     back into `ReadingListGUI.py`, or just keep a backup.
   - **Export PDF** — a readable report: a table of every book (title,
     author, year, pages, progress, rating) plus a Notes section listing
     full comments for any book that has them.
5. **Friends** — search for people under "Find people," send a request,
   and once they accept you can click "View shelf" to see their books,
   progress, ratings, and notes (read-only — same double-click-for-notes
   popup, no edit controls).
6. **Users** — admin only. Full list with a delete button per account
   (deleting removes the account, their friendships, and their books).
   Normal users don't see this page; they use "Find people" in Friends
   instead, which only returns search results, not a full roster.

Login sessions persist in the browser (localStorage), so refreshing the page
won't log you out.

## Notes

- This is a from-scratch static frontend (HTML/CSS/vanilla JS) — no build
  step, no framework. It talks directly to the two FastAPI services over
  `fetch`.
- Cover-art fetching and PDF export from the old Tkinter app aren't ported
  over yet. Let me know if you want either added.
- No email verification or password strength checks yet — noted as a
  future improvement, not blocking anything today.
