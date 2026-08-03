"""
Django settings for Seoto project.
"""

import logging
from os import path
from pathlib import Path as pathlib

from decouple import AutoConfig, Csv
from django.contrib.messages import constants as messages

# settings.py lives at <repo>/src/infrastructure/core/, so walk up to both the
# import root (src/) and the repo root (which owns .env, db, media, staticfiles).
SRC_DIR = pathlib(__file__).resolve().parent.parent.parent
BASE_DIR = SRC_DIR.parent

config = AutoConfig(search_path=BASE_DIR)

logging.basicConfig(
    level=config('LOG_LEVEL', cast=int),
    format=config('LOG_FORMAT')
)

SECRET_KEY = config('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', cast=bool)

# Enforce HTTPS instead of HTTP
SECURE_SSL_REDIRECT = not DEBUG

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', cast=Csv(post_process=tuple))

# Recoverable page (fresh token + one-click retry) instead of Django's bare 403
CSRF_FAILURE_VIEW = 'domains.home.views.error_handlers.csrf_failure'
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv(post_process=tuple))
APP_DOMAIN = config('APP_DOMAIN')

# Gates the TOTP requirement on the admin. Turn off only to recover from a lockout;
# django_otp itself stays installed either way so the devices survive the round trip.
IS_ADMIN_OTP_ENABLED = config('IS_ADMIN_OTP_ENABLED', default=True, cast=bool)

# Application definition
INSTALLED_APPS = [
    # Third-party
    # jazzmin must precede django.contrib.admin so its template overrides win.
    'jazzmin',
    'daphne',
    'channels',
    'django_ckeditor_5',
    'rest_framework',
    'corsheaders',
    'drf_spectacular',
    'django_otp',
    'django_otp.plugins.otp_totp',
    'django_otp.plugins.otp_static',
    # My apps
    'domains.company.products.apps.ProductsConfig',
    'domains.company.faqs.apps.FAQsConfig',
    'domains.accounts',
    'domains.author',
    'domains.home',
    'domains.apps.foodie.apps.FoodieConfig',
    'domains.apps.interest_calc',
    'domains.apps.rhymes',
    'domains.apps.throw_a_die',
    'domains.apps.flip_a_coin',
    'domains.apps.jotter',
    'domains.apps.blog',
    'domains.apps.spending_tracker',
    'domains.apps.generate_invoice',
    'domains.theme',
    'domains.pwa',

    # Django default apps
    'infrastructure.core.apps.OTPAdminConfig' if IS_ADMIN_OTP_ENABLED else 'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'infrastructure.core.middleware.BotScannerMiddleware',
    'django.middleware.security.SecurityMiddleware',
    # Must sit above CommonMiddleware so preflights get their headers.
    'corsheaders.middleware.CorsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # Must follow AuthenticationMiddleware; adds request.user.is_verified().
    'django_otp.middleware.OTPMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'infrastructure.core.middleware.RateLimitMiddleware',
]

ROOT_URLCONF = 'infrastructure.core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [SRC_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'domains.theme.context_processors.theme_css',
                'infrastructure.core.context_processors.recaptcha_site_key',
            ],
        },
    },
]

WSGI_APPLICATION = 'infrastructure.core.wsgi.application'
ASGI_APPLICATION = 'infrastructure.core.asgi.application'

# Channels (in-memory layer for now)
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}

# Database
DATABASES = {
    'sqlite': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    },
}

PG_DB_URL = config('PG_DB_URL', default='')
if PG_DB_URL:
    import dj_database_url
    DATABASES['postgres'] = dj_database_url.parse(PG_DB_URL, conn_max_age=600)
else:
    DATABASES['postgres'] = {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": config('PG_DB_HOST'),
        "PORT": config('PG_DB_PORT', cast=int),
        "NAME": config('PG_DB_NAME'),
        "USER": config('PG_DB_USER'),
        "PASSWORD": config('PG_DB_PASSWORD'),
    }

DATABASES['default'] = DATABASES[config('DEFAULT_DB')]

# Cache configuration (used by rate limiting middleware)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'rate-limit-cache',
    }
}

# Rate limit configuration: path -> {max_requests, window (seconds)}
RATE_LIMIT_CONFIG = {
    '/accounts/login/': {'max_requests': 5, 'window': 300},
    '/accounts/register': {'max_requests': 5, 'window': 300},
    '/accounts/password_reset/': {'max_requests': 3, 'window': 300},
    '/@sean_or_tony': {'max_requests': 3, 'window': 300},
    '/reach-out': {'max_requests': 5, 'window': 300},
    # Roomier than the other auth endpoints: a mistyped rotating code costs an attempt,
    # and django-otp throttles the device itself on top of this.
    '/admin/login/': {'max_requests': 10, 'window': 300},
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = (path.join(SRC_DIR, 'static'),)

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Media config
MEDIA_ROOT = path.join(BASE_DIR, 'media')
MEDIA_URL = 'media/'

# Storage backend: LOCAL | AWS
MEDIA_STORAGE = config('MEDIA_STORAGE', default='LOCAL')

if MEDIA_STORAGE == 'AWS':
    AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='us-east-1')
    AWS_S3_BUCKET_PREFIX = config('AWS_S3_BUCKET_PREFIX', default='')
    AWS_DEFAULT_ACL = 'private'
    AWS_S3_FILE_OVERWRITE = False
    AWS_QUERYSTRING_AUTH = True

    STORAGES = {
        'default': {
            'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage',
            'OPTIONS': {
                'location': AWS_S3_BUCKET_PREFIX,
            },
        },
        'staticfiles': {
            'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage',
            'OPTIONS': {
                'location': f'{AWS_S3_BUCKET_PREFIX}/staticfiles',
                'querystring_auth': False,
            },
        },
    }
    MEDIA_URL = f'https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{AWS_S3_BUCKET_PREFIX}/'
else:
    # Serve collected static files via WhiteNoise, so the app needs no separate
    # static file server in front of it.
    STORAGES = {
        'default': {
            'BACKEND': 'django.core.files.storage.FileSystemStorage',
        },
        'staticfiles': {
            'BACKEND': 'infrastructure.core.storage.AdminSafeStaticFilesStorage',
        },
    }

# Email config
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST')
EMAIL_PORT = config('EMAIL_PORT', cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_PASSWORD')
EMAIL_USE_TLS = config('EMAIL_USE_TLS', cast=bool)
DEFAULT_FROM_EMAIL = config('EMAIL_HOST_USER')

# Theme feature flag
IS_THEME_ENABLED = config('IS_THEME_ENABLED', default=False, cast=bool)

API_PAGE_SIZE = config('API_PAGE_SIZE', default=10, cast=int)
API_MAX_PAGE_SIZE = config('API_MAX_PAGE_SIZE', default=60, cast=int)

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.AllowAny',),
    'DEFAULT_AUTHENTICATION_CLASSES': (),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ) + (('rest_framework.renderers.BrowsableAPIRenderer',) if DEBUG else ()),
    'UNAUTHENTICATED_USER': None,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

IS_API_DOCS_ENABLED = config('IS_API_DOCS_ENABLED', default=False, cast=bool)

SPECTACULAR_SETTINGS = {
    'TITLE': 'Seoto Company API',
    'DESCRIPTION': 'Public read-only API backing the seoto.org marketing site.',
    'VERSION': '1.0.0',
    # The schema endpoint should not describe itself.
    'SERVE_INCLUDE_SCHEMA': False,
    # Only the /api/ tree is DRF; keeps the server-rendered site out of the schema.
    'SCHEMA_PATH_PREFIX': '/api',
    'SERVE_PERMISSIONS': ['rest_framework.permissions.AllowAny'],
}

# CORS — the marketing site (seoto.org) is a separate origin from apps.seoto.org.
# The API is public and read-only, so no credentials are exchanged.
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='', cast=Csv())
CORS_ALLOW_CREDENTIALS = False
CORS_URLS_REGEX = r'^/api/.*$'

# Accounts config
LOGIN_REDIRECT_URL = 'apps'
LOGOUT_REDIRECT_URL = 'apps'

# Admin two-factor (django-otp) — enrol devices with `manage.py setup_admin_totp <user>`
# and mint emergency codes with `manage.py addstatictoken <user>`.
OTP_TOTP_ISSUER = config('OTP_TOTP_ISSUER', default='Seoto')
# Leaving this False keeps the shared secret and QR code reachable in the admin, which is
# how a verified admin enrols a second device without shell access.
OTP_ADMIN_HIDE_SENSITIVE_DATA = config('OTP_ADMIN_HIDE_SENSITIVE_DATA', default=False, cast=bool)

# Admin skin (django-jazzmin)
JAZZMIN_SETTINGS = {
    'site_title': 'Seoto Administration',
    'site_header': 'Seoto',
    'site_brand': 'Seoto',
    'site_logo': 'img/logo-mark-light.png',
    'login_logo': 'img/logo.png',
    'site_logo_classes': '',
    'site_icon': 'img/logo-mark.png',
    'welcome_sign': 'Sign in to Seoto administration',
    'copyright': 'Seoto',
    'search_model': ['auth.User', 'blog.Post'],
    'user_avatar': None,
    'topmenu_links': [
        {'name': 'Site', 'url': 'apps', 'new_window': True},
        {'model': 'auth.User'},
    ],
    'show_sidebar': True,
    # `navigation_expanded` is deliberately absent: templates/admin/base_site.html
    # replaces the menu loop with a two-level one that is always collapsible.
    # Sections come from SeotoAdminSite.get_app_list, so model icon keys are
    # `<section>.<ModelName>` rather than `<app_label>.<ModelName>`.
    'icons': {
        'site': 'fas fa-globe',
        'site.user_profile': 'fas fa-id-badge',
        'site.Intro': 'fas fa-feather',
        'site.Education': 'fas fa-graduation-cap',
        'site.JobExperience': 'fas fa-briefcase',
        'site.Stack': 'fas fa-layer-group',
        'site.Hobby': 'fas fa-heart',
        'site.Message': 'fas fa-envelope',
        'site.ErrorLog': 'fas fa-triangle-exclamation',
        'site.PushSubscription': 'fas fa-bell',
        'site.Notification': 'fas fa-paper-plane',
        'site.ThemePreset': 'fas fa-palette',
        'site.UserTheme': 'fas fa-brush',
        'site.ThemeRating': 'fas fa-star',

        'feature_apps': 'fas fa-shapes',
        'feature_apps.Post': 'fas fa-newspaper',
        'feature_apps.PostTags': 'fas fa-tags',
        'feature_apps.PostReadGroup': 'fas fa-user-group',
        'feature_apps.PostComment': 'fas fa-comments',
        'feature_apps.Transaction': 'fas fa-receipt',
        'feature_apps.RecurringTransaction': 'fas fa-repeat',
        'feature_apps.RecurringTransactionOccurrence': 'fas fa-clock-rotate-left',
        'feature_apps.Account': 'fas fa-piggy-bank',
        'feature_apps.Category': 'fas fa-folder-tree',
        'feature_apps.Tag': 'fas fa-tag',
        'feature_apps.meal': 'fas fa-utensils',
        'feature_apps.MealTimeSlot': 'fas fa-clock',
        'feature_apps.UserMealSchedule': 'fas fa-calendar-days',
        'feature_apps.DailyMealSuggestion': 'fas fa-lightbulb',
        'feature_apps.userPreference': 'fas fa-sliders',
        'feature_apps.tracker': 'fas fa-list-check',
        'feature_apps.todo': 'fas fa-square-check',
        'feature_apps.Rhyme': 'fas fa-music',

        'company': 'fas fa-building',
        'company.Product': 'fas fa-cubes',
        'company.ProductTag': 'fas fa-tag',
        'company.FAQ': 'fas fa-circle-question',
        'company.FAQCategory': 'fas fa-folder-open',

        'security': 'fas fa-shield-halved',
        'security.User': 'fas fa-user',
        'security.Group': 'fas fa-users',
        'security.TOTPDevice': 'fas fa-mobile-screen',
        'security.StaticDevice': 'fas fa-key',
        'security.StaticToken': 'fas fa-hashtag',
    },
    'related_modal_active': True,
    'custom_css': 'css/admin.css',
    'custom_js': 'js/admin_sidebar.js',
    # jazzmin 3.0.5 drops the UI-builder panel into the layout grid instead of
    # positioning it off-canvas, which blows the sidebar column out to ~3x its width.
    'show_ui_builder': False,
    'changeform_format': 'horizontal_tabs',
}

# jazzmin 3.x rides on Bootstrap 5.3 + AdminLTE 4, which dropped the `accent-*`,
# `navbar-*` and `sidebar-dark-*` colour classes — the silver & brown palette is
# applied through CSS custom properties in static/css/admin.css instead.
JAZZMIN_UI_TWEAKS = {
    'no_navbar_border': True,
    'navbar_fixed': True,
    'sidebar_fixed': True,
    'sidebar_nav_child_indent': True,
    'theme': 'default',
    'default_theme_mode': 'auto',
    'button_classes': {
        'primary': 'btn-primary',
        'secondary': 'btn-outline-secondary',
        'info': 'btn-info',
        'warning': 'btn-warning',
        'danger': 'btn-danger',
        'success': 'btn-success',
    },
}

# CKEditor 5
CKEDITOR_5_CONFIGS = {
    'default': {
        'toolbar': [
            'heading', '|',
            'bold', 'italic', 'underline', 'strikethrough', '|',
            'bulletedList', 'numberedList', '|',
            'blockQuote', 'link', '|',
            'undo', 'redo',
        ],
    },
    'blog': {
        'toolbar': [
            'heading', '|',
            'bold', 'italic', 'underline', 'strikethrough', '|',
            'bulletedList', 'numberedList', '|',
            'blockQuote', 'codeBlock', '|',
            'link', 'insertImage', '|',
            'undo', 'redo',
        ],
        'image': {
            'toolbar': ['imageTextAlternative', 'imageStyle:inline', 'imageStyle:block'],
        },
        'htmlSupport': {
            'allow': [
                {'name': 'video', 'attributes': True, 'classes': True, 'styles': True},
                {'name': 'audio', 'attributes': True, 'classes': True, 'styles': True},
                {'name': 'source', 'attributes': True, 'classes': True, 'styles': True},
                {'name': 'iframe', 'attributes': True, 'classes': True, 'styles': True},
                {'name': 'div', 'attributes': True, 'classes': True, 'styles': True},
                {'name': 'a', 'attributes': True, 'classes': True, 'styles': True},
                {'name': 'i', 'attributes': True, 'classes': True, 'styles': True},
            ]
        },
    },
}
CKEDITOR_5_FILE_UPLOAD_PERMISSION = 'authenticated'

# Messages Config
MESSAGE_TAGS = {
    messages.ERROR: 'danger',
}

# Sessions Config
SESSION_EXPIRE_AT_BROWSER_CLOSE = config('SESSION_EXPIRE_AT_BROWSER_CLOSE', cast=bool)

# PWA Configuration
VAPID_PUBLIC_KEY = config('VAPID_PUBLIC_KEY')
VAPID_PRIVATE_KEY = config('VAPID_PRIVATE_KEY')
VAPID_ADMIN_EMAIL = config('VAPID_ADMIN_EMAIL')

# How long the service worker serves configured pages (see sw.js CACHEABLE_ROUTES)
# straight from cache before re-fetching from the network.
CLIENT_CACHE_TTL_SECONDS = config('CLIENT_CACHE_TTL_SECONDS', default=300, cast=int)

# Recurring transactions: expected daily run time for `process_recurring_transactions`,
# configured as a PythonAnywhere Scheduled Task (which takes an hour:minute, not a real
# cron expression) — used only to log a warning if the task drifts from this time.
RECURRING_TRANSACTIONS_CRON = config('RECURRING_TRANSACTIONS_CRON', default='0 19 * * *')

# reCAPTCHA v3 Configuration
RECAPTCHA_VERIFY_URL = config('RECAPTCHA_VERIFY_URL', default='')
RECAPTCHA_SITE_KEY = config('RECAPTCHA_SITE_KEY', default='')
RECAPTCHA_SECRET_KEY = config('RECAPTCHA_SECRET_KEY', default='')
RECAPTCHA_SCORE_THRESHOLD = config('RECAPTCHA_SCORE_THRESHOLD', default=0.5, cast=float)

# Only enforce reCAPTCHA when fully configured (keys present). Lets local/dev
# skip verification by leaving the keys unset/None.
RECAPTCHA_ENABLED = all([RECAPTCHA_SITE_KEY, RECAPTCHA_SECRET_KEY, RECAPTCHA_VERIFY_URL])

# IP Quality Score API Key
IP_QUALITY_SCORE_API_KEY = config('IP_QUALITY_SCORE_API_KEY', default="None")

# Weather widget — provider name selects an implementation via the factory in
# src/infrastructure/external_services/weather/factory.py, so providers can be swapped
# without touching call sites. Both defaults are free and require no API key.
WEATHER_PROVIDER = config('WEATHER_PROVIDER', default='open_meteo')
GEOLOCATION_PROVIDER = config('GEOLOCATION_PROVIDER', default='ip_api')

# Calendly — consultation booking link shown on the reach-out page after the
# qualifying form is submitted. Swap the default for your real scheduling URL.
CALENDLY_URL = config('CALENDLY_URL', default='https://calendly.com/anthony-asamoah/30min')

# Blog media upload limits (MB)
BLOG_UPLOAD_MAX_SIZE_MB = config('BLOG_UPLOAD_MAX_SIZE_MB', default=10, cast=int)

# Structured logging — write ERROR+ to the database via domains.home.log_handler
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'db': {
            'level': 'ERROR',
            'class': 'domains.home.log_handler.DatabaseLogHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['db'],
            'level': 'ERROR',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['db'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}
BLOG_VIDEO_MAX_SIZE_MB = config('BLOG_VIDEO_MAX_SIZE_MB', default=60, cast=int)
DATA_UPLOAD_MAX_MEMORY_SIZE = BLOG_VIDEO_MAX_SIZE_MB * 1024 * 1024
