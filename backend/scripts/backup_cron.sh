#!/bin/bash
# Database Backup Cron Job Script - Render Disk Storage
# Saves backups to /data/backups/ (persistent disk mounted in render.yaml)

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

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/data/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
BACKUP_FILE="backup-$(date +%Y%m%d-%H%M%S).sql.gz"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_FILE"

# Create backup directory
mkdir -p "$BACKUP_DIR"

echo "Backup directory: $BACKUP_DIR"
echo "Retention policy: $RETENTION_DAYS days"
echo "Starting backup: $BACKUP_FILE"

# Create backup
echo "Running pg_dump..."
pg_dump "$DATABASE_URL" | gzip > "$BACKUP_PATH"

# Verify backup was created
if [ ! -f "$BACKUP_PATH" ] || [ ! -s "$BACKUP_PATH" ]; then
    echo "ERROR: Backup file was not created or is empty!"
    exit 1
fi

FILESIZE=$(du -h "$BACKUP_PATH" | cut -f1)
echo "✅ Backup created: $BACKUP_PATH ($FILESIZE)"

# Cleanup old backups
echo "Cleaning up backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -name "backup-*.sql.gz" -type f -mtime +$RETENTION_DAYS -delete
echo "Cleanup complete."

# Show disk usage
echo ""
echo "Disk usage:"
df -h "$BACKUP_DIR" | tail -1

# List current backups
echo ""
echo "Current backups ($(find "$BACKUP_DIR" -name "backup-*.sql.gz" | wc -l) total):"
ls -lh "$BACKUP_DIR"/backup-*.sql.gz 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}' || echo "  No backups found"

echo ""
echo "=== Backup process complete ==="
