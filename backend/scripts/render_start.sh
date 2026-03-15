#!/bin/bash
set -euo pipefail

echo "=== Cerebrum AI Startup ==="
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Environment: ${ENVIRONMENT:-production}"
echo

echo "[1/3] Validating environment..."
: "${DATABASE_URL:?FATAL: DATABASE_URL not set}"
: "${SECRET_KEY:?FATAL: SECRET_KEY not set}"
: "${REDIS_URL:?FATAL: REDIS_URL not set}"
echo "OK: Environment variables validated"
echo

echo "[2/3] Verifying Redis connection..."
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

echo "[3/3] Starting Uvicorn server..."
echo "PORT=${PORT:-8000}"
echo "WEB_CONCURRENCY=${WEB_CONCURRENCY:-1}"
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --proxy-headers \
  --workers "${WEB_CONCURRENCY:-1}" \
  --access-log \
  --log-level debug
