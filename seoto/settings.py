"""
Django settings for Seoto project.
"""

import logging
from os import path
from pathlib import Path as pathlib

from decouple import AutoConfig, Csv
from django.contrib.messages import constants as messages

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = pathlib(__file__).resolve().parent.parent

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
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv(post_process=tuple))
APP_DOMAIN = config('APP_DOMAIN')

# Application definition
INSTALLED_APPS = [
    # Third-party
    'daphne',
    'channels',
    'django_ckeditor_5',
    # My apps
    'accounts',
    'author',
    'home',
    'foodie.apps.FoodieConfig',
    'interest_calc',
    'rhymes',
    'throw_a_die',
    'flip_a_coin',
    'jotter',
    'blog',
    'spending_tracker',
    'generate_invoice',
    'theme',
    'pwa',

    # Django default apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'seoto.middleware.BotScannerMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'seoto.middleware.RateLimitMiddleware',
]

ROOT_URLCONF = 'seoto.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'theme.context_processors.theme_css',
                'seoto.context_processors.recaptcha_site_key',
            ],
        },
    },
]

WSGI_APPLICATION = 'seoto.wsgi.application'
ASGI_APPLICATION = 'seoto.asgi.application'

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
STATICFILES_DIRS = (path.join(BASE_DIR, 'seoto/static'),)

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
            },
        },
    }
    MEDIA_URL = f'https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{AWS_S3_BUCKET_PREFIX}/'
else:
    # Serve collected static files via WhiteNoise (required on Vercel, where the
    # runtime filesystem is read-only and there is no separate static server).
    STORAGES = {
        'default': {
            'BACKEND': 'django.core.files.storage.FileSystemStorage',
        },
        'staticfiles': {
            'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
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

# Accounts config
LOGIN_REDIRECT_URL = 'apps'
LOGOUT_REDIRECT_URL = 'apps'

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

# Calendly — consultation booking link shown on the reach-out page after the
# qualifying form is submitted. Swap the default for your real scheduling URL.
CALENDLY_URL = config('CALENDLY_URL', default='https://calendly.com/anthony-asamoah/30min')

# Blog media upload limits (MB)
BLOG_UPLOAD_MAX_SIZE_MB = config('BLOG_UPLOAD_MAX_SIZE_MB', default=10, cast=int)

# Structured logging — write ERROR+ to the database via home.log_handler
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'db': {
            'level': 'ERROR',
            'class': 'home.log_handler.DatabaseLogHandler',
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
