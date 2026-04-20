#!/bin/bash
set -e

echo "Running Alembic migrations..."
# Alembic requires a sync driver. Strip +asyncpg so it uses plain psycopg2.
SYNC_DB_URL="${DATABASE_URL/+asyncpg/}"
DATABASE_URL="$SYNC_DB_URL" alembic upgrade head

echo "Starting Cerebrum API..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
