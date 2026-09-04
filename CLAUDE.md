# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Run everything from `src/`** (`cd src`) with the project's virtualenv active — `manage.py` lives there and `src/` is the Python import root. Settings come from `.env` at the repo root (read via `decouple.AutoConfig` in `src/infrastructure/core/settings.py`).

Dependencies are managed by **uv** (`pyproject.toml` + `uv.lock` at the repo root; `.python-version` pins 3.13). `uv sync` builds `.venv/`; `uv add` / `uv remove` change deps — never hand-edit `uv.lock`, and don't reintroduce `requirements.txt`. `requires-python` is `>=3.12` because Django 6.0 requires it; note `django-jazzmin` independently floors the project at 3.10, so neither constraint can be relaxed without dropping a dependency. `uv run <cmd>` works without activating the venv. `[tool.uv] package = false` is required — `src/` is deliberately not a package, so there is nothing to build or install.

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

App-specific management commands (full list in `README.md`): blog content/tag migrations, S3 image migrations per app (`migrate_*_images_to_s3`), thumbnail generators (`generate_*_thumbnails`), `seed_themes`, `seed_hobbies`, `generate_vapid_keys`, `setup_admin_totp`.

`/admin/` needs a TOTP code as well as a password (see "Admin two-factor" below). Bootstrap the *first* account with `python manage.py setup_admin_totp <username>`; once you can get in, enrol everyone else from the User change page (see "Admin two-factor").

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
    └── static/                project-level static (STATICFILES_DIRS)
```

Import roots are therefore `infrastructure.*` and `domains.*` — never prefixed with `src.`. `infrastructure/core/` is the Django project package only; shared helpers and third-party clients sit beside it in `infrastructure/utils/` and `infrastructure/external_services/`. There is no top-level `utils` package.

`settings.BASE_DIR` is the repo root (owns `.env`, the sqlite file, `media/`, `staticfiles/`); `settings.SRC_DIR` is `src/`. Use `SRC_DIR` for anything under `src/`.

Django app labels are unchanged by the move (the label is the last path component, e.g. `domains.apps.blog` → `blog`), so existing migrations and DB tables still apply.

Routing is centralized in `src/infrastructure/core/urls.py` — each app owns its own `urls.py` and is mounted from there. There is no REST API layer; views are server-rendered with Django templates. `TEMPLATES.DIRS` is `SRC_DIR/templates` and `APP_DIRS=True`, so both project-level and per-app template dirs are searched. Template names resolve relative to those roots, so they are unaffected by where the app package sits on disk.

### Apps and what they own
- `accounts` — auth flows, the `user_profile` model (profile images, contact), and `services.py` (TOTP device/backup-code issuing, QR rendering, setup-link signing). Django's stock `auth.User` is still the user model. `user_profile` is edited as a `StackedInline` on the User change page and is deliberately **not** registered on its own, so `admin:accounts_user_profile_*` does not reverse and it has no sidebar entry.
- `author` — public author profile (`/@sean_or_tony`), about/contact, hobbies/stack/education models.
- `home` — landing page, error handlers (`handler404`/`handler500` set in `infrastructure/core/urls.py`), `domains.home.log_handler.DatabaseLogHandler` (DB-backed logging sink for ERROR+ — see `LOGGING` in settings).
- `blog` — CKEditor 5 rich text posts, image/video uploads (size-limited via `BLOG_UPLOAD_MAX_SIZE_MB` / `BLOG_VIDEO_MAX_SIZE_MB` → drives `DATA_UPLOAD_MAX_MEMORY_SIZE`), tags + read groups normalization commands. Note `blog/images/` and `blog/media/` are *storage* key prefixes, not repo paths.
- `foodie` — meals with categories, search autocomplete, image thumbnails. Current meal slot is resolved by `domains.apps.foodie.services._current_mealtime`: for authenticated users, it picks the user's `UserMealSchedule` slot whose `time` is the latest one ≤ now (wrapping to the last slot when now precedes all of them); the `'fancy'` pseudo-slot is excluded from this resolution. No schedule / anonymous → hour-band fallback in the same function. Tests mock `domains.apps.foodie.services.datetime` to control "now".
- `spending_tracker` — accounts/transactions/categories/tags, currency-aware. Invariants: idempotency token in session, 24h edit window via `Transaction.is_editable`, `TransactionForm(data, user=...)` requires the `user` kwarg.
- `jotter`, `rhymes`, `throw_a_die`, `flip_a_coin`, `interest_calc`, `generate_invoice` — small standalone tools.
- `theme` — gated behind `IS_THEME_ENABLED` flag; injects CSS via `domains.theme.context_processors.theme_css`.
- `pwa` — service worker, manifest, web push (VAPID keys required in `.env`). `sw.js`/`manifest.json` are read off disk from `SRC_DIR/static/`.
- `domains/company/` — the marketing site's read-only DRF API, mounted at `/api/company/` from `domains/company/urls.py`; each subdomain owns its `urls.py` and is included there. `products` (work we've shipped) and `faqs` (question/answer accordion, optional `FAQCategory` sections). Both follow the same layout — `models.py`, `serializers.py`, `services/` holding the querysets and filter validation, `apis/` as thin `APIView`s that translate a `*FilterError` into a 400, and a `seed_*` management command. App labels are namespaced (`company_products`, `company_faqs`) since the directory name alone would collide.

### Cross-cutting infrastructure
- `infrastructure/core/middleware.py` — `BotScannerMiddleware` (first in chain) and `RateLimitMiddleware` (last). Per-path limits in `settings.RATE_LIMIT_CONFIG`; storage is the default `LocMemCache` so limits are per-process, not cluster-wide.
- `infrastructure/external_services/` — `recaptcha.py` (v3 verification, threshold from `RECAPTCHA_SCORE_THRESHOLD`), `email_validation.py` (IPQualityScore), and `weather/` (provider factory selected by `WEATHER_PROVIDER` / `GEOLOCATION_PROVIDER`; import the providers from `...external_services.weather`, the package root re-exports nothing).
- `infrastructure/core/context_processors.py` — exposes `RECAPTCHA_SITE_KEY` to all templates.
- CSRF: `static/js/csrf.js` (loaded from `base.html`) rewrites every rendered `csrfmiddlewaretoken` from the cookie at submit time, so service-worker-cached or long-open pages don't post a stale token; use its `csrfFetch` for JS POSTs. Failures land on `CSRF_FAILURE_VIEW` → `domains.home.views.error_handlers.csrf_failure`, which re-issues the cookie and offers a one-click retry (same-origin posts only, sensitive fields and uploads never replayed).
- `infrastructure/utils/` — `media.py` (`MediaHelper` for thumbnail generation, used across foodie/accounts), `choices.py` (`BaseChoices`, the `TextChoices` base every model enum subclasses), `admin.py` (`RichTextAdminMixin`, `install_select2_m2m`), `widgets.py` (`Select2MultipleWidget`), `email.py`, `validators.py`, `profanity.py`. The package `__init__` re-exports everything but `contains_profanity`.
- Email: **every** outgoing message goes through `infrastructure.utils.send_branded_email(subject, template, context, to, ...)`. It injects `app_domain` (templates that omit it render a blank footer link — the old hand-rolled senders all got this wrong), falls back to `strip_tags(html)` for the text part, and attaches `static/img/email-logo.png` as an inline `cid:` part. Don't hand-roll `EmailMultiAlternatives` again.
  - It sends via `RelatedEmail`, which retypes the root to `multipart/related` — `cid:` is only guaranteed to resolve there (RFC 2387), and Django 6 removed the `mixed_subtype` hook that used to do this. Use `set_type`, not `replace_header`. Attachments must be `email.message.MIMEPart`; Django 6 deprecates `MIMEBase`.
  - Templates live in `src/templates/emails/` and all extend `base_email.html`. Its palette is the admin's brown with the logo's gold; every pair is checked against WCAG AA. Change colours in `base_email.html`, then re-check the handful of literals in the sub-templates.
  - `email-logo.png` is a 120px downscale of `logo-mark-light.png` (gold/cream on transparent, so it needs a dark backing — it sits in the footer, on the deep brown). Regenerate it if the logo changes — don't attach the 1.4MB `logo.png`.
- `infrastructure/core/mixins/views.py` — shared CBV mixins.
- Admin two-factor: `IS_ADMIN_OTP_ENABLED` swaps `django.contrib.admin` in `INSTALLED_APPS` for `infrastructure.core.apps.OTPAdminConfig`, which points the default admin site at `infrastructure.core.admin.SeotoAdminSite` (a `django_otp` `OTPAdminSite`). The site class must live in a separate module from the `AppConfig` — importing `django_otp.admin` while `INSTALLED_APPS` is being read pulls in auth models and blows up with `AppRegistryNotReady`. `SeotoAdminSite` keeps `name = 'admin'` so `{% url 'admin:...' %}` still resolves. Users without a verified device are treated as non-staff, so the very first admin still has to be enrolled out of band (`setup_admin_totp`, or `addstatictoken` for emergency codes). After that, enrolment happens from the **User change page**: a "Set up 2FA" button (`templates/admin/accounts/user_change_form.html` → jazzmin's empty `extra_actions` block) opens a modal with the QR, the base32 secret and ten backup codes, served by three POST-only endpoints on `CustomUserAdmin.get_urls()`. The logic lives in `domains/accounts/services.py`; `admin_view()` only proves staff + verified OTP, so those endpoints check `auth.change_user` themselves.
  - Devices are issued `confirmed=False` and grant nothing until a code is verified, so a half-finished enrolment is inert. The button reads "Resume 2FA setup" while one is pending (re-shows it, no rotation) and "Reset 2FA" once one is confirmed (warns, then wipes **all** the user's `TOTPDevice`s and regenerates the backup codes).
  - The email leg sends a signed `TimestampSigner` link only — never the QR or the secret, since a readable mailbox must not be enough to enrol. It expires after 24h and dies when the device is confirmed (`read_setup_token` filters on `confirmed=False`); it lands on the public `/accounts/2fa/setup/<token>/` page, which is anonymous by design like password reset. Brute force on the confirm step is handled by django-otp's own device throttling — `RateLimitMiddleware` matches exact paths only and cannot cover a tokenised URL.
  - `csrf.js` is loaded from the site shell, which the admin does not extend, so `window.csrfFetch` exists in the admin only because `CustomUserAdmin.Media` pulls it in alongside `js/admin_totp.js`. `JAZZMIN_SETTINGS['custom_js']` is a single string slot and stays pointed at `admin_sidebar.js`.
- Admin skin: `jazzmin` (Bootstrap 5.3 + AdminLTE 4) — it must stay ahead of the admin app in `INSTALLED_APPS`. Branding lives in `JAZZMIN_SETTINGS`; the silver/brown palette is applied through Bootstrap CSS custom properties in `static/css/admin.css` (`custom_css`), since jazzmin 3.x dropped the AdminLTE `accent-*` / `sidebar-dark-*` classes that `JAZZMIN_UI_TWEAKS` used to drive. `templates/admin/login.html` is a copy of jazzmin's with the `otp_token` field added — re-sync it if jazzmin's login template changes.
- `src/templates/admin/base_site.html` is the sanctioned seam for changing jazzmin's chrome: jazzmin's own copy is just `{% extends 'admin/base.html' %}`, so a project-level version loses nothing and can override any block in jazzmin's 428-line `admin/base.html` without vendoring it. Ours overrides `{% block sidebar %}` only. Blocks it does **not** override must not be redefined blindly — overriding `extrastyle`/`extrahead` there would drop what jazzmin puts in them.
- Sidebar sections: `SeotoAdminSite.get_app_list` merges the flat per-app list into the `SIDEBAR_SECTIONS` tuple in `infrastructure/core/admin.py` (Site / Feature Apps / Company / Security), mirroring `domains/`, and attaches a `subgroups` key so the menu nests section → app → model. The flat `models` list and the `subgroups` entries **share dict identity on purpose** — jazzmin deep-copies the app list and stamps `url`/`icon` onto `models` only, and deepcopy preserves internal aliasing, so the nested entries inherit them. Rebuilding the subgroup dicts instead of aliasing them silently strips every nested icon and link. jazzmin keys model icons as `<app_label>.<ModelName>`, and the merged pseudo-app supplies that label, so `JAZZMIN_SETTINGS['icons']` uses `feature_apps.Post`, not `blog.Post` — **adding a new app means adding it to a section and keying its icons on the section**, otherwise it lands in an ungrouped trailing group. Unrecognised apps deliberately keep their own group rather than disappearing. `order_with_respect_to` and `navigation_expanded` are both unused: ordering and rendering come from the section tuple and our sidebar template.
- `static/js/admin_sidebar.js` (`custom_js`) opens the whole active branch. jazzmin's `main.js` only opens the nearest `li.has-treeview`, which leaves the section level shut once the menu is three levels deep. It resolves the active link itself rather than reading jazzmin's `.active` class, because `custom_js` can execute before the jQuery ready handler that sets it.
- Two jazzmin 3.0.5 quirks are worked around and will re-break if changed: `show_ui_builder` must stay `False` (the panel is auto-placed into the layout grid and roughly triples the sidebar column), and `static/css/admin.css` re-styles the `filter_horizontal` chooser for `button` elements — jazzmin only styles the `a` variant that Django used before 6.0, and AdminLTE's validation JS marks Django's empty multi-selects `is-invalid` on load.
- `infrastructure/core/pagination.py` — `DefaultAPIPagination` (DRF page-number class, sizes from `API_PAGE_SIZE`/`API_MAX_PAGE_SIZE`) and `apply_view_pagination(data, page_number, per_page)` for server-rendered views.
- Storage abstraction: when `MEDIA_STORAGE=AWS`, both `default` and `staticfiles` storages route to S3 with `AWS_S3_BUCKET_PREFIX`. Don't hardcode local-path assumptions in new image-handling code — go through `MediaHelper`. On `LOCAL`, staticfiles uses `infrastructure.core.storage.AdminSafeStaticFilesStorage` (whitenoise manifest storage plus a one-name allowlist for jazzmin's `{% static 'vendor/bootswatch' %}`, which points at a directory and so has no manifest entry). Only the S3 path lacks a manifest, so manifest bugs surface on `LOCAL` and in tests (which run with `DEBUG=False`) but not on `AWS`.

### Conventions to preserve
- Env access goes through `decouple`'s `config(...)` in `settings.py` with an explicit `cast=`; read env only in settings, then import from `django.conf.settings`.
- New apps: create under `src/domains/` (or `src/domains/apps/` for small tools), set `AppConfig.name` to the full dotted path (e.g. `domains.apps.foo`), register that path in `INSTALLED_APPS`, and mount it in `infrastructure/core/urls.py`. Place templates either in the app's `templates/<app>/` or under `src/templates/<app>/` (existing apps mix both — match the neighbors).
- When moving an app, remember migrations can hold fully-qualified references in their *bodies* (`upload_to=`, `validators=`), not just imports — both need updating.
- Errors that should surface in admin go through standard logging; the DB log handler captures `django` and `django.request` at ERROR+.
- HTTPS is forced when `DEBUG=False` (`SECURE_SSL_REDIRECT`).
- dont comment unless absolutely necessary. and if you have to, use concise one liners

## Deployment

Host is **PythonAnywhere**, deployed by `.github/workflows/deploy-pythonanywhere.yml` on push to `master` (SSH → `git pull` → `uv sync --frozen --no-dev` → `migrate` → `collectstatic` → touch the WSGI file to reload → health check).

- **`apps.seoto.org` is the Django app**; `seoto.org` is a separate marketing site. The `APP_DOMAIN` secret must be the former — it selects both the health-check target and the WSGI filename (`/var/www/apps_seoto_org_wsgi.py`). Probing `seoto.org` returns a green 200 from an app that was never deployed.
- Project dir is `~/<PA_USERNAME>.pythonanywhere.com`, the venv is `.venv` **inside** it (not `~/.virtualenvs/`), and the Web tab's Virtualenv field holds that absolute path. `workon` only sees `~/.virtualenvs`, so it needs a symlink there to keep working.
- PythonAnywhere kills sessions that emit too much output, so uv runs with `--no-progress`; `--python-preference only-system` stops uv downloading a ~33MB interpreter into a quota-limited home, and `uv cache prune --ci` keeps the wheel cache off the quota. Disk quota is the binding constraint — this dependency set is ~400MB installed, so two copies of it do not fit.
- The PA WSGI file is hand-written, lives outside the repo, and is **not** `src/infrastructure/core/wsgi.py`. It only needs to put `src/` on `sys.path` and set `DJANGO_SETTINGS_MODULE`; it must not load `.env` itself, since `settings.py` reads it via `AutoConfig(search_path=BASE_DIR)` from the repo root.
- Because `uv sync` prunes to match the lock exactly, anything hand-installed into the venv disappears on the next deploy. Undeclared packages that survived under `pip install -r` will surface as `ModuleNotFoundError` — declare them in `pyproject.toml` or remove the import.
- Prod runs on **sqlite** (`DEFAULT_DB=sqlite`), same as dev.