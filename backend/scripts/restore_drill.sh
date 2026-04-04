#!/bin/bash
# Backup Restore Drill Script
# Tests backup integrity by restoring to a test database
# WARNING: Never run this against production database

set -euo pipefail

# Configuration
S3_BACKUP_BUCKET="${S3_BACKUP_BUCKET:-}"
RESTORE_TEST_DB_URL="${RESTORE_TEST_DB_URL:-}"
LOCK_KEY=43  # Different from render_start.sh

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Validate prerequisites
validate_prereqs() {
    log_info "Validating prerequisites..."
    
    if [ -z "$S3_BACKUP_BUCKET" ]; then
        log_error "S3_BACKUP_BUCKET environment variable not set"
        exit 1
    fi
    
    if [ -z "$RESTORE_TEST_DB_URL" ]; then
        log_error "RESTORE_TEST_DB_URL environment variable not set"
        exit 1
    fi
    
    # Check for required tools
    command -v aws >/dev/null 2>&1 || { log_error "aws CLI required but not installed"; exit 1; }
    command -v psql >/dev/null 2>&1 || { log_error "psql required but not installed"; exit 1; }
    command -v pg_dump >/dev/null 2>&1 || { log_error "pg_dump required but not installed"; exit 1; }
    
    log_info "Prerequisites validated"
}

# Step 1: Locate latest backup
locate_backup() {
    log_info "Locating latest backup in s3://$S3_BACKUP_BUCKET/backups/..."
    
    LATEST_BACKUP=$(aws s3 ls "s3://$S3_BACKUP_BUCKET/backups/" --recursive 2>/dev/null | sort | tail -1 | awk '{print $4}')
    
    if [ -z "$LATEST_BACKUP" ]; then
        log_error "No backups found in S3 bucket"
        exit 1
    fi
    
    log_info "Latest backup: $LATEST_BACKUP"
}

# Step 2: Download backup
download_backup() {
    log_info "Downloading backup..."
    
    WORKDIR="/tmp/restore-test-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$WORKDIR"
    cd "$WORKDIR"
    
    if ! aws s3 cp "s3://$S3_BACKUP_BUCKET/$LATEST_BACKUP" ./backup.sql.gz 2>/dev/null; then
        log_error "Failed to download backup from S3"
        exit 1
    fi
    
    # Verify file integrity
    if ! gzip -t backup.sql.gz 2>/dev/null; then
        log_error "Backup file is corrupted (gzip test failed)"
        exit 1
    fi
    
    log_info "Backup downloaded and verified: $(du -h backup.sql.gz | cut -f1)"
}

# Step 3: Prepare target database
prepare_database() {
    log_info "Preparing target database..."
    
    # Test connection
    if ! psql "$RESTORE_TEST_DB_URL" -c "SELECT 1" >/dev/null 2>&1; then
        log_error "Cannot connect to restore test database"
        exit 1
    fi
    
    # Drop and recreate schema
    psql "$RESTORE_TEST_DB_URL" -c "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;" >/dev/null 2>&1
    
    log_info "Target database prepared"
}

# Step 4: Execute restore
execute_restore() {
    log_info "Starting restore at $(date -Iseconds)..."
    
    START_TIME=$(date +%s)
    
    if ! gunzip -c backup.sql.gz | psql "$RESTORE_TEST_DB_URL" >/dev/null 2>&1; then
        log_error "Restore failed"
        exit 1
    fi
    
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    
    log_info "Restore completed in ${DURATION}s"
}

# Step 5: Verify integrity
verify_integrity() {
    log_info "Verifying restore integrity..."
    
    # Check critical tables
    CRITICAL_TABLES=("users" "projects" "documents" "audit_logs")
    
    for table in "${CRITICAL_TABLES[@]}"; do
        COUNT=$(psql "$RESTORE_TEST_DB_URL" -t -c "SELECT COUNT(*) FROM $table" 2>/dev/null | xargs)
        
        if [ -z "$COUNT" ] || [ "$COUNT" = "0" ]; then
            log_warn "Table '$table' has $COUNT rows"
        else
            log_info "Table '$table': $COUNT rows"
        fi
    done
    
    # Check schema version
    SCHEMA_VERSION=$(psql "$RESTORE_TEST_DB_URL" -t -c "SELECT version_num FROM alembic_version" 2>/dev/null | xargs)
    log_info "Schema version: $SCHEMA_VERSION"
}

# Step 6: Cleanup
cleanup() {
    log_info "Cleaning up..."
    
    if [ -n "${WORKDIR:-}" ] && [ -d "$WORKDIR" ]; then
        rm -rf "$WORKDIR"
        log_info "Removed temp directory: $WORKDIR"
    fi
    
    # Drop test schema
    psql "$RESTORE_TEST_DB_URL" -c "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;" >/dev/null 2>&1
}

# Main execution
main() {
    echo "========================================"
    echo "  Backup Restore Drill"
    echo "  Started: $(date -Iseconds)"
    echo "========================================"
    
    # Set trap for cleanup
    trap cleanup EXIT
    
    validate_prereqs
    locate_backup
    download_backup
    prepare_database
    execute_restore
    verify_integrity
    
    echo "========================================"
    log_info "✅ Restore drill completed successfully"
    echo "  Finished: $(date -Iseconds)"
    echo "========================================"
}

main "$@"
