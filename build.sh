#!/bin/bash
set -euo pipefail

# manage.py lives in src/, which is also the import root.
cd "$(dirname "$0")/src"

echo "Collecting static files..."
python3 manage.py collectstatic --noinput

echo "Running migrations..."
python3 manage.py migrate --noinput
