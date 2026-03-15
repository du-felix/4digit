#!/bin/sh
set -e

# Wait for MySQL to accept connections before running migrations.
# Retries until Django can open a cursor (i.e. the DB is up and the schema exists).
echo "Waiting for database..."
until python - <<'EOF' 2>/dev/null
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fourdigit.settings')
django.setup()
from django.db import connections
connections['default'].cursor()
EOF
do
  echo "  Database not ready – retrying in 2 s..."
  sleep 2
done
echo "Database ready."

echo "Running migrations..."
python manage.py migrate --noinput

exec "$@"
