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
