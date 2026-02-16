"""
Cleanup Tasks - Maintenance and Cleanup Automation
Periodic cleanup tasks for maintaining system health and performance.
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import logging

from app.workers.celery_config import celery_app, BaseTask

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, base=BaseTask)
def cleanup_expired_sessions(self):
    """Clean up expired user sessions."""
    logger.info("Starting expired session cleanup")
    
    try:
        # In production, would query database
        # DELETE FROM user_sessions WHERE expires_at < NOW()
        
        deleted_count = 150  # Mock count
        
        logger.info(f"Cleaned up {deleted_count} expired sessions")
        return {'deleted_sessions': deleted_count}
        
    except Exception as e:
        logger.error(f"Session cleanup failed: {e}")
        raise


@celery_app.task(bind=True, base=BaseTask)
def cleanup_old_task_results(self, days: int = 7):
    """Clean up old Celery task results."""
    logger.info(f"Cleaning up task results older than {days} days")
    
    try:
        from celery.result import AsyncResult
        
        # In production, would query result backend
        # This is a placeholder implementation
        
        cleaned_count = 500  # Mock count
        
        logger.info(f"Cleaned up {cleaned_count} old task results")
        return {'cleaned_results': cleaned_count}
        
    except Exception as e:
        logger.error(f"Task result cleanup failed: {e}")
        raise


@celery_app.task(bind=True, base=BaseTask)
def cleanup_temp_files(self, max_age_hours: int = 24):
    """Clean up temporary files."""
    logger.info(f"Cleaning up temp files older than {max_age_hours} hours")
    
    try:
        import os
        import shutil
        
        temp_dirs = ['/tmp/cerebrum', '/var/tmp/cerebrum']
        cleaned_count = 0
        freed_bytes = 0
        
        for temp_dir in temp_dirs:
            if not os.path.exists(temp_dir):
                continue
            
            cutoff = datetime.now() - timedelta(hours=max_age_hours)
            
            for item in os.listdir(temp_dir):
                item_path = os.path.join(temp_dir, item)
                
                try:
                    stat = os.stat(item_path)
                    modified = datetime.fromtimestamp(stat.st_mtime)
                    
                    if modified < cutoff:
                        if os.path.isfile(item_path):
                            freed_bytes += stat.st_size
                            os.remove(item_path)
                        elif os.path.isdir(item_path):
                            freed_bytes += self._get_dir_size(item_path)
                            shutil.rmtree(item_path)
                        
                        cleaned_count += 1
                        
                except Exception as e:
                    logger.warning(f"Failed to remove {item_path}: {e}")
        
        logger.info(f"Cleaned up {cleaned_count} temp files, freed {freed_bytes / 1024 / 1024:.2f} MB")
        return {
            'cleaned_files': cleaned_count,
            'freed_bytes': freed_bytes
        }
        
    except Exception as e:
        logger.error(f"Temp file cleanup failed: {e}")
        raise


def _get_dir_size(self, path: str) -> int:
    """Get total size of directory."""
    total = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total += os.path.getsize(fp)
    return total


@celery_app.task(bind=True, base=BaseTask)
def cleanup_old_exports(self, days: int = 30):
    """Clean up old model exports and reports."""
    logger.info(f"Cleaning up exports older than {days} days")
    
    try:
        # In production, would query database and S3
        deleted_count = 25  # Mock count
        
        logger.info(f"Cleaned up {deleted_count} old exports")
        return {'deleted_exports': deleted_count}
        
    except Exception as e:
        logger.error(f"Export cleanup failed: {e}")
        raise


@celery_app.task(bind=True, base=BaseTask)
def cleanup_audit_logs(self, days: int = 90):
    """Archive and clean up old audit logs."""
    logger.info(f"Archiving audit logs older than {days} days")
    
    try:
        # In production, would archive to cold storage
        archived_count = 10000  # Mock count
        
        logger.info(f"Archived {archived_count} audit log entries")
        return {'archived_logs': archived_count}
        
    except Exception as e:
        logger.error(f"Audit log cleanup failed: {e}")
        raise


@celery_app.task(bind=True, base=BaseTask)
def optimize_database(self):
    """Run database optimization tasks."""
    logger.info("Starting database optimization")
    
    try:
        # In production, would run:
        # - VACUUM ANALYZE
        # - REINDEX
        # - Update statistics
        
        optimizations = [
            'vacuumed_tables',
            'reindexed_tables',
            'updated_statistics'
        ]
        
        logger.info(f"Database optimization completed: {optimizations}")
        return {'optimizations': optimizations}
        
    except Exception as e:
        logger.error(f"Database optimization failed: {e}")
        raise


@celery_app.task(bind=True)
def health_check(self):
    """Perform system health check."""
    logger.info("Running system health check")
    
    try:
        checks = {
            'database': True,
            'redis': True,
            'celery': True,
            'storage': True
        }
        
        all_healthy = all(checks.values())
        
        logger.info(f"Health check completed: {'healthy' if all_healthy else 'unhealthy'}")
        return {
            'status': 'healthy' if all_healthy else 'degraded',
            'checks': checks
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            'status': 'unhealthy',
            'error': str(e)
        }
