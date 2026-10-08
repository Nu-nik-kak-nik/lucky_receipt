#!/bin/sh
set -e

python - <<'PY'
import os, socket, sys, time
host = os.environ.get("POSTGRES_HOST", "db")
port = int(os.environ.get("POSTGRES_PORT", "5432"))
for _ in range(60):
    try:
        with socket.create_connection((host, port), timeout=1):
            sys.exit(0)
    except OSError:
        time.sleep(1)
sys.exit("Postgres is not reachable")
PY

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec "$@"
