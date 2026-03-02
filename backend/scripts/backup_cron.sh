#!/bin/sh
# Database Backup Cron Job Script
# This script is used by the db-backup cronjob in Render

set -euo pipefail

BACKUP_FILE="backup-$(date +%Y%m%d-%H%M%S).sql.gz"
echo "Starting backup: $BACKUP_FILE"

# Create backup
pg_dump "$DATABASE_URL" | gzip > "/tmp/$BACKUP_FILE"
echo "Backup created: $(ls -lh /tmp/$BACKUP_FILE)"

# F15: Upload to S3 with encryption if configured
if [ -n "${AWS_ACCESS_KEY_ID:-}" ] && [ -n "${AWS_SECRET_ACCESS_KEY:-}" ]; then
    pip install awscli --quiet
    
    # Upload with server-side encryption (AES256) and IA storage class
    aws s3 cp "/tmp/$BACKUP_FILE" "s3://$S3_BACKUP_BUCKET/backups/$BACKUP_FILE" \
        --storage-class STANDARD_IA \
        --sse AES256
    
    echo "Backup uploaded to S3 (encrypted): s3://$S3_BACKUP_BUCKET/backups/$BACKUP_FILE"
    
    # F14: Cleanup old backups (retention policy)
    RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
    echo "Cleaning up backups older than $RETENTION_DAYS days..."
    aws s3 ls "s3://$S3_BACKUP_BUCKET/backups/" | awk '{print $4}' | while read -r OLD_BACKUP; do
        BACKUP_DATE=$(echo "$OLD_BACKUP" | grep -oE "backup-[0-9]{8}" | sed 's/backup-//' || true)
        if [ -n "$BACKUP_DATE" ]; then
            # Calculate days old (portable POSIX shell approach)
            BACKUP_EPOCH=$(date -d "${BACKUP_DATE:0:4}-${BACKUP_DATE:4:2}-${BACKUP_DATE:6:2}" +%s 2>/dev/null || echo "0")
            NOW_EPOCH=$(date +%s)
            if [ "$BACKUP_EPOCH" -gt 0 ]; then
                DAYS_OLD=$(( ( NOW_EPOCH - BACKUP_EPOCH ) / 86400 ))
                if [ "$DAYS_OLD" -gt "$RETENTION_DAYS" ]; then
                    echo "Deleting old backup: $OLD_BACKUP ($DAYS_OLD days old)"
                    aws s3 rm "s3://$S3_BACKUP_BUCKET/backups/$OLD_BACKUP" || true
                fi
            fi
        fi
    done
else
    echo "WARNING: AWS credentials not configured. Backup saved locally only."
    echo "To enable S3 backups, set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY"
fi

# Cleanup local backup
rm -f "/tmp/$BACKUP_FILE"
echo "Backup process complete"
