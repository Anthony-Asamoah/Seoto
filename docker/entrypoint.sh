#!/bin/sh
set -e

# The web process migrates by default; worker/beat would only race it. RUN_MIGRATIONS=0/1 overrides.
if [ "$1" = "gunicorn" ]; then
    : "${RUN_MIGRATIONS:=1}"
fi

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
    python manage.py relabel_apps
    python manage.py migrate --noinput
fi

exec "$@"
