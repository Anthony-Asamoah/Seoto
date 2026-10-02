#!/bin/bash
# One-off cutover: copy a sqlite DB into the compose Postgres. Usage: docker/sqlite_to_postgres.sh path/to/db.sqlite3
set -euo pipefail

SOURCE=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
cd "$(dirname "$0")/.."
WORK=$(mktemp -d)
cp "$SOURCE" "$WORK/db.sqlite3"

C() { docker compose --env-file "${ENV_FILE:-.env.prod}" "$@"; }

C up -d --wait postgres pgbouncer redis

users=$(C exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "select count(*) from auth_user" 2>/dev/null || echo 0')
if [ "$users" != "0" ]; then
    echo "Postgres already holds $users user(s); refusing to flush it." >&2
    exit 1
fi

C stop web worker beat 2>/dev/null || true

# Root only so sqlite can write its journal beside the copy in /app; the original is never touched.
echo "Exporting from the sqlite copy..."
C run --rm --no-deps --user root -e DEFAULT_DB=sqlite -e RUN_MIGRATIONS=1 \
    -v "$WORK/db.sqlite3:/app/db.sqlite3" -v "$WORK:/migrate" web sh -c '
        python manage.py remove_stale_contenttypes --include-stale-apps --noinput &&
        python manage.py dumpdata --natural-foreign --natural-primary \
            -e contenttypes -e auth.permission -e sessions -o /migrate/seoto.json'

echo "Loading into Postgres..."
C run --rm -v "$WORK:/migrate:ro" web sh -c '
    python manage.py flush --noinput &&
    python manage.py loaddata /migrate/seoto.json'

C up -d --wait
echo "Done. Dump kept at $WORK/seoto.json"
