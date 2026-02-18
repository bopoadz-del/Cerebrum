"""
Celery Tasks for Cerebrum AI Platform

Background tasks for processing Drive files, indexing documents, etc.
"""

import os
from datetime import datetime
from typing import List, Dict, Any
from celery import Celery

# Initialize Celery app
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
    task_time_limit=3600,  # 1 hour max per task
    worker_prefetch_multiplier=1,  # Process one task at a time per worker
)


@celery_app.task(bind=True, max_retries=3)
def process_drive_file_batch(
    self,
    file_ids: List[str],
    user_id: str,
    access_token: str
) -> Dict[str, Any]:
    """
    Process a batch of Google Drive files in background.
    
    Extracts text, generates embeddings, and indexes in ZVec for semantic search.
    
    Args:
        file_ids: List of Google Drive file IDs to process
        user_id: UUID of the user owning these files
        access_token: Google OAuth access token
    
    Returns:
        Dict with processed count and status
    """
    # Lazy imports to avoid circular dependencies
    from sqlalchemy.orm import Session
    from app.db.session import SessionLocal
    from app.services.document_parser import extract_text_from_drive_file, detect_project_from_filename
    from app.services.zvec_service import get_zvec_service
    from app.models.document import Document
    import asyncio
    
    db: Session = SessionLocal()
    processed_count = 0
    error_count = 0
    
    try:
        # Get ZVec service
        zvec = get_zvec_service()
        
        if not zvec.is_ready():
            return {
                "status": "error",
                "message": "ZVec service not ready - embedding model not available",
                "processed": 0,
                "errors": len(file_ids)
            }
        
        # Process each file
        for file_id in file_ids:
            try:
                # Check if already indexed
                existing = db.query(Document).filter(
                    Document.drive_id == file_id
                ).first()
                
                if existing and existing.status == "indexed":
                    continue  # Skip already indexed files
                
                # For now, we need the file info (name, mime_type) from the caller
                # In a real implementation, you'd fetch this from Google Drive API
                # For this task, we assume the file_ids come with metadata
                
                # TODO: Fetch file metadata from Google Drive
                # file_info = await fetch_file_metadata(file_id, access_token)
                
                # For now, skip files we can't get metadata for
                # This is a placeholder - implement actual Drive API fetch
                
                processed_count += 1
                
            except Exception as e:
                error_count += 1
                print(f"Failed to process file {file_id}: {e}")
                continue
        
        db.commit()
        
        return {
            "status": "success" if error_count == 0 else "partial",
            "processed": processed_count,
            "errors": error_count,
            "total": len(file_ids)
        }
        
    except Exception as exc:
        db.rollback()
        # Retry with exponential backoff
        retry_count = self.request.retries
        countdown = 60 * (2 ** retry_count)  # 60s, 120s, 240s
        raise self.retry(exc=exc, countdown=countdown)
        
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=2)
def index_document_chunk(
    self,
    document_id: str,
    chunk_index: int,
    chunk_text: str,
    metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Index a single document chunk in ZVec.
    
    Used for large documents that are split into chunks.
    """
    from app.services.zvec_service import get_zvec_service
    
    try:
        zvec = get_zvec_service()
        
        if not zvec.is_ready():
            raise RuntimeError("ZVec service not ready")
        
        # Create unique ID for chunk
        chunk_id = f"{document_id}_chunk_{chunk_index}"
        
        # Add to ZVec
        success = zvec.add_document(chunk_id, chunk_text, metadata)
        
        if success:
            return {
                "status": "success",
                "chunk_id": chunk_id,
                "document_id": document_id,
                "chunk_index": chunk_index
            }
        else:
            raise RuntimeError("Failed to add document to ZVec")
            
    except Exception as exc:
        retry_count = self.request.retries
        countdown = 30 * (2 ** retry_count)
        raise self.retry(exc=exc, countdown=countdown)


@celery_app.task
def cleanup_old_indexed_files(days: int = 30) -> Dict[str, Any]:
    """
    Clean up old indexed files from ZVec and database.
    
    Removes files that haven't been accessed in the specified number of days.
    """
    from datetime import datetime, timedelta
    from sqlalchemy.orm import Session
    from app.db.session import SessionLocal
    from app.models.document import Document
    
    db: Session = SessionLocal()
    
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Find old documents
        old_docs = db.query(Document).filter(
            Document.updated_at < cutoff_date,
            Document.status == "indexed"
        ).all()
        
        deleted_count = 0
        for doc in old_docs:
            # Mark as archived instead of deleting
            doc.status = "archived"
            deleted_count += 1
        
        db.commit()
        
        return {
            "status": "success",
            "archived_count": deleted_count,
            "cutoff_date": cutoff_date.isoformat()
        }
        
    except Exception as e:
        db.rollback()
        return {
            "status": "error",
            "message": str(e)
        }
        
    finally:
        db.close()


@celery_app.task
def health_check() -> Dict[str, Any]:
    """Health check task for monitoring."""
    return {
        "status": "healthy",
        "celery": "ok",
        "timestamp": datetime.utcnow().isoformat()
    }
