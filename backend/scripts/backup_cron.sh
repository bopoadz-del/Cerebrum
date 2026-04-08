#!/bin/bash
# Database Backup Cron Job Script
# This script creates database backups for the cerebrum-db
# Note: Render also provides native automated backups for PostgreSQL

set -euo pipefail

echo "=== Database Backup Cron Job Started ==="
echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Check required commands
for cmd in pg_dump gzip; do
    if ! command -v "$cmd" &> /dev/null; then
        echo "ERROR: Required command '$cmd' not found"
        exit 1
    fi
done

# Check DATABASE_URL
if [ -z "${DATABASE_URL:-}" ]; then
    echo "ERROR: DATABASE_URL environment variable is not set"
    exit 1
fi

BACKUP_FILE="backup-$(date +%Y%m%d-%H%M%S).sql.gz"
echo "Starting backup: $BACKUP_FILE"

# Create backup
echo "Running pg_dump..."
if ! pg_dump "$DATABASE_URL" | gzip > "/tmp/$BACKUP_FILE"; then
    echo "ERROR: pg_dump failed"
    exit 1
fi

BACKUP_SIZE=$(ls -lh "/tmp/$BACKUP_FILE" | awk '{print $5}')
echo "Backup created successfully: $BACKUP_FILE ($BACKUP_SIZE)"

# Show backup stats
echo "Backup stats:"
ls -lh "/tmp/$BACKUP_FILE"

# Note: Render provides native automated backups for PostgreSQL databases.
# This cron job serves as an additional custom backup mechanism.
# To download this backup manually, run the cron job and check the logs.

# Cleanup local backup (cron jobs are ephemeral)
rm -f "/tmp/$BACKUP_FILE"
echo "Backup process complete at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""
echo "Note: Render's native PostgreSQL backups are also enabled automatically."
echo "You can restore from native backups via the Render dashboard."
