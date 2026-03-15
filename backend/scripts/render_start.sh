#!/bin/bash
set -e

echo "=== Cerebrum AI Startup ==="
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Environment: ${ENVIRONMENT:-production}"
echo "PORT: ${PORT:-8000}"
echo

echo "[1/3] Validating environment..."
if [ -z "$DATABASE_URL" ]; then
    echo "FATAL: DATABASE_URL not set"
    exit 1
fi
if [ -z "$SECRET_KEY" ]; then
    echo "FATAL: SECRET_KEY not set"
    exit 1
fi
if [ -z "$REDIS_URL" ]; then
    echo "FATAL: REDIS_URL not set"
    exit 1
fi
echo "OK: Environment variables validated"
echo

echo "[2/3] Verifying Redis connection..."
python3 -c "
import os, sys
import redis
try:
    r = redis.from_url(os.getenv('REDIS_URL'))
    r.ping()
    print('OK: Redis connection verified')
except Exception as e:
    print(f'ERROR: Redis connection failed: {e}', file=sys.stderr)
    sys.exit(1)
"
echo

echo "[3/3] Starting Uvicorn server on port ${PORT:-8000}..."
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --proxy-headers \
  --workers "${WEB_CONCURRENCY:-1}" \
  --access-log \
  --log-level info
