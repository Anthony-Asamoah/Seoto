"""
Django settings for Seoto project.
"""

import logging
from os import getenv, environ, path
from pathlib import Path

from django.contrib.messages import constants as messages

from seoto.utils import load_variables_into_environment

load_variables_into_environment()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = getenv('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = getenv('DEBUG')

# Enforce HTTPS instead of HTTP
SECURE_SSL_REDIRECT = not DEBUG

ALLOWED_HOSTS = [ip for ip in getenv('ALLOWED_HOSTS').split(",")]

# Application definition
INSTALLED_APPS = [
	# My apps
	'accounts',
	'author',
	'home',
	'foodie',
	'interest_calc',
	'rhymes',
	'throw_a_die',
	'flip_a_coin',
	'jotter',

	# Django default apps
	'django.contrib.admin',
	'django.contrib.auth',
	'django.contrib.contenttypes',
	'django.contrib.sessions',
	'django.contrib.messages',
	'django.contrib.staticfiles',
]

MIDDLEWARE = [
	'django.middleware.security.SecurityMiddleware',
	'django.contrib.sessions.middleware.SessionMiddleware',
	'django.middleware.common.CommonMiddleware',
	'django.middleware.csrf.CsrfViewMiddleware',
	'django.contrib.auth.middleware.AuthenticationMiddleware',
	'django.contrib.messages.middleware.MessageMiddleware',
	'django.middleware.clickjacking.XFrameOptionsMiddleware',
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
			],
		},
	},
]

WSGI_APPLICATION = 'seoto.wsgi.application'

# Database
DATABASES = {
	'default': {
		'ENGINE': 'django.db.backends.sqlite3',
		'NAME': BASE_DIR / 'db.sqlite3',
	}
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

# Email config
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'anthonyasamoah48@gmail.com'
EMAIL_HOST_PASSWORD = getenv('EMAIL_PASSWORD')
EMAIL_USE_TLS = True

# Accounts config
LOGIN_REDIRECT_URL = 'index'
LOGOUT_REDIRECT_URL = 'index'

# Messages Config
MESSAGE_TAGS = {
	messages.ERROR: 'danger',
}

# Sessions Config
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
