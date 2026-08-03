#!/bin/bash
set -euo pipefail

# manage.py lives in src/, which is also the import root.
cd "$(dirname "$0")"

echo "Installing dependencies..."
uv sync --frozen --no-dev

# manage.py lives in src/, which is also the import root.
cd src

echo "Collecting static files..."
uv run --no-sync python manage.py collectstatic --noinput

echo "Running migrations..."
uv run --no-sync python manage.py migrate --noinput
