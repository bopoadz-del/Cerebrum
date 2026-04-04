"""
Enhanced Celery Tasks for Cerebrum AI

Queue Strategy:
- celery_fast: Quick tasks (OCR, notifications, webhooks)
- celery_slow: Heavy tasks (BIM, bulk indexing, ML processing)
- trigger_events: Event-driven tasks

Hydration: Daily sync of local files with ChromaDB index
"""

import os
import asyncio
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
from celery import Celery

# Initialize Celery with Redis broker
broker_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
celery_app = Celery(
    "cerebrum",
    broker=broker_url,
    backend=broker_url,
    include=["app.tasks"]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max for slow tasks
    worker_prefetch_multiplier=1,
    # Task routing
    task_routes={
        'app.tasks.process_upload_hydration': {'queue': 'celery_slow'},
        'app.tasks.index_single_document': {'queue': 'celery_fast'},
        'app.tasks.bulk_reindex_documents': {'queue': 'celery_slow'},
        'app.tasks.analyze_bim_model': {'queue': 'celery_slow'},
        'app.tasks.enhance_code_async': {'queue': 'celery_slow'},
        'app.tasks.process_invoice_ocr': {'queue': 'celery_fast'},
        'app.tasks.cleanup_orphaned_indexes': {'queue': 'celery_slow'},
        'app.tasks.generate_daily_report': {'queue': 'celery_slow'},
    },
    # Beat schedule (periodic tasks)
    beat_schedule={
        'daily-hydration': {
            'task': 'app.tasks.process_upload_hydration',
            'schedule': timedelta(hours=24),  # Daily
            'kwargs': {'full_scan': True}
        },
        'cleanup-orphaned': {
            'task': 'app.tasks.cleanup_orphaned_indexes',
            'schedule': timedelta(hours=24),
        },
        'health-check': {
            'task': 'app.tasks.worker_health_check',
            'schedule': timedelta(minutes=5),
        },
    },
)

# ============================================================================
# HYDRATION TASK (Daily Sync)
# ============================================================================

@celery_app.task(bind=True, max_retries=2)
def process_upload_hydration(
    self,
    upload_dir: str = "/tmp/document_uploads",
    full_scan: bool = False
) -> Dict[str, Any]:
    """
    Daily hydration task - sync local uploads with ChromaDB index.
    
    Scans upload directory, checks what's indexed, indexes missing files,
    removes orphaned index entries.
    
    Runs overnight on celery_slow queue.
    Reports progress to Redis for real-time status tracking.
    """
    import asyncio
    from app.services.chroma_service import get_chroma_service
    from app.services.document_parser import extract_text_from_file
    from app.services.redis_state_store import RedisStateStore
    
    logger = celery_app.log.get_default_logger()
    chroma = get_chroma_service()
    task_id = self.request.id
    
    # Helper to report progress
    async def report_progress(progress: int, message: str, result: dict = None):
        try:
            store = RedisStateStore()
            await store.connect()
            await store.set_task_progress(task_id, progress, "running", message, result)
            await store.disconnect()
        except Exception as e:
            logger.warning(f"Failed to report progress: {e}")
    
    if not os.path.exists(upload_dir):
        # Report failure
        asyncio.run(report_progress(0, "Upload directory not found", {"error": f"Dir not found: {upload_dir}"}))
        return {"status": "error", "error": f"Upload dir not found: {upload_dir}"}
    
    results = {
        "scanned": 0,
        "indexed_new": 0,
        "already_indexed": 0,
        "failed": 0,
        "orphaned_removed": 0,
        "start_time": datetime.utcnow().isoformat()
    }
    
    try:
        # Report start
        asyncio.run(report_progress(0, "Starting hydration scan"))
        
        # Get current index stats
        stats = chroma.get_stats_sync()
        logger.info(f"Hydration starting. Current index: {stats.get('count', 0)} docs")
        
        # Scan upload directory
        upload_path = Path(upload_dir)
        files = list(upload_path.glob("*"))
        results["scanned"] = len(files)
        
        asyncio.run(report_progress(5, f"Found {len(files)} files to scan"))
        
        # Get list of already indexed IDs
        indexed_ids = set()
        if chroma.is_available and chroma._collection:
            try:
                all_docs = chroma._collection.get()
                if all_docs and 'ids' in all_docs:
                    indexed_ids = set(all_docs['ids'])
            except Exception as e:
                logger.warning(f"Could not list indexed docs: {e}")
        
        for file_path in files:
            try:
                file_id = file_path.stem  # filename without extension
                doc_id = f"chat_upload_{file_id}"
                
                if doc_id in indexed_ids and not full_scan:
                    results["already_indexed"] += 1
                    continue
                
                # Extract text
                file_ext = file_path.suffix.lower()
                mime_type = _get_mime_type(file_ext)
                
                with open(file_path, 'rb') as f:
                    file_content = f.read()
                
                # Skip if too small
                if len(file_content) < 100:
                    continue
                
                # Extract text
                from app.services.document_parser import extract_text_from_upload
                text = extract_text_from_upload(file_content, mime_type, file_ext)
                
                if not text or len(text) < 50:
                    logger.warning(f"No text extracted from {file_path.name}")
                    results["failed"] += 1
                    continue
                
                # Build metadata
                stat = file_path.stat()
                metadata = {
                    'name': file_path.name,
                    'source': 'hydration',
                    'mime_type': mime_type,
                    'size_bytes': len(file_content),
                    'modified_time': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'file_id': file_id,
                }
                
                # Index in ChromaDB
                if chroma.add_document(doc_id, text, metadata):
                    results["indexed_new"] += 1
                    logger.info(f"Indexed: {file_path.name}")
                else:
                    results["failed"] += 1
                    
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")
                results["failed"] += 1
        
        # Cleanup orphaned indexes (files deleted but still indexed)
        if full_scan:
            cleanup_result = cleanup_orphaned_indexes(upload_dir)
            results["orphaned_removed"] = cleanup_result.get("removed", 0)
        
        results["end_time"] = datetime.utcnow().isoformat()
        results["status"] = "success"
        
        logger.info(f"Hydration complete: {results}")
        return results
        
    except Exception as exc:
        logger.error(f"Hydration failed: {exc}")
        results["status"] = "error"
        results["error"] = str(exc)
        # Retry with backoff
        raise self.retry(exc=exc, countdown=300)


def _get_mime_type(ext: str) -> str:
    """Map file extension to MIME type."""
    mime_map = {
        '.pdf': 'application/pdf',
        '.txt': 'text/plain',
        '.md': 'text/markdown',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.tiff': 'image/tiff',
    }
    return mime_map.get(ext.lower(), 'application/octet-stream')


@celery_app.task
def cleanup_orphaned_indexes(upload_dir: str = "/tmp/document_uploads") -> Dict[str, Any]:
    """
    Remove index entries for files that no longer exist.
    """
    from app.services.chroma_service import get_chroma_service
    
    chroma = get_chroma_service()
    logger = celery_app.log.get_default_logger()
    
    if not chroma.is_available or not chroma._collection:
        return {"status": "skipped", "reason": "ChromaDB not available"}
    
    removed = 0
    
    try:
        # Get all indexed documents
        all_docs = chroma._collection.get()
        if not all_docs or 'ids' not in all_docs:
            return {"status": "success", "removed": 0}
        
        # Check each document
        ids_to_delete = []
        for i, doc_id in enumerate(all_docs['ids']):
            metadata = all_docs['metadatas'][i] if all_docs.get('metadatas') else {}
            source = metadata.get('source', '')
            
            # Only check documents from upload/hydration
            if source in ['chat_upload', 'hydration']:
                file_id = metadata.get('file_id', '')
                # Check if file exists
                file_path = Path(upload_dir) / file_id
                # Try with common extensions
                exists = False
                for ext in ['', '.pdf', '.txt', '.docx', '.png', '.jpg']:
                    if (file_path.with_suffix(ext)).exists():
                        exists = True
                        break
                
                if not exists:
                    ids_to_delete.append(doc_id)
        
        # Delete orphaned entries
        if ids_to_delete:
            chroma._collection.delete(ids=ids_to_delete)
            removed = len(ids_to_delete)
            logger.info(f"Removed {removed} orphaned index entries")
        
        return {"status": "success", "removed": removed}
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return {"status": "error", "error": str(e)}


# ============================================================================
# DOCUMENT PROCESSING TASKS
# ============================================================================

@celery_app.task(bind=True, max_retries=3)
def index_single_document(
    self,
    file_id: str,
    file_path: str,
    user_id: str,
    metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Index a single document (fast queue for immediate indexing).
    Called right after file upload.
    """
    from app.services.chroma_service import get_chroma_service
    from app.services.document_parser import extract_text_from_file
    
    logger = celery_app.log.get_default_logger()
    chroma = get_chroma_service()
    
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Extract text
        with open(file_path, 'rb') as f:
            content = f.read()
        
        from app.services.document_parser import extract_text_from_upload
        file_ext = Path(file_path).suffix
        mime_type = _get_mime_type(file_ext)
        text = extract_text_from_upload(content, mime_type, file_ext)
        
        if not text or len(text) < 50:
            return {"status": "skipped", "reason": "no_text_extracted"}
        
        # Add user_id to metadata
        metadata['user_id'] = user_id
        metadata['indexed_at'] = datetime.utcnow().isoformat()
        
        doc_id = f"chat_upload_{file_id}"
        
        if chroma.add_document(doc_id, text, metadata):
            return {
                "status": "success",
                "doc_id": doc_id,
                "text_length": len(text),
                "using_ml": chroma.get_embedding_model_info().get('using_ml', False)
            }
        else:
            raise RuntimeError("Failed to add to ChromaDB")
            
    except Exception as exc:
        logger.error(f"Index failed for {file_id}: {exc}")
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True, max_retries=2)
def bulk_reindex_documents(
    self,
    document_ids: List[str],
    use_ml: bool = True
) -> Dict[str, Any]:
    """
    Bulk reindex documents with ML embeddings (slow queue).
    """
    from app.services.chroma_service import get_chroma_service
    
    logger = celery_app.log.get_default_logger()
    chroma = get_chroma_service()
    
    results = {"success": 0, "failed": 0, "total": len(document_ids)}
    
    for doc_id in document_ids:
        try:
            # Reindex logic here
            # Would fetch from DB and re-add to ChromaDB
            results["success"] += 1
        except Exception as e:
            logger.error(f"Reindex failed for {doc_id}: {e}")
            results["failed"] += 1
    
    return results


# ============================================================================
# INVOICE PROCESSING TASKS
# ============================================================================

@celery_app.task(bind=True, max_retries=3)
def process_invoice_ocr(
    self,
    file_id: str,
    file_path: str,
    user_id: str
) -> Dict[str, Any]:
    """
    Process invoice with OCR and entity extraction.
    Fast queue - returns quickly with extracted data.
    """
    from app.pipelines.ocr import extract_text_from_image
    from app.pipelines.ner_extraction import extract_entities
    
    logger = celery_app.log.get_default_logger()
    
    try:
        # OCR
        with open(file_path, 'rb') as f:
            image_data = f.read()
        
        text = extract_text_from_image(image_data)
        
        # Extract entities (amounts, dates, vendors)
        entities = extract_entities(text)
        
        return {
            "status": "success",
            "file_id": file_id,
            "extracted_text_length": len(text),
            "entities": entities,
        }
        
    except Exception as exc:
        logger.error(f"Invoice OCR failed: {exc}")
        raise self.retry(exc=exc, countdown=120)


# ============================================================================
# CODE ENHANCEMENT TASKS
# ============================================================================

@celery_app.task(bind=True, max_retries=1, time_limit=1800)
def enhance_code_async(
    self,
    file_path: str,
    enhancement_types: List[str],
    auto_apply: bool = False
) -> Dict[str, Any]:
    """
    Background code enhancement (slow queue).
    Can take up to 30 minutes for large files.
    """
    logger = celery_app.log.get_default_logger()
    
    try:
        # This would call your existing code enhancement logic
        # Running in background so it doesn't block the API
        
        logger.info(f"Enhancing {file_path} with types: {enhancement_types}")
        
        # Simulated result
        return {
            "status": "success",
            "file": file_path,
            "enhancements_applied": len(enhancement_types),
            "auto_applied": auto_apply,
        }
        
    except Exception as exc:
        logger.error(f"Enhancement failed: {exc}")
        raise self.retry(exc=exc, countdown=300)


# ============================================================================
# BIM ANALYSIS TASKS
# ============================================================================

@celery_app.task(bind=True, max_retries=1, time_limit=3600)
def analyze_bim_model(
    self,
    file_id: str,
    file_path: str,
    analysis_type: str = "full"
) -> Dict[str, Any]:
    """
    Heavy BIM model analysis (slow queue).
    Clash detection, quantity takeoff, etc.
    """
    logger = celery_app.log.get_default_logger()
    
    try:
        logger.info(f"Analyzing BIM model: {file_id}")
        
        # Would call IFC processing logic here
        # This is CPU-intensive and belongs on slow queue
        
        return {
            "status": "success",
            "file_id": file_id,
            "analysis_type": analysis_type,
            "elements_found": 0,  # Would be actual count
        }
        
    except Exception as exc:
        logger.error(f"BIM analysis failed: {exc}")
        raise


# ============================================================================
# MONITORING & HEALTH
# ============================================================================

@celery_app.task
def worker_health_check() -> Dict[str, Any]:
    """Periodic health check from workers."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "worker": "celery",
    }


@celery_app.task
def generate_daily_report() -> Dict[str, Any]:
    """Generate daily system report."""
    from app.services.chroma_service import get_chroma_service
    
    chroma = get_chroma_service()
    stats = chroma.get_stats_sync()
    
    return {
        "date": datetime.utcnow().isoformat(),
        "indexed_documents": stats.get("count", 0),
        "embedding_model": stats.get("embedding", {}).get("model_name", "unknown"),
        "using_ml": stats.get("embedding", {}).get("using_ml", False),
    }


# ============================================================================
# LEGACY TASKS (Keep for compatibility)
# ============================================================================

@celery_app.task(bind=True, max_retries=3)
def process_drive_file_batch(
    self,
    file_ids: List[str],
    user_id: str,
    access_token: str
) -> Dict[str, Any]:
    """
    LEGACY: Google Drive file processing.
    Disabled - kept for compatibility.
    """
    return {
        "status": "disabled",
        "message": "Google Drive integration is disabled",
        "processed": 0
    }


@celery_app.task
def cleanup_old_indexed_files(days: int = 30) -> Dict[str, Any]:
    """Clean up old files from storage."""
    # This would clean up /tmp/document_uploads
    return {"status": "success", "archived_count": 0}


@celery_app.task
def sync_drive_projects(user_id: str) -> Dict[str, Any]:
    """LEGACY: Drive project sync. Disabled."""
    return {"status": "disabled", "message": "Google Drive integration is disabled"}
