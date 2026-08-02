# Seoto

A single Django project hosting a personal site and a collection of small, self-contained
feature apps — a blog, a meal picker, a spending tracker, an author profile, and several
standalone tools. Views are server-rendered with Django templates; there is no separate REST
API layer. The project is ASGI-ready (Daphne + Channels) and ships as a PWA with web push.

## Stack

- **Python / Django** (ASGI via Daphne + Channels)
- **Database:** SQLite by default, PostgreSQL optional (`dj-database-url`, `psycopg2`)
- **Storage:** local filesystem by default, S3 optional (`django-storages`)
- **Static files:** WhiteNoise
- **Rich text:** CKEditor 5
- **Web push:** VAPID (`pywebpush`)
- **Deploy:** PythonAnywhere (GitHub Actions workflow, build via `build.sh`)

## Apps

| App | What it owns |
| --- | --- |
| `accounts` | Custom user model, auth flows, profile images |
| `author` | Public author profile (`/@sean_or_tony`), about/contact, hobbies/stack/education |
| `home` | Landing page, error handlers, DB-backed logging sink |
| `blog` | CKEditor 5 posts, image/video uploads, tags + read groups |
| `foodie` | Meals with categories, search autocomplete, schedule-aware meal-slot resolution |
| `spending_tracker` | Accounts, transactions, categories, tags (currency-aware) |
| `jotter` | Quick notes |
| `interest_calc`, `throw_a_die`, `flip_a_coin`, `rhymes` | Standalone tools |
| `generate_invoice` | Invoice generation |
| `theme` | Theme presets, gated behind `IS_THEME_ENABLED`; injects CSS via context processor |
| `pwa` | Service worker, manifest, web push (VAPID) |

Apps live under `src/domains/`; the Django project package is `src/infrastructure/core/`.
Routing is centralized in `src/infrastructure/core/urls.py`; each app mounts its own `urls.py`
from there. See `CLAUDE.md` for deeper architecture notes.

## Getting started

Requires Python 3 and `pip`. Create a virtualenv and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create your environment file and fill in values:

```bash
cp .env.example .env
```

At minimum set `SECRET_KEY`. Settings are read via `python-decouple` (OS env vars override
`.env`). See `.env.example` for all options — database, email, media storage, VAPID, reCAPTCHA,
and feature flags.

Set up the database and run the server. `manage.py` lives in `src/`, which is also the
Python import root — run all management commands from there:

```bash
cd src
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

`runserver` is fine for HTTP. For WebSocket / Channels testing, run under Daphne:

```bash
daphne infrastructure.core.asgi:application
```

## Configuration

All settings come from `.env` (see `.env.example`). Common toggles:

- **Database:** `DEFAULT_DB=sqlite` or `postgres` (Postgres vars only needed when selected).
- **Media storage:** `MEDIA_STORAGE=LOCAL` or `AWS` (S3 vars only needed when `AWS`).
- **Theme feature:** `IS_THEME_ENABLED=True/False`.
- **Web push:** generate keys with `python manage.py generate_vapid_keys` and paste into `.env`.
- **reCAPTCHA v3:** leave keys blank to skip verification locally.

## Testing

There is no top-level test config; tests run per app. Run from `src/` — discovery walks up
from the working directory, so it only finds every app when started there.

```bash
cd src
python manage.py test                                  # all apps
python manage.py test domains.apps.spending_tracker    # single app
python manage.py test domains.apps.spending_tracker.tests.TestClassName.test_method
```

## Deployment

Deployment targets PythonAnywhere. Pushing to `master` triggers
`.github/workflows/deploy-pythonanywhere.yml`, which pulls the branch over SSH, installs
requirements, then runs migrations and `collectstatic` from `src/` and reloads the web app.

`build.sh` does the same collect-static + migrate pair locally, if you need to run it by hand:

```bash
bash build.sh
```

HTTPS is forced when `DEBUG=False` (`SECURE_SSL_REDIRECT`).

## Management commands

### Blog

#### `migrate_blog_to_richtext`
Converts existing blog post content from Markdown to HTML. Safe to re-run — skips posts whose content already appears to be HTML.

```bash
python manage.py migrate_blog_to_richtext --dry-run   # preview
python manage.py migrate_blog_to_richtext
```

#### `sanitize_tags_and_groups`
Normalizes existing blog tags to **singular lowercase** and read groups to **plural lowercase**. Merges duplicates that arise after normalization by reassigning all post/member references before deleting the stale record.

```bash
python manage.py sanitize_tags_and_groups --dry-run   # preview
python manage.py sanitize_tags_and_groups
```

#### `cleanup_orphan_blog_images`
Scans the `blog/images/` and `blog/media/` directories in storage and deletes any media files (images, video, audio, documents) not referenced in any live post. Run after bulk post deletions or as periodic maintenance.

```bash
python manage.py cleanup_orphan_blog_images --dry-run   # preview
python manage.py cleanup_orphan_blog_images
```

### Accounts

#### `migrate_accounts_images_to_s3`
Migrates user profile images from local storage to S3. Requires `MEDIA_STORAGE=AWS` to be configured.

```bash
python manage.py migrate_accounts_images_to_s3
```

#### `generate_profile_thumbnails`
Generates or regenerates 80×80 JPEG thumbnails for all user profile pictures that are missing a thumbnail.

```bash
python manage.py generate_profile_thumbnails
```

### Author

#### `migrate_author_images_to_s3`
Migrates author profile images from local storage to S3. Requires `MEDIA_STORAGE=AWS` to be configured.

```bash
python manage.py migrate_author_images_to_s3
```

#### `seed_hobbies`
Seeds the database with a default set of hobby options for author profiles.

```bash
python manage.py seed_hobbies
```

### Foodie

#### `migrate_foodie_images_to_s3`
Migrates meal images from local storage to S3. Requires `MEDIA_STORAGE=AWS` to be configured.

```bash
python manage.py migrate_foodie_images_to_s3
```

#### `generate_foodie_thumbnails`
Generates or regenerates thumbnails for all meal images that are missing one.

```bash
python manage.py generate_foodie_thumbnails
```

### Spending Tracker

#### `process_recurring_transactions`
Processes due recurring transactions: auto-creates the transaction (`is_auto_renew=True`) or sends a push/in-app notification asking the user to approve it (`is_auto_renew=False`). Idempotent — safe to re-run for the same day. Intended to run once a day; since this app has no task queue, add it as a daily **PythonAnywhere Scheduled Task** at the time configured by the `RECURRING_TRANSACTIONS_CRON` env var (default `0 19 * * *`, i.e. 7pm) — the command logs a warning if it's invoked more than an hour off that time.

```bash
python manage.py process_recurring_transactions
```

### Theme

#### `seed_themes`
Seeds the database with the 5 official theme presets (Light, Dark, High Contrast, Ocean, Forest). Safe to re-run — uses `update_or_create`.

```bash
python manage.py seed_themes
```

### PWA

#### `generate_vapid_keys`
Generates a VAPID key pair for web push notifications and prints the values to add to `.env`.

```bash
python manage.py generate_vapid_keys
```
