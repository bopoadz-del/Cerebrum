#!/bin/bash
# Startup script for Cerebrum API

set -e

echo "========================================"
echo "Cerebrum API Startup"
echo "========================================"

echo "[1/2] Validating environment..."
: "${DATABASE_URL:?FATAL: DATABASE_URL not set}"
: "${SECRET_KEY:?FATAL: SECRET_KEY not set}"
: "${REDIS_URL:?FATAL: REDIS_URL not set}"
echo "✓ Environment variables validated"

echo "[2/2] Starting FastAPI application..."
echo "========================================"

# Start FastAPI (foreground)
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers "${WEB_CONCURRENCY:-1}"
