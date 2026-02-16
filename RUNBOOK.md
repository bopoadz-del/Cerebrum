# Cerebrum AI - Operations Runbook

This document contains operational procedures for the Cerebrum AI platform.

## Table of Contents

1. [Rollback Procedure](#rollback-procedure)
2. [Health Checks](#health-checks)
3. [Database Operations](#database-operations)
4. [Incident Response](#incident-response)

---

## Rollback Procedure

### When to Rollback

- Deployment causes service degradation
- Critical bugs discovered in production
- Database migration failures
- Performance degradation beyond acceptable thresholds

### Rollback Steps

1. **Stop the deployment pipeline**
   ```bash
   # Cancel any in-progress deployments
   render deploy cancel --service cerebrum-api
   ```

2. **Roll back API service to last successful deploy**
   ```bash
   # Via Render Dashboard
   # 1. Go to Services > cerebrum-api
   # 2. Click "Manual Deploy"
   # 3. Select previous successful deployment
   # 4. Click "Deploy"
   ```

3. **Verify health check returns 200**
   ```bash
   curl -fsS https://cerebrum.ai/health/ready
   curl -fsS https://cerebrum.ai/health/live
   ```

4. **Roll back frontend if API contract changed**
   ```bash
   # Via Render Dashboard
   # 1. Go to Services > cerebrum-frontend
   # 2. Click "Manual Deploy"
   # 3. Select compatible deployment
   # 4. Click "Deploy"
   ```

5. **If DB migration was applied, restore via PITR/export**
   ```bash
   # For Render PostgreSQL:
   # 1. Go to Dashboard > cerebrum-db
   # 2. Click "Recovery"
   # 3. Select point-in-time recovery
   # 4. Follow restore wizard
   ```

---

## Health Checks

### Endpoints

| Endpoint | Purpose | Expected Response |
|----------|---------|-------------------|
| `/health/live` | Liveness probe | `{"status": "alive"}` |
| `/health/ready` | Readiness probe | `{"status": "ready"}` |
| `/health` | Detailed health | Full system status |

### Check All Services

```bash
# API Health
curl https://cerebrum.ai/health/ready

# Database Connection
# (Included in /health/ready response)

# Redis Connection
# (Included in /health/ready response)

# Worker Status
# Check Flower dashboard: https://cerebrum.ai/flower
```

---

## Database Operations

### Manual Backup

```bash
# Create manual backup
pg_dump $DATABASE_URL | gzip > backup-$(date +%Y%m%d-%H%M%S).sql.gz
```

### Restore from Backup

```bash
# Restore from backup
gunzip -c backup-YYYYMMDD.sql.gz | psql $DATABASE_URL
```

### Migration Status

```bash
# Check current migration
alembic current

# View migration history
alembic history --verbose
```

---

## Backup Restore Drill

**Purpose**: Verify backup integrity and document exact restore procedures for disaster recovery.

**Frequency**: Run monthly or after any infrastructure changes.

### Prerequisites

- Access to S3 backup bucket
- PostgreSQL client (`psql`, `pg_dump`) installed
- Target database for restore testing (NEVER production)

### Step 1: Locate Latest Backup

```bash
# List available backups in S3
aws s3 ls s3://$S3_BACKUP_BUCKET/backups/ --recursive | tail -10

# Export latest backup file name
export LATEST_BACKUP=$(aws s3 ls s3://$S3_BACKUP_BUCKET/backups/ --recursive | sort | tail -1 | awk '{print $4}')
echo "Latest backup: $LATEST_BACKUP"
```

### Step 2: Download Backup

```bash
# Create temp directory for restore test
mkdir -p /tmp/restore-test-$(date +%Y%m%d)
cd /tmp/restore-test-$(date +%Y%m%d)

# Download backup from S3
aws s3 cp s3://$S3_BACKUP_BUCKET/$LATEST_BACKUP ./backup.sql.gz

# Verify file integrity
 gunzip -t backup.sql.gz && echo "Backup file is valid"
```

### Step 3: Prepare Target Database

```bash
# Set target database URL (restore test database, NOT production)
export RESTORE_TEST_DB_URL="postgresql://user:pass@restore-test-db:5432/restore_test"

# Drop and recreate target database
psql $RESTORE_TEST_DB_URL -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
```

### Step 4: Execute Restore

```bash
# Restore backup to target database
echo "Starting restore at $(date)"
gunzip -c backup.sql.gz | psql $RESTORE_TEST_DB_URL

# Check restore completed
if [ $? -eq 0 ]; then
    echo "✅ Restore completed successfully at $(date)"
else
    echo "❌ Restore FAILED at $(date)"
    exit 1
fi
```

### Step 5: Verify Restore Integrity

```bash
# Check critical tables have data
psql $RESTORE_TEST_DB_URL -c "
SELECT 
    'users' as table_name, COUNT(*) as row_count FROM users
UNION ALL
SELECT 'projects', COUNT(*) FROM projects
UNION ALL
SELECT 'documents', COUNT(*) FROM documents
UNION ALL
SELECT 'audit_logs', COUNT(*) FROM audit_logs;
"

# Verify schema version matches
psql $RESTORE_TEST_DB_URL -c "SELECT version_num FROM alembic_version;"
```

### Step 6: Application Connectivity Test

```bash
# Test API can connect to restored database (if applicable)
# Update API config to point to restore test DB temporarily
# Run health check
curl -fsS http://localhost:8000/health/ready
```

### Step 7: Cleanup

```bash
# Remove temp files
cd /
rm -rf /tmp/restore-test-*

# Drop test database
psql $RESTORE_TEST_DB_URL -c "DROP SCHEMA public CASCADE;"

echo "✅ Restore drill completed successfully"
```

### CI/Manual Trigger

**GitHub Actions (Manual Trigger)**:
```yaml
# .github/workflows/backup-restore-test.yml
name: Backup Restore Test
on:
  workflow_dispatch:  # Manual trigger only
  schedule:
    - cron: '0 3 1 * *'  # Monthly at 3 AM on 1st

jobs:
  restore-test:
    runs-on: ubuntu-latest
    steps:
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Run restore drill
        env:
          S3_BACKUP_BUCKET: ${{ secrets.S3_BACKUP_BUCKET }}
          RESTORE_TEST_DB_URL: ${{ secrets.RESTORE_TEST_DB_URL }}
        run: |
          # Steps 1-7 from above
          bash scripts/restore_drill.sh
```

### Expected Results

| Metric | Expected | Action if Failed |
|--------|----------|------------------|
| Backup download | Success | Check S3 permissions |
| File integrity | Valid gzip | Alert: Backup corruption |
| Restore completion | Exit 0 | Escalate to P0 incident |
| Row counts | > 0 for critical tables | Investigate data loss |
| Schema version | Matches production | Migration drift detected |

### Emergency Contacts

- **Backup failures**: devops@cerebrum.ai
- **Data integrity issues**: eng-lead@cerebrum.ai
- **Production restore**: oncall@cerebrum.ai (P0)

---

## Incident Response

### Severity Levels

- **P0 (Critical)**: Complete service outage, data loss
- **P1 (High)**: Major functionality impaired
- **P2 (Medium)**: Minor functionality impaired
- **P3 (Low)**: Cosmetic issues

### Escalation

1. **P0/P1**: Page on-call engineer immediately
2. **P2**: Create incident ticket, address within 4 hours
3. **P3**: Add to backlog for next sprint

### Communication

- **Slack**: #incidents channel
- **Status Page**: status.cerebrum.ai
- **Email**: oncall@cerebrum.ai

---

## Contact Information

- **Engineering Lead**: eng-lead@cerebrum.ai
- **DevOps**: devops@cerebrum.ai
- **On-Call**: oncall@cerebrum.ai
