# Seoto

A single Django project hosting a personal site and a collection of small, self-contained
apps — a blog, a meal picker, a spending tracker, an author profile, and several
standalone tools. Views are server-rendered with Django templates; there is no separate REST
API layer. The project is ASGI-ready (Daphne + Channels) and ships as a PWA with web push.

## Stack

- **Python / Django** (ASGI via Daphne + Channels)
- **Database:** SQLite by default, PostgreSQL optional (`dj-database-url`, `psycopg2`); Docker runs PostgreSQL behind PgBouncer
- **Background work:** Celery worker + Celery beat on Redis (Docker); Redis also backs the cache
- **Storage:** local filesystem by default, S3 optional (`django-storages`)
- **Static files:** WhiteNoise
- **Rich text:** CKEditor 5
- **Admin:** jazzmin skin, TOTP second factor (`django-otp`)
- **Web push:** VAPID (`pywebpush`)
- **Deploy:** Docker Compose behind Traefik (HTTPS via Let's Encrypt); previously PythonAnywhere (GitHub Actions workflow, build via `build.sh`)

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

Apps live under `src/domains/`; the Django project package is `src/config/` (settings,
urls, wsgi/asgi, celery) and shared cross-cutting code lives in `src/common/`.
Routing is centralized in `src/config/urls.py`; each app mounts its own `urls.py`
from there. See `CLAUDE.md` for deeper architecture notes.

## Getting started

Dependencies are managed with [uv](https://docs.astral.sh/uv/). Install it, then sync — this
creates `.venv/` on the Python pinned in `.python-version` (3.13) and installs the exact
versions in `uv.lock`:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync
```

The project requires Python >= 3.12 (Django 6.0). `uv` downloads a matching interpreter if the
system has none. Prefix commands with `uv run` instead of activating the venv, or activate it
the usual way with `source .venv/bin/activate`.

To add or remove a dependency, use `uv add <pkg>` / `uv remove <pkg>` — both update
`pyproject.toml` and `uv.lock` together. Commit the lockfile.

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
python manage.py setup_admin_totp <username>   # required — see Admin access below
python manage.py runserver
```

`runserver` is fine for HTTP. For WebSocket / Channels testing, run under Daphne:

```bash
daphne config.asgi:application
```

## Running with Docker

`compose.yaml` runs the whole stack:

| Service | What it does |
| --- | --- |
| `traefik` | Public entrypoint. Terminates HTTPS (Let's Encrypt), redirects HTTP → HTTPS. The only service with published ports. |
| `web` | Django under gunicorn. Runs `relabel_apps` + `migrate` on start; serves static files baked into the image. |
| `worker` | Celery worker — executes background tasks. |
| `beat` | Celery beat — sends the scheduled-jobs tick every minute. Run exactly one. |
| `pgbouncer` | Connection pooler (transaction mode) between Django and Postgres. |
| `postgres` | PostgreSQL 18. Data in the `postgres` volume. |
| `redis` | Celery broker (db 0) and Django cache (db 1, shared rate limits). |

Every command takes `--env-file <file>`: it supplies both the values compose interpolates
(Postgres credentials, host name, ports) and the env the containers read. Without it, compose
stops with a missing-variable error rather than silently using the dev `.env`.

### Locally

`.env.docker.local` (gitignored) holds safe local values: `https://apps.localhost:8443`, local
media, no real credentials. If you don't have one, create it from `.env.example`: fill in the
`DOCKER` block with the local values shown there, and set `ALLOWED_HOSTS=apps.localhost`,
`CSRF_TRUSTED_ORIGINS=https://apps.localhost:8443`, `APP_DOMAIN=https://apps.localhost`,
`DEBUG=False`.

1. Start Docker Desktop.
2. Build and start everything:
   ```bash
   docker compose --env-file .env.docker.local up -d --build --wait
   ```
3. Optional — load your dev data (only into an empty database, so start fresh):
   ```bash
   docker compose --env-file .env.docker.local down -v
   ENV_FILE=.env.docker.local docker/sqlite_to_postgres.sh db.sqlite3
   ```
   This brings your dev users and their TOTP devices along; skip step 4 if you do it.
4. Create an admin and enrol TOTP (interactive — scan the QR, type the code):
   ```bash
   docker compose --env-file .env.docker.local exec web python manage.py createsuperuser
   docker compose --env-file .env.docker.local exec web python manage.py setup_admin_totp <username>
   ```
5. Open **https://apps.localhost:8443** in Chrome or Firefox and accept the self-signed
   certificate warning (Traefik can't get a real certificate for `localhost`). Use the
   `https://…:8443` URL directly — the HTTP redirect points at port 443. If your browser
   doesn't resolve `apps.localhost`, add `127.0.0.1 apps.localhost` to `/etc/hosts`.

Uploaded media isn't served locally (`MEDIA_STORAGE=LOCAL` with `DEBUG=False`); email goes
to [Mailpit](https://mailpit.axllent.org/) on the host at port 1025 if it is running.

### Everyday commands

Locally use `--env-file .env.docker.local`; on the server, `--env-file .env.prod`.

```bash
docker compose --env-file .env.docker.local ps                          # web/postgres/pgbouncer/redis show (healthy)
docker compose --env-file .env.docker.local logs -f web worker beat     # logs
docker compose --env-file .env.docker.local up -d --build               # rebuild after code changes
docker compose --env-file .env.docker.local exec web python manage.py <command>
docker compose --env-file .env.docker.local exec web python manage.py run_jobs --job <id>  # force a job now
docker compose --env-file .env.docker.local down                        # stop, keep data
docker compose --env-file .env.docker.local down -v                     # stop and wipe Postgres, Redis, certificates
```

### Celery, Redis and beat

- **Beat is only the clock.** Every minute it queues
  `infrastructure.scheduler.tasks.run_due_jobs_task`; a worker runs it, and the existing
  scheduler decides which jobs are actually due (see [Scheduled jobs](#scheduled-jobs)). Downtime
  never produces a backlog, and job history stays in `home.ScheduledJobRun`. Run exactly one
  `beat`, or every tick is sent twice.
- **Adding background work:** put a `@shared_task` in the domain's `tasks.py` (auto-discovered)
  that calls into its `services`, then `.delay()` it from a view or service. Worker
  concurrency is set on the `worker` command in `compose.yaml`.
- **Redis** is the broker (db 0) and the Django cache (db 1), so login rate limits are shared
  by every gunicorn worker. Without `REDIS_URL` (plain `runserver`), Celery uses an
  in-memory broker and the cache is per-process.

### Production

1. On the server, put `.env.prod` next to `compose.yaml` with `DEBUG=False`, a fresh
   `SECRET_KEY`, `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD`, `APP_HOST` and
   `ACME_EMAIL` (see the `DOCKER` block in `.env.example`).
2. Point the domain's DNS at the server and open ports 80 and 443.
3. Start it: `docker compose --env-file .env.prod up -d --build`. Traefik requests the
   certificate on first start.
4. Moving from the old SQLite database: `docker/sqlite_to_postgres.sh path/to/db.sqlite3`.
   It works on a copy (the original is never touched), migrates it, prunes stale content
   types, dumps it, then flushes and loads Postgres. It refuses to run if Postgres already
   has users.

Back up Postgres separately, e.g.
`docker compose --env-file .env.prod exec -T postgres pg_dump -U seoto seoto > backup.sql`.

## Admin access

`/admin/` requires two factors: password plus a rotating code from an authenticator app
(Google Authenticator, 1Password, Authy, Bitwarden — anything that speaks TOTP). A staff
user with no verified device is treated as non-staff, so **enrol a device before you need
one**:

```bash
cd src
python manage.py setup_admin_totp <username>
```

It prints a QR code to scan, then asks for the code your app shows so it can prove the
secret took before trusting the device. `--reset` reissues the secret, `--name` adds a
second device (phone plus laptop, say), `--noinput` skips the confirmation prompt.

Mint single-use emergency codes as well — they work in the same field on the login form:

```bash
python manage.py addstatictoken <username>
```

If you are locked out entirely, set `IS_ADMIN_OTP_ENABLED=False` in `.env` and restart.
That drops the admin back to password-only; the enrolled devices survive, so you can
re-enable it once you are back in. Once signed in, devices are also manageable under
**OTP_TOTP → TOTP devices** in the admin (set `OTP_ADMIN_HIDE_SENSITIVE_DATA=True` to hide
secrets and QR codes there).

## Configuration

All settings come from `.env` (see `.env.example`). Common toggles:

- **Database:** `DEFAULT_DB=sqlite` or `postgres` (Postgres vars only needed when selected).
  Behind PgBouncer set `PG_BEHIND_PGBOUNCER=True` (Docker does this for you).
- **Redis:** `REDIS_URL` enables the Celery broker and the shared cache; blank keeps both in-process.
- **Static files:** `STATIC_STORAGE=LOCAL` (WhiteNoise) or `AWS`; defaults to `MEDIA_STORAGE`.
- **HTTPS hardening:** `SECURE_HSTS_SECONDS` (0 = off); `SECRET_KEY_FALLBACKS` for key rotation.
- **Media storage:** `MEDIA_STORAGE=LOCAL` or `AWS` (S3 vars only needed when `AWS`).
- **Theme feature:** `IS_THEME_ENABLED=True/False`.
- **Admin 2FA:** `IS_ADMIN_OTP_ENABLED=True/False`, issuer name via `OTP_TOTP_ISSUER`.
- **Web push:** generate keys with `python manage.py generate_vapid_keys` and paste into `.env`.
- **reCAPTCHA v3:** leave keys blank to skip verification locally.

## Testing

All tests live in `src/infrastructure/tests/`, in packages mirroring `domains/` — so
`domains/apps/spending_tracker/` is covered by `infrastructure/tests/apps/spending_tracker/`.
Run from `src/`: discovery walks up from the working directory, so it only finds everything
when started there.

```bash
cd src
python manage.py test                                            # everything
python manage.py test infrastructure.tests.apps.spending_tracker  # one domain
python manage.py test infrastructure.tests.apps.spending_tracker.test_recurring.TestClassName.test_method
```

Modules within a package are named for what they cover (`test_recurring.py`, `test_api.py`);
fixtures shared between them live in that package's `helpers.py`.

## Deployment

The Docker setup above is the production path going forward. The PythonAnywhere
deployment below still works until the switch-over.

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

#### `setup_admin_totp`
Enrols a TOTP device for a user so they can sign in to the admin. Prints a QR code to scan, then asks for the code shown by the app before trusting the device. See [Admin access](#admin-access).

```bash
python manage.py setup_admin_totp <username>
python manage.py setup_admin_totp <username> --reset          # reissue the secret
python manage.py setup_admin_totp <username> --name Laptop    # add a second device
python manage.py setup_admin_totp <username> --light-terminal # QR for a light background
```

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

### Scheduled jobs

Recurring work is not a set of per-app management commands. Jobs are registered with
`@scheduled_job` in `src/infrastructure/scheduler/jobs/` — one module per domain, each
job calling straight into that domain's `services` — and executed by a single entrypoint
that runs whichever of them are due.

**The trigger frequency is up to you.** Each job stores its own next-run time
(`home.ScheduledJobRun`), so dueness never depends on the tick landing on a particular
minute. A job scheduled for 19:00 fires once a day whether the runner is invoked every
minute, every 5, every 15, or hourly — pick whatever the host makes convenient and
change it later without touching code. Finer ticks only reduce how late a job can start.

#### `run_jobs`
Under Docker nothing needs scheduling — Celery beat ticks every minute (see
[Celery, Redis and beat](#celery-redis-and-beat)). On PythonAnywhere, schedule this as a
Scheduled Task at any frequency:

```bash
python /home/<PA_USERNAME>/<PA_USERNAME>.pythonanywhere.com/src/infrastructure/scheduler/run_jobs.py
```

Locally, or to force one job regardless of whether it is due (this does not disturb its
schedule):

```bash
python manage.py run_jobs
python manage.py run_jobs --job process_recurring_transactions
```

Currently registered:

| Job id | Schedule | Late runs | What it does |
| --- | --- | --- | --- |
| `send_meal_notifications` | hourly, on the hour | skipped after 30 min | Pushes a meal suggestion to each user whose `UserMealSchedule` slot falls in this hour. |
| `process_recurring_transactions` | daily, at the hour in `RECURRING_TRANSACTIONS_CRON` (default `0 19 * * *`, i.e. 7pm) | always run | Auto-creates due recurring transactions (`is_auto_renew=True`) or sends an approval notification (`is_auto_renew=False`). |

Each run reports per job: `ran`, `skipped` (not due), `misfired` (too late to be useful,
rescheduled) or `error` (logged, and never stops the other jobs). If the runner is not
invoked for a long stretch, the missed fires coalesce into a single run rather than a
backlog.

### Company

#### `seed_products`
Seeds the products shown on the marketing site. Re-running skips products that already exist, so copy edited in the admin survives; pass `--refresh` to overwrite it.

```bash
python manage.py seed_products [--refresh]
```

#### `seed_faqs`
Seeds the FAQs shown on the marketing site (mirrors `faqItems` in the `seoto_ui` project). Same `--refresh` semantics as `seed_products`.

```bash
python manage.py seed_faqs [--refresh]
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
