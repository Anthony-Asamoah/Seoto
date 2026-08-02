# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Run everything from `src/`** (`cd src`) with the project's virtualenv active — `manage.py` lives there and `src/` is the Python import root. Settings come from `.env` at the repo root (read via `decouple.AutoConfig` in `src/infrastructure/core/settings.py`).

- Run dev server: `python manage.py runserver`
  - ASGI is configured (`daphne` + `channels`); `runserver` works for HTTP, use `daphne infrastructure.core.asgi:application` for WebSocket testing.
- Migrations: `python manage.py makemigrations` / `python manage.py migrate`
- Tests (per app, since there is no top-level test runner config):
  - All: `python manage.py test`
  - Single app: `python manage.py test domains.apps.spending_tracker`
  - Single test: `python manage.py test domains.apps.spending_tracker.tests.TestClassName.test_method`
  - Test discovery walks up from the cwd, so it only finds every app when run from `src/`.
  - Each app has a `tests.py`; many start as a stub (`from django.test import TestCase`). When changing logic in an app whose `tests.py` is empty/stub, add tests there for the new/changed behavior — don't leave the stub untouched.
- Collect static: `python manage.py collectstatic --noinput`
- Switch DB: set `DEFAULT_DB=sqlite` or `DEFAULT_DB=postgres` in `.env` (both are pre-configured in `settings.DATABASES`).
- Switch storage: `MEDIA_STORAGE=LOCAL` or `AWS` in `.env` (S3 backend wired via `django-storages`).

App-specific management commands (full list in `README.md`): blog content/tag migrations, S3 image migrations per app (`migrate_*_images_to_s3`), thumbnail generators (`generate_*_thumbnails`), `seed_themes`, `seed_hobbies`, `generate_vapid_keys`.

## Architecture

Single Django project migrating from stock Django MVT toward a repository-pattern layout. The migration is incremental — expect further moves.

### Layout

```
<repo root>          .env, db.sqlite3, media/, staticfiles/, build.sh
└── src/             the Python import root (deliberately NOT a package — no __init__.py)
    ├── manage.py
    ├── infrastructure/core/   the Django project package (settings, urls, wsgi/asgi, middleware)
    ├── domains/               feature apps
    │   ├── accounts/ author/ home/ pwa/ theme/
    │   └── apps/              blog/ foodie/ spending_tracker/ jotter/ rhymes/
    │                          throw_a_die/ flip_a_coin/ interest_calc/ generate_invoice/
    ├── templates/             project-level templates (TEMPLATES.DIRS)
    ├── static/                project-level static (STATICFILES_DIRS)
    └── utils/                 shared helpers (paginator, admin mixins, enums)
```

Import roots are therefore `infrastructure.core.*`, `domains.*`, and `utils.*` — never prefixed with `src.`.

`settings.BASE_DIR` is the repo root (owns `.env`, the sqlite file, `media/`, `staticfiles/`); `settings.SRC_DIR` is `src/`. Use `SRC_DIR` for anything under `src/`.

Django app labels are unchanged by the move (the label is the last path component, e.g. `domains.apps.blog` → `blog`), so existing migrations and DB tables still apply.

Routing is centralized in `src/infrastructure/core/urls.py` — each app owns its own `urls.py` and is mounted from there. There is no REST API layer; views are server-rendered with Django templates. `TEMPLATES.DIRS` is `SRC_DIR/templates` and `APP_DIRS=True`, so both project-level and per-app template dirs are searched. Template names resolve relative to those roots, so they are unaffected by where the app package sits on disk.

### Apps and what they own
- `accounts` — auth flows and the `user_profile` model (profile images, contact). Django's stock `auth.User` is still the user model.
- `author` — public author profile (`/@sean_or_tony`), about/contact, hobbies/stack/education models.
- `home` — landing page, error handlers (`handler404`/`handler500` set in `infrastructure/core/urls.py`), `domains.home.log_handler.DatabaseLogHandler` (DB-backed logging sink for ERROR+ — see `LOGGING` in settings).
- `blog` — CKEditor 5 rich text posts, image/video uploads (size-limited via `BLOG_UPLOAD_MAX_SIZE_MB` / `BLOG_VIDEO_MAX_SIZE_MB` → drives `DATA_UPLOAD_MAX_MEMORY_SIZE`), tags + read groups normalization commands. Note `blog/images/` and `blog/media/` are *storage* key prefixes, not repo paths.
- `foodie` — meals with categories, search autocomplete, image thumbnails. Current meal slot is resolved by `domains.apps.foodie.services._current_mealtime`: for authenticated users, it picks the user's `UserMealSchedule` slot whose `time` is the latest one ≤ now (wrapping to the last slot when now precedes all of them); the `'fancy'` pseudo-slot is excluded from this resolution. No schedule / anonymous → hour-band fallback in the same function. Tests mock `domains.apps.foodie.services.datetime` to control "now".
- `spending_tracker` — accounts/transactions/categories/tags, currency-aware. Invariants: idempotency token in session, 24h edit window via `Transaction.is_editable`, `TransactionForm(data, user=...)` requires the `user` kwarg.
- `jotter`, `rhymes`, `throw_a_die`, `flip_a_coin`, `interest_calc`, `generate_invoice` — small standalone tools.
- `theme` — gated behind `IS_THEME_ENABLED` flag; injects CSS via `domains.theme.context_processors.theme_css`.
- `pwa` — service worker, manifest, web push (VAPID keys required in `.env`). `sw.js`/`manifest.json` are read off disk from `SRC_DIR/static/`.
- `domains/company/` — empty placeholder, not in `INSTALLED_APPS`; inactive.

### Cross-cutting infrastructure
- `infrastructure/core/middleware.py` — `BotScannerMiddleware` (first in chain) and `RateLimitMiddleware` (last). Per-path limits in `settings.RATE_LIMIT_CONFIG`; storage is the default `LocMemCache` so limits are per-process, not cluster-wide.
- `infrastructure/core/external_services/` — `recaptcha.py` (v3 verification, threshold from `RECAPTCHA_SCORE_THRESHOLD`), `email_validation.py` (IPQualityScore), and `weather/` (provider factory selected by `WEATHER_PROVIDER` / `GEOLOCATION_PROVIDER`).
- `infrastructure/core/context_processors.py` — exposes `RECAPTCHA_SITE_KEY` to all templates.
- CSRF: `static/js/csrf.js` (loaded from `base.html`) rewrites every rendered `csrfmiddlewaretoken` from the cookie at submit time, so service-worker-cached or long-open pages don't post a stale token; use its `csrfFetch` for JS POSTs. Failures land on `CSRF_FAILURE_VIEW` → `domains.home.views.error_handlers.csrf_failure`, which re-issues the cookie and offers a one-click retry (same-origin posts only, sensitive fields and uploads never replayed).
- `infrastructure/core/utils/` — `media.py` (`MediaHelper` for thumbnail generation, used across foodie/accounts), `choices.py`, `validators.py`, `profanity.py`.
- `infrastructure/core/mixins/views.py` — shared CBV mixins.
- `utils/paginator.py` — shared pagination helper.
- Storage abstraction: when `MEDIA_STORAGE=AWS`, both `default` and `staticfiles` storages route to S3 with `AWS_S3_BUCKET_PREFIX`. Don't hardcode local-path assumptions in new image-handling code — go through `MediaHelper`.

### Conventions to preserve
- Env access goes through `decouple`'s `config(...)` in `settings.py` with an explicit `cast=`; read env only in settings, then import from `django.conf.settings`.
- New apps: create under `src/domains/` (or `src/domains/apps/` for small tools), set `AppConfig.name` to the full dotted path (e.g. `domains.apps.foo`), register that path in `INSTALLED_APPS`, and mount it in `infrastructure/core/urls.py`. Place templates either in the app's `templates/<app>/` or under `src/templates/<app>/` (existing apps mix both — match the neighbors).
- When moving an app, remember migrations can hold fully-qualified references in their *bodies* (`upload_to=`, `validators=`), not just imports — both need updating.
- Errors that should surface in admin go through standard logging; the DB log handler captures `django` and `django.request` at ERROR+.
- HTTPS is forced when `DEBUG=False` (`SECURE_SSL_REDIRECT`).
