"""
Documents API - Stub implementation
File upload and document management endpoints
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from typing import Optional
import uuid

router = APIRouter()

@router.post("/upload/public")
async def upload_public_document(
    file: UploadFile = File(...),
):
    """Upload a document (public endpoint for chat attachments)"""
    file_id = str(uuid.uuid4())
    return {
        "file_key": file_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "size": 0,
        "url": f"/api/v1/documents/{file_id}",
        "message": "Document upload stub - implement actual storage"
    }

@router.post("/upload/chat/{conversation_id}")
async def upload_chat_document(
    conversation_id: str,
    file: UploadFile = File(...),
):
    """Upload a document to a conversation"""
    file_id = str(uuid.uuid4())
    return {
        "file_key": file_id,
        "conversation_id": conversation_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "url": f"/api/v1/documents/{file_id}",
        "message": "Document upload stub - implement actual storage"
    }

@router.get("/{document_id}")
async def get_document(document_id: str):
    """Get document by ID"""
    raise HTTPException(status_code=404, detail="Document not found - stub implementation")

@router.delete("/{document_id}")
async def delete_document(document_id: str):
    """Delete document"""
    return {"message": "Document deleted (stub)"}
