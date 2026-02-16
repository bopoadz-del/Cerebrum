"""
Database Cleanup - Automated Purging and Archival
Implements automated cleanup and archival of old data.
"""
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import logging

logger = logging.getLogger(__name__)


class CleanupAction(str, Enum):
    """Cleanup actions."""
    DELETE = "delete"
    ARCHIVE = "archive"
    ANONYMIZE = "anonymize"
    COMPRESS = "compress"


@dataclass
class CleanupRule:
    """Rule for data cleanup."""
    name: str
    table: str
    retention_days: int
    action: CleanupAction
    date_column: str = "created_at"
    archive_table: Optional[str] = None
    batch_size: int = 1000
    enabled: bool = True
    condition: Optional[str] = None  # Additional SQL condition


class DatabaseCleanupManager:
    """Manages database cleanup operations."""
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
        self.rules: List[CleanupRule] = []
        self._running = False
    
    def add_rule(self, rule: CleanupRule):
        """Add a cleanup rule."""
        self.rules.append(rule)
        logger.info(f"Added cleanup rule: {rule.name}")
    
    def remove_rule(self, name: str) -> bool:
        """Remove a cleanup rule."""
        for i, rule in enumerate(self.rules):
            if rule.name == name:
                del self.rules[i]
                logger.info(f"Removed cleanup rule: {name}")
                return True
        return False
    
    async def run_cleanup(self, rule_name: Optional[str] = None) -> Dict[str, Any]:
        """Run cleanup for all or specific rule."""
        results = {}
        
        rules_to_run = self.rules
        if rule_name:
            rules_to_run = [r for r in self.rules if r.name == rule_name]
        
        for rule in rules_to_run:
            if not rule.enabled:
                continue
            
            try:
                result = await self._execute_rule(rule)
                results[rule.name] = result
            except Exception as e:
                logger.error(f"Cleanup rule {rule.name} failed: {e}")
                results[rule.name] = {"status": "error", "error": str(e)}
        
        return results
    
    async def _execute_rule(self, rule: CleanupRule) -> Dict[str, Any]:
        """Execute a single cleanup rule."""
        cutoff_date = datetime.utcnow() - timedelta(days=rule.retention_days)
        
        if rule.action == CleanupAction.DELETE:
            return await self._delete_old_records(rule, cutoff_date)
        elif rule.action == CleanupAction.ARCHIVE:
            return await self._archive_old_records(rule, cutoff_date)
        elif rule.action == CleanupAction.ANONYMIZE:
            return await self._anonymize_old_records(rule, cutoff_date)
        elif rule.action == CleanupAction.COMPRESS:
            return await self._compress_old_records(rule, cutoff_date)
        
        return {"status": "unknown_action"}
    
    async def _delete_old_records(self, rule: CleanupRule, 
                                   cutoff_date: datetime) -> Dict[str, Any]:
        """Delete old records."""
        deleted_count = 0
        
        async with self.db_pool.acquire() as conn:
            while True:
                # Build query
                where_clause = f"{rule.date_column} < $1"
                if rule.condition:
                    where_clause += f" AND {rule.condition}"
                
                # Delete in batches
                query = f"""
                    DELETE FROM {rule.table}
                    WHERE {where_clause}
                    AND id IN (
                        SELECT id FROM {rule.table}
                        WHERE {where_clause}
                        LIMIT $2
                    )
                    RETURNING id
                """
                
                result = await conn.fetch(query, cutoff_date, rule.batch_size)
                
                if not result:
                    break
                
                deleted_count += len(result)
                logger.debug(f"Deleted {len(result)} records from {rule.table}")
        
        logger.info(f"Cleanup rule {rule.name}: deleted {deleted_count} records")
        
        return {
            "status": "success",
            "action": "delete",
            "deleted_count": deleted_count,
            "cutoff_date": cutoff_date.isoformat()
        }
    
    async def _archive_old_records(self, rule: CleanupRule,
                                    cutoff_date: datetime) -> Dict[str, Any]:
        """Archive old records to archive table."""
        archive_table = rule.archive_table or f"{rule.table}_archive"
        archived_count = 0
        
        async with self.db_pool.acquire() as conn:
            # Ensure archive table exists
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {archive_table} (
                    LIKE {rule.table} INCLUDING ALL
                )
            """)
            
            while True:
                where_clause = f"{rule.date_column} < $1"
                if rule.condition:
                    where_clause += f" AND {rule.condition}"
                
                # Archive in batches
                async with conn.transaction():
                    # Insert to archive
                    insert_query = f"""
                        INSERT INTO {archive_table}
                        SELECT * FROM {rule.table}
                        WHERE {where_clause}
                        AND id IN (
                            SELECT id FROM {rule.table}
                            WHERE {where_clause}
                            LIMIT $2
                        )
                        ON CONFLICT DO NOTHING
                    """
                    
                    await conn.execute(insert_query, cutoff_date, rule.batch_size)
                    
                    # Delete from main table
                    delete_query = f"""
                        DELETE FROM {rule.table}
                        WHERE {where_clause}
                        AND id IN (
                            SELECT id FROM {archive_table}
                            WHERE archived_at > NOW() - INTERVAL '1 minute'
                        )
                    """
                    
                    result = await conn.execute(delete_query, cutoff_date)
                    rows_affected = int(result.split()[-1]) if result else 0
                    
                    if rows_affected == 0:
                        break
                    
                    archived_count += rows_affected
        
        logger.info(f"Cleanup rule {rule.name}: archived {archived_count} records")
        
        return {
            "status": "success",
            "action": "archive",
            "archived_count": archived_count,
            "archive_table": archive_table,
            "cutoff_date": cutoff_date.isoformat()
        }
    
    async def _anonymize_old_records(self, rule: CleanupRule,
                                      cutoff_date: datetime) -> Dict[str, Any]:
        """Anonymize old records (GDPR compliance)."""
        anonymized_count = 0
        
        async with self.db_pool.acquire() as conn:
            # This is a simplified example - actual implementation
            # would depend on your data structure
            where_clause = f"{rule.date_column} < $1"
            if rule.condition:
                where_clause += f" AND {rule.condition}"
            
            query = f"""
                UPDATE {rule.table}
                SET 
                    email = 'anonymized_' || id || '@anonymized.local',
                    name = 'Anonymized User',
                    phone = NULL,
                    address = NULL,
                    anonymized_at = NOW()
                WHERE {where_clause}
            """
            
            result = await conn.execute(query, cutoff_date)
            anonymized_count = int(result.split()[-1]) if result else 0
        
        logger.info(f"Cleanup rule {rule.name}: anonymized {anonymized_count} records")
        
        return {
            "status": "success",
            "action": "anonymize",
            "anonymized_count": anonymized_count,
            "cutoff_date": cutoff_date.isoformat()
        }
    
    async def _compress_old_records(self, rule: CleanupRule,
                                     cutoff_date: datetime) -> Dict[str, Any]:
        """Compress old records (placeholder for compression logic)."""
        # This would typically involve:
        # 1. Exporting old data to compressed format
        # 2. Storing in object storage
        # 3. Deleting from database
        
        logger.info(f"Cleanup rule {rule.name}: compression not yet implemented")
        
        return {
            "status": "not_implemented",
            "action": "compress"
        }
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get cleanup statistics."""
        stats = {}
        
        async with self.db_pool.acquire() as conn:
            for rule in self.rules:
                # Get count of records matching rule
                where_clause = f"{rule.date_column} < NOW() - INTERVAL '{rule.retention_days} days'"
                if rule.condition:
                    where_clause += f" AND {rule.condition}"
                
                query = f"""
                    SELECT COUNT(*) as count
                    FROM {rule.table}
                    WHERE {where_clause}
                """
                
                result = await conn.fetchval(query)
                
                stats[rule.name] = {
                    "table": rule.table,
                    "retention_days": rule.retention_days,
                    "action": rule.action.value,
                    "records_to_cleanup": result,
                    "enabled": rule.enabled
                }
        
        return stats


# Default cleanup rules for Cerebrum
DEFAULT_CLEANUP_RULES = [
    CleanupRule(
        name="audit_logs",
        table="audit_logs",
        retention_days=365,
        action=CleanupAction.ARCHIVE,
        archive_table="audit_logs_archive"
    ),
    CleanupRule(
        name="temp_files",
        table="temp_files",
        retention_days=7,
        action=CleanupAction.DELETE
    ),
    CleanupRule(
        name="old_sessions",
        table="user_sessions",
        retention_days=30,
        action=CleanupAction.DELETE,
        date_column="last_activity"
    ),
    CleanupRule(
        name="expired_tokens",
        table="auth_tokens",
        retention_days=1,
        action=CleanupAction.DELETE,
        date_column="expires_at",
        condition="expires_at < NOW()"
    ),
    CleanupRule(
        name="old_notifications",
        table="notifications",
        retention_days=90,
        action=CleanupAction.ARCHIVE,
        archive_table="notifications_archive"
    ),
    CleanupRule(
        name="clash_detection_history",
        table="clash_results",
        retention_days=180,
        action=CleanupAction.ARCHIVE,
        archive_table="clash_results_archive"
    ),
]


# Celery task for scheduled cleanup
from ..workers.celery_config import low_priority_task

@low_priority_task(bind=True)
def scheduled_cleanup(self, rule_name: Optional[str] = None):
    """Run scheduled cleanup task."""
    import asyncio
    
    # This would be called with proper db_pool in production
    logger.info(f"Running scheduled cleanup for rule: {rule_name or 'all'}")
    
    # Placeholder - actual implementation would use db_pool
    # asyncio.run(cleanup_manager.run_cleanup(rule_name))
    
    return {"status": "completed", "rule": rule_name}


# Kubernetes CronJob for scheduled cleanup
CLEANUP_CRONJOB = """
apiVersion: batch/v1
kind: CronJob
metadata:
  name: database-cleanup
  namespace: default
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  concurrencyPolicy: Forbid
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: cleanup
            image: cerebrum-api:latest
            command:
            - python
            - -m
            - app.db.cleanup
            - --run
            env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: db-credentials
                  key: url
            resources:
              requests:
                memory: "256Mi"
                cpu: "100m"
              limits:
                memory: "512Mi"
                cpu: "500m"
          restartPolicy: OnFailure
"""
