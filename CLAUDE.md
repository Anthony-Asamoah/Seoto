# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Run from the repo root with the project's virtualenv active. Settings come from `.env` (loaded via `python-dotenv` in `seoto/settings.py`).

- Run dev server: `python manage.py runserver`
  - ASGI is configured (`daphne` + `channels`); `runserver` works for HTTP, use `daphne seoto.asgi:application` for WebSocket testing.
- Migrations: `python manage.py makemigrations` / `python manage.py migrate`
- Tests (per app, since there is no top-level test runner config):
  - All: `python manage.py test`
  - Single app: `python manage.py test spending_tracker`
  - Single test: `python manage.py test spending_tracker.tests.TestClassName.test_method`
  - Each app has a `tests.py`; many start as a stub (`from django.test import TestCase`). When changing logic in an app whose `tests.py` is empty/stub, add tests there for the new/changed behavior — don't leave the stub untouched.
- Collect static: `python manage.py collectstatic --noinput`
- Switch DB: set `DEFAULT_DB=sqlite` or `DEFAULT_DB=postgres` in `.env` (both are pre-configured in `settings.DATABASES`).
- Switch storage: `MEDIA_STORAGE=LOCAL` or `AWS` in `.env` (S3 backend wired via `django-storages`).

App-specific management commands (full list in `README.md`): blog content/tag migrations, S3 image migrations per app (`migrate_*_images_to_s3`), thumbnail generators (`generate_*_thumbnails`), `seed_themes`, `seed_hobbies`, `generate_vapid_keys`.

## Architecture

Single Django project (`seoto/`) hosting many small feature apps. Routing is centralized in `seoto/urls.py` — each app owns its own `urls.py` and is mounted from there. There is no REST API layer; views are server-rendered with Django templates from the project-level `templates/` directory (note: `TEMPLATES.DIRS` includes `BASE_DIR/templates`, and `APP_DIRS=True`, so both project-level and per-app template dirs are searched).

### Apps and what they own
- `accounts` — custom user, auth flows, profile images.
- `author` — public author profile (`/@sean_or_tony`), about/contact, hobbies/stack/education models.
- `home` — landing page, error handlers (`handler404`/`handler500` set in `seoto/urls.py`), `home.log_handler.DatabaseLogHandler` (DB-backed logging sink for ERROR+ — see `LOGGING` in settings).
- `blog` — CKEditor 5 rich text posts, image/video uploads (size-limited via `BLOG_UPLOAD_MAX_SIZE_MB` / `BLOG_VIDEO_MAX_SIZE_MB` → drives `DATA_UPLOAD_MAX_MEMORY_SIZE`), tags + read groups normalization commands.
- `foodie` — meals with categories, search autocomplete, image thumbnails. Current meal slot is resolved by `foodie.services._current_mealtime`: for authenticated users, it picks the user's `UserMealSchedule` slot whose `time` is the latest one ≤ now (wrapping to the last slot when now precedes all of them); the `'fancy'` pseudo-slot is excluded from this resolution. No schedule / anonymous → hour-band fallback in the same function. Tests mock `foodie.services.datetime` to control "now".
- `spending_tracker` — accounts/transactions/categories/tags, currency-aware. Invariants: idempotency token in session, 24h edit window via `Transaction.is_editable`, `TransactionForm(data, user=...)` requires the `user` kwarg.
- `jotter`, `rhymes`, `throw_a_die`, `flip_a_coin`, `interest_calc` — small standalone tools.
- `theme` — gated behind `IS_THEME_ENABLED` flag; injects CSS via `theme.context_processors.theme_css`.
- `pwa` — service worker, manifest, web push (VAPID keys required in `.env`).
- `chat` — Channels-based; uses in-memory channel layer (`CHANNEL_LAYERS`).
- `domains` — present at repo root but not in `INSTALLED_APPS`; treat as inactive unless told otherwise.

### Cross-cutting infrastructure
- `seoto/middleware.py` — `BotScannerMiddleware` (first in chain) and `RateLimitMiddleware` (last). Per-path limits in `settings.RATE_LIMIT_CONFIG`; storage is the default `LocMemCache` so limits are per-process, not cluster-wide.
- `seoto/external_services/` — `recaptcha.py` (v3 verification, threshold from `RECAPTCHA_SCORE_THRESHOLD`) and `email_validation.py` (IPQualityScore).
- `seoto/context_processors.py` — exposes `RECAPTCHA_SITE_KEY` to all templates.
- CSRF: `static/js/csrf.js` (loaded from `base.html`) rewrites every rendered `csrfmiddlewaretoken` from the cookie at submit time, so service-worker-cached or long-open pages don't post a stale token; use its `csrfFetch` for JS POSTs. Failures land on `CSRF_FAILURE_VIEW` → `home.views.error_handlers.csrf_failure`, which re-issues the cookie and offers a one-click retry (same-origin posts only, sensitive fields and uploads never replayed).
- `seoto/utils/` — `GetEnv` (typed env reader; all settings go through it), `media.py` (`MediaHelper` for thumbnail generation, used across foodie/accounts), `choices.py`.
- `seoto/mixins/views.py` — shared CBV mixins.
- `utils/paginator.py` — shared pagination helper.
- Storage abstraction: when `MEDIA_STORAGE=AWS`, both `default` and `staticfiles` storages route to S3 with `AWS_S3_BUCKET_PREFIX`. Don't hardcode local-path assumptions in new image-handling code — go through `MediaHelper`.

### Conventions to preserve
- All env access via `seoto.utils.GetEnv as Env` with typed accessors (`Env.str`, `Env.int`, `Env.bool`, `Env.tuple`, `Env.float`). Don't `os.getenv` directly.
- New apps: register in `INSTALLED_APPS`, mount under `seoto/urls.py`, place templates either in the app's `templates/<app>/` or under top-level `templates/<app>/` (existing apps mix both — match the neighbors).
- Errors that should surface in admin go through standard logging; the DB log handler captures `django` and `django.request` at ERROR+.
- HTTPS is forced when `DEBUG=False` (`SECURE_SSL_REDIRECT`).
