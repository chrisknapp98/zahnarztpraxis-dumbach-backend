# Zahnarztpraxis Dumbach backend

Django 5.2 LTS with PostgreSQL. Python and dependencies run inside Docker; no local Python installation is required.

## Local development

```sh
docker compose build
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py createsuperuser
docker compose up
```

Open http://localhost:8000/admin/ and sign in with the superuser account.
Source files are mounted into the container and Django reloads after edits.
Compose starts PostgreSQL automatically. Database contents persist in a named volume.

## Common commands

```sh
docker compose run --rm web python manage.py check
docker compose run --rm web python manage.py makemigrations
docker compose run --rm web python manage.py migrate
docker compose down
```

To add a dependency, edit requirements.txt and run `docker compose build`.
Optional local overrides can be placed in `.env` using `.env.example` as a starting point.

## Deployment

This Compose file is for local development. Production needs a production application server, DEBUG disabled, explicit allowed hosts, private secrets, static file serving, HTTPS, and database backups.

## Practice information

The `practice` app groups editable practice information, starting with announcements.
It contains the singular `Announcement` model, stored in
Django's default `practice_announcement` table. Fields are UUID `id`,
`message`, `created_at`, and nonnegative `position`. Lower positions appear first;
within a position, newer announcements appear first. Creation dates and UUIDs can
be preserved when importing existing frontend data. The future API can expose
`created_at` as the existing frontend `date` field.

Manage announcements at `/admin/practice/announcement/`. Positions can be
edited directly in the admin list. Messages are stored as text, including line
breaks and links. The existing frontend API has not yet been connected.

```sh
docker compose run --rm web python manage.py test practice
```

## Announcement API

`/api/announcements` (also accepts a trailing slash):

| Method | Input | Result |
| --- | --- | --- |
| GET | None | Public ordered list |
| POST | JSON `{"message":"News"}` | Create at front; 201 and updated list |
| DELETE | Query `?id=<uuid>` | Delete; updated list |
| PUT | JSON `{"orderedIds":["<uuid>"]}` | Reorder; omitted items follow in their existing order |

List items retain the frontend contract: `id`, `message`, `date` (ISO 8601).
Writes require an active practice-editor Django session and the corresponding add/delete/change
announcement permission. Superusers have these permissions automatically.
Sign in at `/admin/` for now; dedicated JSON login/logout endpoints and frontend
integration are not implemented yet. Existing Next.js authentication is separate.

GET sets a `csrftoken` cookie. For writes, send that token in the `X-CSRFToken`
header along with the session cookie. POST and PUT require `application/json`.
CSRF failures use Django's standard 403 response; other API errors return JSON.
Invalid or duplicate reorder IDs return 400 without changing the order.

## Frontend sessions

The Next.js frontend proxies `/api/announcements` and `/api/auth*` to Django.
GET `/api/auth/validate` returns `valid` and a masked `csrfToken`, also for anonymous
requests (401). POST `/api/auth` accepts JSON `username` and `password`, establishes
a practice-editor session, and returns a rotated CSRF token. POST `/api/auth/logout` invalidates
the session. Login, logout, and all announcement writes require CSRF protection.
For production, set `CSRF_TRUSTED_ORIGINS` to the public HTTPS frontend origin
(comma-separated if multiple), disable DEBUG, and configure ALLOWED_HOSTS.

## Editor accounts and Django admin

The `Practice editors` group grants frontend access and view/add/change/delete
announcement permissions. Assign daily users to this group and leave Staff status
and Superuser status unchecked. Staff status controls Django admin access only;
it does not grant frontend access. Active superusers may use both interfaces.
Model permissions are checked for each write, and removing group membership
immediately blocks subsequent frontend session checks and writes.

Create and manage these accounts through Django admin as the technical maintainer.
The migration creates the group automatically; it does not enroll users.

## Password changes

POST `/api/auth/password` accepts `old_password`, `new_password1`, and
`new_password2` as JSON, with a session and CSRF token. Practice editors can only
change their own password. Django's PasswordChangeForm validates the current
password, confirmation, and configured strength rules. Success preserves the
current session; other sessions are rejected on their next authenticated request.

## Local VS Code tests

The local `.venv` can discover and run Django tests using the workspace Python
settings and `MANAGE_PY_PATH=./manage.py` in `.env`. Keep
`python.testing.unittestArgs` empty; do not use unittest's `-s`/`-p` options with
Django's runner. Reload the VS Code window after changing these settings.

PostgreSQL is exposed only on `127.0.0.1:55432` for local Python. Configure
`POSTGRES_DB=dumbach`, `POSTGRES_USER=dumbach`, `POSTGRES_HOST=127.0.0.1`, and
`POSTGRES_PORT=55432` in `.env`. The password is shared with Docker; the web
container explicitly uses `db:5432` instead. Start the database before running
tests (`docker compose up -d db`). Django creates a separate `test_dumbach`
database for tests; the development database is preserved.

## Announcement authors

Every announcement has a required author referencing AUTH_USER_MODEL. The API and
Django admin assign the creator automatically; client-supplied authors are ignored.
The author is read-only in admin. Users referenced by announcements cannot be deleted
(PROTECT); deactivate their accounts instead. Public API responses do not expose authors.
The author migration attributes existing announcements to the maintainer-selected
`admin` account, and fresh databases with no announcements need no backfill account.
