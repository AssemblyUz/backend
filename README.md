# Assembly backend

Django + DRF backend for the O'zbekiston Iqtisodiyot Assambleyasi website.

It owns every piece of **editorial content** on the site — site settings, home
page copy, the whole about page, associations, services, projects, partners,
news and contact submissions. Editors manage all of it from the Django admin.

Interaction **chrome** (nav labels, "View all", form placeholders) stays in the
frontend's `messages/*.json`. It changes with the code, not with the editor.

## Quick start

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate        # Windows (Git Bash); use .venv/bin/activate on Linux/macOS
uv sync --locked

cp .env.example .env
python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
# paste that into SECRET_KEY in .env

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Control panel: <http://127.0.0.1:8000/admin/>
API root: <http://127.0.0.1:8000/api/v1/>

## Importing the existing site content

The site's content currently lives in `messages/*.json` and `src/data/*.ts`.
Move it into the database in two steps, from the **repo root**:

```bash
node --experimental-strip-types backend/seed/export_frontend_data.mjs
cd backend && python manage.py seed_content
```

`seed_content` is idempotent — it matches on natural keys and updates in place,
so running it twice never duplicates rows. It is a **migration tool, not a
merge**: it overwrites edits made in the admin. Use `--dry-run` to preview.

Once Django owns the content, the static files it reads from become dead.

## API

Every endpoint takes `?locale=uz|ru|en` (default `uz`). An unknown locale falls
back to Uzbek rather than erroring, so a malformed query string can never take a
public page down. Responses are already flattened to the requested locale — the
per-locale `*_uz` / `*_ru` / `*_en` columns are never exposed.

A blank translation falls back to Uzbek, so editors can publish in one language
and fill in the others later without the site rendering empty strings.

| Method | Path | Notes |
|---|---|---|
| GET | `/api/v1/site/` | Name, tagline, contacts, social links |
| GET | `/api/v1/home/` | Hero, section headings, CTA banner, stats |
| GET | `/api/v1/about/` | Every about-page block |
| GET | `/api/v1/associations/` | Published only |
| GET | `/api/v1/associations/<slug>/` | |
| GET | `/api/v1/services/` | Published only |
| GET | `/api/v1/projects/` | Blank `url` means "in development" |
| GET | `/api/v1/partners/` | Groups with nested partners |
| GET | `/api/v1/news/` | Published, newest first, no body |
| GET | `/api/v1/news/<slug>/` | Adds `body` as a list of paragraphs |
| POST | `/api/v1/contact/` | The only write endpoint |

Association slugs are generated with the same rules as the frontend's
`slugify()` in `src/data/associations.ts`, so existing URLs keep working. There
is a test (`catalog.tests.SlugifyParityTests`) that fails if the two drift.

### Contact endpoint

```json
POST /api/v1/contact/
{"name": "Aziz", "email": "a@example.com", "message": "...", "locale": "uz"}
```

- Rate limited per IP (`CONTACT_THROTTLE_RATE`, default `5/hour`). Reads are never throttled.
- `website` is a honeypot field. Humans never see it, so anything that fills it
  is a bot: the request answers `201` but stores nothing, so the bot cannot tell
  acceptance from rejection.
- The submission is saved **before** the notification email is sent. A mail
  outage loses a notification, never the visitor's message.

## Drafts

`Article.published` excludes unpublished posts and any dated in the future, so a
draft is not reachable by guessing its slug. Only `is_published=True` articles
with `published_on <= today` appear in the API.

## Control panel languages

The admin interface itself is available in Uzbek, Russian and English. A
switcher in the header (also on the login page, where an editor who cannot read
English needs it most) posts to `set_language`, which stores the choice in the
session. Uzbek is the default; without a stored choice, `Accept-Language` wins,
then `LANGUAGE_CODE`.

Translated: model and app names, fieldset headings, admin actions, custom
columns, and change-form field labels — `hero_title_uz` renders as
"Bosh blok sarlavhasi (UZ)". Labels are resolved at render time by
`core.admin.LocalizedLabelsMixin` rather than via `verbose_name`, which would
mean an `AlterField` migration for each of the ~300 per-locale columns.

Django ships a complete Russian admin catalogue but only a partial Uzbek one.
`locale/uz` fills the gaps (`Log in`, `Home`, `History`, `username`, …).
`LOCALE_PATHS` takes precedence over Django's own catalogues, so those entries
win. Russian is left to Django — overriding a complete upstream translation
would be a regression.

Three plural count strings ("0 of N selected") are deliberately left in English
for Uzbek: a wrong plural rule reads worse than English.

### Editing translations

Edit the `.po`, then recompile:

```bash
# edit locale/uz/LC_MESSAGES/django.po
python scripts/compile_messages.py
```

`manage.py compilemessages` shells out to GNU gettext's `msgfmt`, which is not
installed on Windows by default. `scripts/compile_messages.py` uses polib
(pure Python) and is equivalent. The compiled `.mo` files are committed, so no
deployment needs gettext. A test fails if a `.mo` is older than its `.po`.

Note that `LocaleMiddleware` adds `Accept-Language` to the `Vary` header on all
responses, including the API. API *content* is unaffected — it is selected by
`?locale=`, never by `Accept-Language`.

## Configuration

All configuration is environment-driven; see `.env.example`. `SECRET_KEY` has no
default — the process refuses to start without it rather than falling back to a
well-known value.

Notable settings:

- `ADMIN_URL` — move the control panel off `/admin/` in production.
- `CORS_ALLOWED_ORIGINS` — the Next.js origin, and nothing else. Never use `CORS_ALLOW_ALL_ORIGINS`.
- `DATABASE_URL` — SQLite locally, Postgres in production.
- When `DEBUG=False`, HSTS, SSL redirect and secure cookies switch on automatically.

## Tests

```bash
python manage.py test
```

125 tests. To measure coverage:

```bash
uv add --dev coverage
uv run coverage run --source='.' --omit='*/migrations/*,*/tests.py,*/test_*.py,manage.py,scripts/*,config/wsgi.py,config/asgi.py' manage.py test
uv run coverage report
```

## Docker

`docker-compose.yml` brings up Postgres and the API. It reads secrets from
`backend/.env` and contains none itself. Set `POSTGRES_PASSWORD` there first.

```bash
docker compose up --build
docker compose exec api python manage.py migrate
docker compose exec api python manage.py createsuperuser
```

## Deployment notes

- Set `DEBUG=False` and a real `ALLOWED_HOSTS`.
- Run `python manage.py collectstatic` so the admin CSS is served.
- Put the API behind TLS. `SECURE_PROXY_SSL_HEADER` is already configured for a
  reverse proxy that sets `X-Forwarded-Proto`.
- `gunicorn` does not run on Windows; deploy on Linux.
