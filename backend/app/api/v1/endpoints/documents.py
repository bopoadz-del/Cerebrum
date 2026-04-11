"""
Documents API - GCS Implementation
File upload and document management endpoints with Google Cloud Storage
"""

import uuid
import io
from typing import Optional, List
from datetime import datetime, timedelta

from fastapi import (
    APIRouter, UploadFile, File, HTTPException, Depends, 
    BackgroundTasks, Query, Request
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

# Google Cloud Storage
from google.cloud import storage
from google.cloud.storage import Blob

from app.db.session import get_db_session
from app.core.logging import get_logger
from app.core.config import settings
from app.models.user import User
from app.models.message import FileUpload
from app.api.v1.endpoints.auth import get_current_user

logger = get_logger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])

# GCS Configuration
GCS_BUCKET_NAME = "cerebrum-documents-30d9c"
GCS_PROJECT_ID = "cerebrum-30d9c"

# File upload limits
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_CONTENT_TYPES = [
    # Documents
    "application/pdf",
    "text/plain",
    "text/markdown",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    # Images
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    # Spreadsheets
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/csv",
]


def get_gcs_client() -> storage.Client:
    """Get GCS client instance."""
    return storage.Client(project=GCS_PROJECT_ID)


def validate_file(file: UploadFile) -> None:
    """Validate file type and size."""
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{file.content_type}' not allowed. Allowed types: {', '.join(ALLOWED_CONTENT_TYPES)}"
        )


async def upload_to_gcs(
    file_content: bytes,
    destination_path: str,
    content_type: str,
) -> str:
    """
    Upload file to Google Cloud Storage.
    
    Returns:
        Public URL of the uploaded file
    """
    try:
        client = get_gcs_client()
        bucket = client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(destination_path)
        
        # Upload with content type
        blob.upload_from_string(
            file_content,
            content_type=content_type,
        )
        
        # Make blob publicly readable
        blob.make_public()
        
        logger.info(f"Uploaded file to gs://{GCS_BUCKET_NAME}/{destination_path}")
        return blob.public_url
        
    except Exception as e:
        logger.error(f"GCS upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")


async def delete_from_gcs(storage_path: str) -> None:
    """Delete file from Google Cloud Storage."""
    try:
        client = get_gcs_client()
        bucket = client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(storage_path)
        blob.delete()
        logger.info(f"Deleted file from gs://{GCS_BUCKET_NAME}/{storage_path}")
    except Exception as e:
        logger.error(f"GCS delete failed: {e}")
        # Don't raise - file might not exist


@router.post("/upload")
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    conversation_id: Optional[str] = Query(None, description="Optional conversation ID to associate with"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a document to GCS and save metadata to database.
    
    Returns file metadata including public URL.
    """
    # Validate file
    validate_file(file)
    
    # Read file content
    content = await file.read()
    
    # Check file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum of {MAX_FILE_SIZE // (1024*1024)}MB"
        )
    
    # Generate unique filename
    file_id = uuid.uuid4()
    file_ext = file.filename.split('.')[-1] if '.' in file.filename else ''
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    storage_filename = f"{current_user.id}/{timestamp}_{file_id}.{file_ext}" if file_ext else f"{current_user.id}/{timestamp}_{file_id}"
    
    try:
        # Upload to GCS
        public_url = await upload_to_gcs(
            file_content=content,
            destination_path=storage_filename,
            content_type=file.content_type,
        )
        
        # Parse conversation_id if provided
        conv_id_uuid = None
        if conversation_id:
            try:
                conv_id_uuid = uuid.UUID(conversation_id)
            except ValueError:
                logger.warning(f"Invalid conversation_id format: {conversation_id}")
        
        # Save to database
        file_upload = FileUpload(
            id=file_id,
            user_id=current_user.id,
            conversation_id=conv_id_uuid,
            filename=storage_filename,
            original_filename=file.filename,
            content_type=file.content_type,
            size_bytes=len(content),
            storage_provider="gcs",
            storage_bucket=GCS_BUCKET_NAME,
            storage_path=storage_filename,
            public_url=public_url,
            status="pending",  # Will be updated after processing
        )
        
        db.add(file_upload)
        await db.commit()
        await db.refresh(file_upload)
        
        logger.info(f"Document uploaded: {file_id} by user {current_user.id}")
        
        return {
            "success": True,
            "file_id": str(file_id),
            "filename": file.filename,
            "content_type": file.content_type,
            "size_bytes": len(content),
            "url": public_url,
            "conversation_id": conversation_id,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document upload failed: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/upload/public")
async def upload_public_document(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Upload a document without authentication (public endpoint for chat attachments).
    
    **Note:** Files uploaded here are temporary and may be cleaned up.
    """
    # Validate file
    validate_file(file)
    
    # Read file content
    content = await file.read()
    
    # Check file size (smaller limit for public uploads)
    if len(content) > 10 * 1024 * 1024:  # 10MB for public
        raise HTTPException(
            status_code=400,
            detail="File size exceeds maximum of 10MB for public uploads"
        )
    
    # Generate unique filename in temp folder
    file_id = uuid.uuid4()
    file_ext = file.filename.split('.')[-1] if '.' in file.filename else ''
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    storage_filename = f"temp/{timestamp}_{file_id}.{file_ext}" if file_ext else f"temp/{timestamp}_{file_id}"
    
    try:
        # Upload to GCS
        public_url = await upload_to_gcs(
            file_content=content,
            destination_path=storage_filename,
            content_type=file.content_type,
        )
        
        logger.info(f"Public document uploaded: {file_id}")
        
        return {
            "success": True,
            "file_key": str(file_id),
            "filename": file.filename,
            "content_type": file.content_type,
            "size_bytes": len(content),
            "url": public_url,
        }
        
    except Exception as e:
        import traceback
        error_msg = f"{type(e).__name__}: {str(e)}"
        logger.error(f"Public document upload failed: {error_msg}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Upload failed: {error_msg}")


@router.post("/upload/chat/{conversation_id}")
async def upload_chat_document(
    conversation_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Upload a document to a specific conversation."""
    # This is just a wrapper around upload_document with conversation_id in path
    from fastapi import Request
    
    # Create a mock request object
    request = Request(scope={"type": "http"})
    
    return await upload_document(
        request=request,
        background_tasks=None,
        file=file,
        conversation_id=conversation_id,
        db=db,
        current_user=current_user,
    )


@router.get("/my")
async def list_my_documents(
    conversation_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> List[dict]:
    """List documents uploaded by the current user."""
    query = select(FileUpload).where(FileUpload.user_id == current_user.id)
    
    if conversation_id:
        try:
            conv_uuid = uuid.UUID(conversation_id)
            query = query.where(FileUpload.conversation_id == conv_uuid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid conversation_id format")
    
    query = query.order_by(desc(FileUpload.created_at)).offset(offset).limit(limit)
    
    result = await db.execute(query)
    files = result.scalars().all()
    
    return [file.to_dict() for file in files]


@router.get("/{document_id}")
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Get document metadata by ID."""
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID format")
    
    result = await db.execute(
        select(FileUpload).where(
            FileUpload.id == doc_uuid,
            FileUpload.user_id == current_user.id
        )
    )
    file = result.scalar_one_or_none()
    
    if not file:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return file.to_dict()


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Delete a document."""
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID format")
    
    result = await db.execute(
        select(FileUpload).where(
            FileUpload.id == doc_uuid,
            FileUpload.user_id == current_user.id
        )
    )
    file = result.scalar_one_or_none()
    
    if not file:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete from GCS
    await delete_from_gcs(file.storage_path)
    
    # Delete from database
    await db.delete(file)
    await db.commit()
    
    logger.info(f"Document deleted: {document_id} by user {current_user.id}")
    
    return {"success": True, "message": "Document deleted"}


@router.get("/{document_id}/download")
async def get_download_url(
    document_id: str,
    expiry_minutes: int = Query(15, ge=1, le=60),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """
    Get a signed URL for downloading a private document.
    
    Note: Most documents are public, but this can be used for private files
    or to generate temporary download links.
    """
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID format")
    
    result = await db.execute(
        select(FileUpload).where(
            FileUpload.id == doc_uuid,
            FileUpload.user_id == current_user.id
        )
    )
    file = result.scalar_one_or_none()
    
    if not file:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Generate signed URL
    try:
        client = get_gcs_client()
        bucket = client.bucket(file.storage_bucket)
        blob = bucket.blob(file.storage_path)
        
        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=expiry_minutes),
            method="GET",
        )
        
        return {
            "success": True,
            "download_url": url,
            "expires_in_minutes": expiry_minutes,
        }
    except Exception as e:
        logger.error(f"Failed to generate signed URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate download URL")
