#!/bin/bash
# PostgreSQL Backup Script with version compatibility
# Handles server/client version mismatch using Docker

set -e

# Configuration - modify these for your environment
DB_HOST="${DB_HOST:-your-db-host.render.com}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-your_database}"
DB_USER="${DB_USER:-your_user}"
DB_PASSWORD="${DB_PASSWORD:-your_password}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"

# PostgreSQL server version (match your server)
PG_VERSION="${PG_VERSION:-18}"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Generate timestamp
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_FILE="backup-${TIMESTAMP}.sql.gz"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_FILE"

echo "================================"
echo "Database Backup"
echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Server: $DB_HOST:$DB_PORT"
echo "Database: $DB_NAME"
echo "Backup File: $BACKUP_FILE"
echo "================================"

# Run pg_dump using Docker with matching PostgreSQL version
echo "Running pg_dump using PostgreSQL $PG_VERSION..."

# Use docker to run pg_dump with correct version
docker run --rm \
    -e PGPASSWORD="$DB_PASSWORD" \
    postgres:$PG_VERSION-bookworm \
    pg_dump \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --verbose \
        --no-owner \
        --no-acl \
    | gzip > "$BACKUP_PATH"

# Check if backup was successful
if [ -f "$BACKUP_PATH" ] && [ -s "$BACKUP_PATH" ]; then
    FILESIZE=$(du -h "$BACKUP_PATH" | cut -f1)
    echo ""
    echo "✅ Backup completed successfully!"
    echo "   File: $BACKUP_PATH"
    echo "   Size: $FILESIZE"
else
    echo "❌ Backup failed!"
    rm -f "$BACKUP_PATH"
    exit 1
fi

# Clean up old backups
echo ""
echo "Cleaning up backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -name "backup-*.sql.gz" -type f -mtime +$RETENTION_DAYS -delete
echo "Cleanup complete."

echo ""
echo "Current backups:"
ls -lh "$BACKUP_DIR"/backup-*.sql.gz 2>/dev/null || echo "No backups found"
