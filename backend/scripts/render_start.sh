#!/bin/bash
set -euo pipefail

echo "=== Cerebrum AI Startup ==="
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Environment: ${ENVIRONMENT:-production}"
echo

echo "[1/4] Validating environment..."
: "${DATABASE_URL:?FATAL: DATABASE_URL not set}"
: "${SECRET_KEY:?FATAL: SECRET_KEY not set}"
: "${REDIS_URL:?FATAL: REDIS_URL not set}"
echo "OK: Environment variables validated"
echo

echo "[2/4] Running database migrations..."
cd /app

CANDIDATES=(
  "/app/app/db/migrations/alembic.ini"
  "/app/backend/app/db/migrations/alembic.ini"
  "/app/alembic.ini"
  "/app/backend/alembic.ini"
)

ALEMBIC_INI=""
for p in "${CANDIDATES[@]}"; do
  if [[ -f "$p" ]]; then
    ALEMBIC_INI="$p"
    break
  fi
done

if [[ -z "$ALEMBIC_INI" ]]; then
  echo "FATAL: Could not find alembic.ini. Debug listing:" >&2
  ls -la /app || true
  ls -la /app/app/db/migrations 2>/dev/null || true
  ls -la /app/backend/app/db/migrations 2>/dev/null || true
  exit 2
fi

export PYTHONPATH="/app:/app/backend:${PYTHONPATH:-}"
echo "Using ALEMBIC_INI=$ALEMBIC_INI"
python -m alembic -c "$ALEMBIC_INI" upgrade head
echo "OK: Migrations completed"
echo

echo "[3/4] Verifying Redis connection..."
python3 << 'PY'
import os, sys, redis
try:
    r = redis.from_url(os.getenv('REDIS_URL'))
    r.ping()
    print("OK: Redis connection verified")
except Exception as e:
    print(f"ERROR: Redis connection failed: {e}", file=sys.stderr)
    sys.exit(1)
PY
echo

echo "[4/4] Starting Uvicorn server..."
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --proxy-headers \
  --workers "${WEB_CONCURRENCY:-1}" \
  --access-log \
  --log-level info
