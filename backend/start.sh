#!/bin/bash
set -e

# Migrations are handled by the Deploy workflow Cloud Run job. Optional here so
# the container binds :$PORT quickly (Cloud Run fails revisions that don't listen).
if [ "${RUN_MIGRATIONS_ON_START:-false}" = "true" ]; then
  echo "Running Alembic migrations..."
  # Alembic requires a sync driver. Strip +asyncpg so it uses plain psycopg2.
  SYNC_DB_URL="${DATABASE_URL/+asyncpg/}"
  DATABASE_URL="$SYNC_DB_URL" alembic upgrade head
else
  echo "Skipping startup migrations (RUN_MIGRATIONS_ON_START!=true)"
fi

echo "Starting Cerebrum API..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
