# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Run everything from `src/`** (`cd src`) with the project's virtualenv active — `manage.py` lives there and `src/` is the Python import root. Settings come from `.env` at the repo root (read via `decouple.AutoConfig` in `src/config/settings.py`).

Dependencies are managed by **uv** (`pyproject.toml` + `uv.lock` at the repo root; `.python-version` pins 3.13). `uv sync` builds `.venv/`; `uv add` / `uv remove` change deps — never hand-edit `uv.lock`, and don't reintroduce `requirements.txt`. `requires-python` is `>=3.12` because Django 6.0 requires it; note `django-jazzmin` independently floors the project at 3.10, so neither constraint can be relaxed without dropping a dependency. `uv run <cmd>` works without activating the venv. `[tool.uv] package = false` is required — `src/` is deliberately not a package, so there is nothing to build or install.

- Run dev server: `python manage.py runserver`
  - ASGI is configured (`daphne` + `channels`); `runserver` works for HTTP, use `daphne config.asgi:application` for WebSocket testing.
- Migrations: `python manage.py makemigrations` / `python manage.py migrate`
- Tests — every test lives under `src/infrastructure/tests/`, in a package mirroring `domains/` (`accounts/`, `apps/foodie/`, `company/hr/staff/`, plus `common/`, `utils/`, `external_services/`). Apps have no `tests.py` of their own.
  - All: `python manage.py test`
  - One domain: `python manage.py test infrastructure.tests.apps.spending_tracker`
  - Single test: `python manage.py test infrastructure.tests.apps.spending_tracker.test_recurring.TestClassName.test_method`
  - Test discovery walks up from the cwd, so it only finds everything when run from `src/`.
  - Modules are named for what they cover (`test_recurring.py`, `test_api.py`); fixtures shared across a package's modules go in that package's `helpers.py`. When changing an app whose domain has no test package yet (`blog`, `jotter`, `throw_a_die`, `flip_a_coin`, `interest_calc`), create one for the new/changed behavior.
- Collect static: `python manage.py collectstatic --noinput`
- Switch DB: set `DEFAULT_DB=sqlite` or `DEFAULT_DB=postgres` in `.env` (both are pre-configured in `settings.DATABASES`).
- Switch storage: `MEDIA_STORAGE=LOCAL` or `AWS` in `.env` (S3 backend wired via `django-storages`).

App-specific management commands (full list in `README.md`) are all one-off seeds/migrations — blog content/tag migrations, S3 image migrations per app (`migrate_*_images_to_s3`), thumbnail generators (`generate_*_thumbnails`), `seed_themes`, `seed_hobbies`, `generate_vapid_keys`, `setup_admin_totp`. Each is a presentation-only wrapper: the logic lives in the domain's `services.py` and takes an optional `on_progress(message, level)` callback, adapted from the command by `common.management_utils.command_progress`. Recurring work is not a command at all — see "Scheduled jobs".

`/admin/` needs a TOTP code as well as a password (see "Admin two-factor" below). Bootstrap the *first* account with `python manage.py setup_admin_totp <username>`; once you can get in, enrol everyone else from the User change page (see "Admin two-factor").

## Architecture

Single Django project migrating from stock Django MVT toward a repository-pattern layout. The migration is incremental — expect further moves.

### Layout

```
<repo root>          .env, db.sqlite3, media/, staticfiles/, build.sh
└── src/             the Python import root (deliberately NOT a package — no __init__.py)
    ├── manage.py
    ├── config/                the Django settings module only (settings, urls, wsgi/asgi)
    ├── common/                cross-cutting code (admin, middleware, mixins, pagination, storage)
    ├── infrastructure/        utils/, external_services/, scheduler/, tests/, words/
    ├── domains/               feature apps
    │   ├── accounts/ author/ home/ pwa/ theme/
    │   └── apps/              blog/ foodie/ spending_tracker/ jotter/ rhymes/
    │                          throw_a_die/ flip_a_coin/ interest_calc/ generate_invoice/
    ├── templates/             project-level templates (TEMPLATES.DIRS)
    └── static/                project-level static (STATICFILES_DIRS)
```

Import roots are therefore `config.*`, `common.*`, `infrastructure.*` and `domains.*` — never prefixed with `src.`. `config/` holds the Django settings module and nothing else (kept deliberately thin); `common/` holds project-wide cross-cutting code; third-party clients and shared helpers stay in `infrastructure/utils/` and `infrastructure/external_services/`. There is no top-level `utils` package.

`settings.BASE_DIR` is the repo root (owns `.env`, the sqlite file, `media/`, `staticfiles/`); `settings.SRC_DIR` is `src/`. Use `SRC_DIR` for anything under `src/`.

Django app labels are unchanged by the move (the label is the last path component, e.g. `domains.apps.blog` → `blog`), so existing migrations and DB tables still apply.

Routing is centralized in `src/config/urls.py` — each app owns its own `urls.py` and is mounted from there. There is no REST API layer; views are server-rendered with Django templates. `TEMPLATES.DIRS` is `SRC_DIR/templates` and `APP_DIRS=True`, so both project-level and per-app template dirs are searched. Template names resolve relative to those roots, so they are unaffected by where the app package sits on disk.

### Apps and what they own
- `accounts` — auth flows, the `user_profile` model (profile images, contact), and `services.py` (TOTP device/backup-code issuing, QR rendering, setup-link signing). Django's stock `auth.User` is still the user model. `user_profile` is edited as a `StackedInline` on the User change page and is deliberately **not** registered on its own, so `admin:accounts_user_profile_*` does not reverse and it has no sidebar entry.
- `author` — public author profile (`/@sean_or_tony`), about/contact, hobbies/stack/education models.
- `home` — landing page, error handlers (`handler404`/`handler500` set in `config/urls.py`), `domains.home.log_handler.DatabaseLogHandler` (DB-backed logging sink for ERROR+ — see `LOGGING` in settings).
- `blog` — CKEditor 5 rich text posts, image/video uploads (size-limited via `BLOG_UPLOAD_MAX_SIZE_MB` / `BLOG_VIDEO_MAX_SIZE_MB` → drives `DATA_UPLOAD_MAX_MEMORY_SIZE`), tags + read groups normalization commands. Note `blog/images/` and `blog/media/` are *storage* key prefixes, not repo paths.
- `foodie` — meals with categories, search autocomplete, image thumbnails. Current meal slot is resolved by `domains.apps.foodie.services._current_mealtime`: for authenticated users, it picks the user's `UserMealSchedule` slot whose `time` is the latest one ≤ now (wrapping to the last slot when now precedes all of them); the `'fancy'` pseudo-slot is excluded from this resolution. No schedule / anonymous → hour-band fallback in the same function. Tests mock `domains.apps.foodie.services.datetime` to control "now".
- `spending_tracker` — accounts/transactions/categories/tags, currency-aware. Invariants: idempotency token in session, 24h edit window via `Transaction.is_editable`, `TransactionForm(data, user=...)` requires the `user` kwarg.
- `jotter`, `rhymes`, `throw_a_die`, `flip_a_coin`, `interest_calc`, `generate_invoice` — small standalone tools.
- `theme` — gated behind `IS_THEME_ENABLED` flag; injects CSS via `domains.theme.context_processors.theme_css`.
- `pwa` — service worker, manifest, web push (VAPID keys required in `.env`). `sw.js`/`manifest.json` are read off disk from `SRC_DIR/static/`.
- `domains/company/` — the marketing site's read-only DRF API, mounted at `/api/company/` from `domains/company/urls.py`; each subdomain owns its `urls.py` and is included there. `products` (work we've shipped) and `faqs` (question/answer accordion, optional `FAQCategory` sections). Both follow the same layout — `models.py`, `serializers.py`, `services/` holding the querysets and filter validation, `apis/` as thin `APIView`s that translate a `*FilterError` into a 400, and a `seed_*` management command. App labels are namespaced (`company_products`, `company_faqs`) since the directory name alone would collide.

### Cross-cutting infrastructure
- `common/middleware/` — `BotScannerMiddleware` (first in chain) and `RateLimitMiddleware` (last). Per-path limits in `settings.RATE_LIMIT_CONFIG`; storage is the default `LocMemCache` so limits are per-process, not cluster-wide.
- `infrastructure/external_services/` — one package per vendor: `google/recaptcha.py` (v3 verification, threshold from `RECAPTCHA_SCORE_THRESHOLD`), `ipqualityscore/email_validation.py`, and `weather/` (provider factory selected by `WEATHER_PROVIDER` / `GEOLOCATION_PROVIDER`; import the providers from `...external_services.weather`, the package root re-exports nothing). `weather/providers/` is a package — one module per upstream (`open_meteo.py`, `ip_api.py`) plus `wmo.py` for the shared code→(text, icon) table; its `__init__` re-exports both classes and quiets the httpx loggers, so `...weather.providers import X` still works.
- `common/context_processors.py` — exposes `RECAPTCHA_SITE_KEY` to all templates.
- CSRF: `static/js/csrf.js` (loaded from `base.html`) rewrites every rendered `csrfmiddlewaretoken` from the cookie at submit time, so service-worker-cached or long-open pages don't post a stale token; use its `csrfFetch` for JS POSTs. Failures land on `CSRF_FAILURE_VIEW` → `domains.home.views.error_handlers.csrf_failure`, which re-issues the cookie and offers a one-click retry (same-origin posts only, sensitive fields and uploads never replayed).
- `infrastructure/utils/` — `media.py` (`MediaHelper` for thumbnail generation, used across foodie/accounts), `choices.py` (`BaseChoices`, the `TextChoices` base every model enum subclasses), `admin.py` (`RichTextAdminMixin`, `install_select2_m2m`), `widgets.py` (`Select2MultipleWidget`), `email.py`, `validators.py`, `profanity.py`. The package `__init__` re-exports everything but `contains_profanity`.
- Scheduled jobs — recurring work is **not** a management command per app. `infrastructure/scheduler/jobs/` holds one module per domain; each job is a function decorated with `@scheduled_job(trigger=..., id=...)` that calls straight into that domain's `services`, and the decorator appends it to `SCHEDULED_JOBS` in `registry.py`. `jobs/__init__` imports every job module — a job module missing from it is silently never registered. There is deliberately no separate tasks layer between job and service: without a queue it would only forward the call.
  - There is no daemon and no task queue. `infrastructure/scheduler/run_jobs.py` is a standalone script (bootstraps Django itself: `src/` onto `sys.path`, `DJANGO_SETTINGS_MODULE`, `django.setup()`) run by a PythonAnywhere Scheduled Task; `python manage.py run_jobs` is the same thing locally, and `--job <id>` forces one regardless of dueness without disturbing its schedule. The `sys.path` hop counts directories, so moving that script changes it.
  - **The tick rate is deliberately not load-bearing.** Dueness is never a match against the current clock — `domains.home.ScheduledJobRun` stores a `next_run_at` per job id, the runner fires everything with `next_run_at <= now`, then advances it with `triggers.next_fire_time(job, now)`. So a job declared `hour=19, minute=0` fires once a day whether the runner is invoked every minute, every 15, or hourly, and a tick that never lands exactly on 19:00 still fires it. Changing the PA task's frequency needs no code change.
  - Advancing from `now` rather than from the missed time **coalesces**: an outage spanning eight hourly fires produces one run, not a backlog of eight.
  - `trigger='cron'` takes `hour` and `minute`, each an int, an iterable or `'*'` (minute defaults to 0 — omitting it on an `hour='*'` job is what makes it hourly rather than every minute). `trigger='interval'` takes `seconds`/`minutes`/`hours`, anchored to local midnight so fires land on predictable clock times; a period that does not divide the day restarts at midnight rather than drifting.
  - `misfire_grace` (seconds) skips a run already later than that and reschedules — for work that is worthless once its moment passed, like `send_meal_notifications` (30 min). Omit it for work that must happen even if late, like `process_recurring_transactions`. A skipped run is reported as `status='misfired'` and does **not** set `last_run_at`.
  - A newly registered job is stored with its next fire *ahead* of now, so deploying one never fires it immediately. The due check runs under `select_for_update` so two overlapping ticks cannot both claim the same due time (a no-op on sqlite, which is what prod runs).
  - Jobs should still be idempotent where it is cheap to be: `--job` forces reruns, and the lock is only as strong as the DB. Both current jobs are.
  - `run_jobs` lives in `domains/home/management/commands/` because `common/` is **not** an installed app — its `AppConfig`s stand in for `django.contrib.admin`, so Django never discovers commands there.
- `common/pagination.py` — `DefaultAPIPagination` (DRF page-number class, sizes from `API_PAGE_SIZE`/`API_MAX_PAGE_SIZE`) and `apply_view_pagination(data, page_number, per_page)` for server-rendered views.
- Storage abstraction: when `MEDIA_STORAGE=AWS`, both `default` and `staticfiles` storages route to S3 with `AWS_S3_BUCKET_PREFIX`. Don't hardcode local-path assumptions in new image-handling code — go through `MediaHelper`. On `LOCAL`, staticfiles uses `common.storage.AdminSafeStaticFilesStorage` (whitenoise manifest storage plus a one-name allowlist for jazzmin's `{% static 'vendor/bootswatch' %}`, which points at a directory and so has no manifest entry). Only the S3 path lacks a manifest, so manifest bugs surface on `LOCAL` and in tests (which run with `DEBUG=False`) but not on `AWS`.

### Conventions to preserve
- Env access goes through `decouple`'s `config(...)` in `settings.py` with an explicit `cast=`; read env only in settings, then import from `django.conf.settings`.
- New apps: create under `src/domains/` (or `src/domains/apps/` for small tools), set `AppConfig.name` to the full dotted path (e.g. `domains.apps.foo`), register that path in `INSTALLED_APPS`, and mount it in `config/urls.py`. Place templates either in the app's `templates/<app>/` or under `src/templates/<app>/` (existing apps mix both — match the neighbors).
- When moving an app, remember migrations can hold fully-qualified references in their *bodies* (`upload_to=`, `validators=`), not just imports — both need updating.
- Errors that should surface in admin go through standard logging; the DB log handler captures `django` and `django.request` at ERROR+.
- HTTPS is forced when `DEBUG=False` (`SECURE_SSL_REDIRECT`).
- dont comment unless absolutely necessary. and if you have to, use concise one liners

## Deployment

Host is **PythonAnywhere**, deployed by `.github/workflows/deploy-pythonanywhere.yml` on push to `master` (SSH → `git pull` → `uv sync --frozen --no-dev` → `migrate` → `collectstatic` → touch the WSGI file to reload → health check).

- **`apps.seoto.org` is the Django app**; `seoto.org` is a separate marketing site. The `APP_DOMAIN` secret must be the former — it selects both the health-check target and the WSGI filename (`/var/www/apps_seoto_org_wsgi.py`). Probing `seoto.org` returns a green 200 from an app that was never deployed.
- Project dir is `~/<PA_USERNAME>.pythonanywhere.com`, the venv is `.venv` **inside** it (not `~/.virtualenvs/`), and the Web tab's Virtualenv field holds that absolute path. `workon` only sees `~/.virtualenvs`, so it needs a symlink there to keep working.
- PythonAnywhere kills sessions that emit too much output, so uv runs with `--no-progress`; `--python-preference only-system` stops uv downloading a ~33MB interpreter into a quota-limited home, and `uv cache prune --ci` keeps the wheel cache off the quota. Disk quota is the binding constraint — this dependency set is ~400MB installed, so two copies of it do not fit.
- The PA WSGI file is hand-written, lives outside the repo, and is **not** `src/config/wsgi.py`. It only needs to put `src/` on `sys.path` and set `DJANGO_SETTINGS_MODULE`; it must not load `.env` itself, since `settings.py` reads it via `AutoConfig(search_path=BASE_DIR)` from the repo root.
- Because `uv sync` prunes to match the lock exactly, anything hand-installed into the venv disappears on the next deploy. Undeclared packages that survived under `pip install -r` will surface as `ModuleNotFoundError` — declare them in `pyproject.toml` or remove the import.
- Prod runs on **sqlite** (`DEFAULT_DB=sqlite`), same as dev.