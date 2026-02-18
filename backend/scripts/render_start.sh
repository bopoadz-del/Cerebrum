#!/bin/bash
# Cerebrum AI Production Startup Script (Render)
#
# Notes:
# - Database migrations are run at startup.
# - Migration concurrency is protected by a Postgres advisory lock
#   implemented inside Alembic env.py (same DB connection as migrations).

set -euo pipefail

echo "=== Cerebrum AI Startup ==="
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Environment: ${ENVIRONMENT:-production}"
echo

# =============================================================================
# Validate Critical Environment Variables
# =============================================================================

echo "[1/4] Validating environment..."
: "${DATABASE_URL:?FATAL: DATABASE_URL not set}"
: "${SECRET_KEY:?FATAL: SECRET_KEY not set}"
: "${REDIS_URL:?FATAL: REDIS_URL not set}"
echo "OK: Environment variables validated"
echo

# =============================================================================
# Run DB Migrations (protected by Alembic advisory lock)
# =============================================================================

echo "[2/4] Running database migrations..."
cd /app
alembic -c alembic.ini upgrade head
echo "OK: Migrations completed"
echo

# =============================================================================
# Verify Redis Connection
# =============================================================================

echo "[3/4] Verifying Redis connection..."
python3 << 'PYTHON_EOF'
import os
import sys
import redis

try:
    r = redis.from_url(os.getenv('REDIS_URL'))
    r.ping()
    print("OK: Redis connection verified")
except Exception as e:
    print(f"ERROR: Redis connection failed: {e}", file=sys.stderr)
    sys.exit(1)
PYTHON_EOF
echo

# =============================================================================
# Start Application
# =============================================================================

echo "[4/4] Starting Uvicorn server..."
echo "Workers: ${WEB_CONCURRENCY:-1}"
echo "Port: ${PORT:-8000}"
echo

exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --proxy-headers \
    --workers "${WEB_CONCURRENCY:-1}" \
    --access-log \
    --log-level info
