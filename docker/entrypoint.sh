#!/bin/sh
set -e

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
    python manage.py relabel_apps
    python manage.py migrate --noinput
fi

exec "$@"
