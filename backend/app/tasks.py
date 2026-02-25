"""
Celery Tasks for Cerebrum AI Platform

Background tasks for processing Drive files via API, indexing documents, etc.
No files are downloaded to disk - everything is processed via Google Drive API.
"""

import os
import asyncio
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
    task_time_limit=1800,  # 30 min max per task (Drive API calls can be slow)
    worker_prefetch_multiplier=1,
)


@celery_app.task(bind=True, max_retries=3)
def process_drive_file_batch(
    self,
    file_ids: List[str],
    user_id: str,
    access_token: str
) -> Dict[str, Any]:
    """
    Process a batch of Google Drive files via API (no downloads).
    
    For each file:
    1. Calls Drive API to extract text (export for Docs, stream for PDFs)
    2. Generates embeddings locally using sentence-transformers
    3. Indexes in ZVec vector store (local, no cloud DB)
    4. Saves metadata to SQL database
    
    Files are never saved to disk - processed entirely in memory.
    
    Args:
        file_ids: List of Google Drive file IDs to process
        user_id: UUID of the user owning these files
        access_token: Google OAuth access token
    
    Returns:
        Dict with processed count and status
    """
    from sqlalchemy.orm import Session
    from app.db.session import SessionLocal
    from app.services.document_parser import (
        extract_text_from_drive_file,
        detect_project_from_filename,
        list_drive_files
    )
    from app.services.zvec_service import get_zvec_service
    from app.models.document import Document
    
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
        
        # Get file metadata from Drive API
        # Run async function in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            files_info = loop.run_until_complete(
                list_drive_files(access_token, page_size=100)
            )
            # Filter to requested file IDs
            files_info = [f for f in files_info if f['id'] in file_ids]
        finally:
            loop.close()
        
        # Process each file
        for file_info in files_info:
            file_id = file_info['id']
            
            try:
                # Check if already indexed
                existing = db.query(Document).filter(
                    Document.drive_id == file_id
                ).first()
                
                if existing and existing.status == "indexed":
                    continue  # Skip already indexed files
                
                # Extract text via Drive API (in memory, no download)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    text = loop.run_until_complete(
                        extract_text_from_drive_file(
                            file_id,
                            access_token,
                            file_info.get('mimeType', 'application/pdf')
                        )
                    )
                finally:
                    loop.close()
                
                if not text or len(text) < 100:
                    print(f"Skipping {file_id}: insufficient content")
                    continue
                
                # Detect project from filename
                project_name = detect_project_from_filename(file_info['name'])
                
                # Index in ZVec (local vector DB)
                doc_id = f"drive_{file_id}"
                metadata = {
                    'drive_id': file_id,
                    'name': file_info['name'],
                    'mime_type': file_info.get('mimeType'),
                    'modified_time': file_info.get('modifiedTime'),
                    'user_id': user_id,
                    'project': project_name,
                    'content_preview': text[:500]
                }
                
                success = zvec.add_document(doc_id, text, metadata)
                
                if success:
                    # Save to SQL database
                    if existing:
                        existing.content = text[:2000]
                        existing.project_name = project_name
                        existing.status = "indexed"
                        existing.updated_at = datetime.utcnow()
                    else:
                        doc = Document(
                            drive_id=file_id,
                            filename=file_info['name'],
                            content=text[:2000],
                            project_name=project_name,
                            mime_type=file_info.get('mimeType'),
                            status="indexed",
                            user_id=user_id
                        )
                        db.add(doc)
                    
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
        retry_count = self.request.retries
        countdown = 60 * (2 ** retry_count)
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
    Index a single document chunk in ZVec (for large documents).
    """
    from app.services.zvec_service import get_zvec_service
    
    try:
        zvec = get_zvec_service()
        
        if not zvec.is_ready():
            raise RuntimeError("ZVec service not ready")
        
        chunk_id = f"{document_id}_chunk_{chunk_index}"
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
    """
    from sqlalchemy.orm import Session
    from app.db.session import SessionLocal
    from app.models.document import Document
    
    db: Session = SessionLocal()
    
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        old_docs = db.query(Document).filter(
            Document.updated_at < cutoff_date,
            Document.status == "indexed"
        ).all()
        
        archived_count = 0
        for doc in old_docs:
            doc.status = "archived"
            archived_count += 1
        
        db.commit()
        
        return {
            "status": "success",
            "archived_count": archived_count,
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


@celery_app.task(bind=True, max_retries=2)
def sync_drive_projects(self, user_id: str) -> Dict[str, Any]:
    """
    Discover 'smart' Google Drive projects (folder-first scan) and upsert:
      - Project
      - GoogleDriveProject mapping

    This is metadata-only discovery (no ZVec indexing here yet).
    """
    import uuid as _uuid
    from sqlalchemy.orm import Session
    from app.db.session import SessionLocal
    from app.services.drive_project_sync import discover_and_upsert_drive_projects

    db: Session = SessionLocal()
    try:
        uid = _uuid.UUID(user_id)
        return discover_and_upsert_drive_projects(db, uid)
    except Exception as exc:
        db.rollback()
        retry_count = getattr(self.request, "retries", 0)
        countdown = 30 * (2 ** retry_count)
        raise self.retry(exc=exc, countdown=countdown)
    finally:
        db.close()
