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
