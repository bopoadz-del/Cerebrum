"""
Document AI API Endpoints
RESTful API for document processing including OCR, classification, and transcription.
"""

import os
import io
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, File, UploadFile, Form, Query
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from app.api.deps import get_current_user, User
from app.core.logging import get_logger
from app.pipelines.ocr import extract_text_from_image, OCRLanguage, OCRMode
from app.pipelines.document_classification import classify_document, DocumentType
from app.pipelines.ner_extraction import extract_entities
from app.pipelines.action_extraction import extract_action_items
from app.pipelines.transcription import transcribe_audio

logger = get_logger(__name__)
router = APIRouter(prefix="/documents", tags=["Document AI"])

# Pydantic Models
class OCRRequest(BaseModel):
    language: str = "eng"
    mode: str = "standard"
    preprocess: bool = True


class OCRResponse(BaseModel):
    text: str
    confidence: float
    language: str
    word_count: int
    processing_time: float


class ClassificationResponse(BaseModel):
    document_type: str
    category: str
    confidence: float
    subtype: Optional[str] = None
    key_fields: Dict[str, Any] = {}


class NERResponse(BaseModel):
    entities: List[Dict[str, Any]]
    entity_counts: Dict[str, int]
    processing_time: float


class ActionExtractionResponse(BaseModel):
    actions: List[Dict[str, Any]]
    total_found: int
    with_deadline: int
    with_assignee: int


class TranscriptionResponse(BaseModel):
    text: str
    language: str
    duration: float
    segments: List[Dict[str, Any]]
    word_count: int


class BatchProcessRequest(BaseModel):
    operations: List[str] = ["ocr", "classification", "ner"]


class BatchProcessResponse(BaseModel):
    file_id: str
    results: Dict[str, Any]
    processing_time: float


# File storage
UPLOAD_DIR = "/tmp/document_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def get_file_path(file_id: str) -> str:
    """Get full path for uploaded file."""
    return os.path.join(UPLOAD_DIR, file_id)


# OCR Endpoints
@router.post("/ocr", response_model=OCRResponse)
async def perform_ocr(
    file: UploadFile = File(...),
    language: str = Form(default="eng"),
    mode: str = Form(default="standard"),
    preprocess: bool = Form(default=True),
    current_user: User = Depends(get_current_user)
) -> OCRResponse:
    """Perform OCR on an image or PDF."""
    try:
        # Read file
        content = await file.read()
        
        # Validate file type
        if not (file.filename.endswith(('.png', '.jpg', '.jpeg', '.pdf', '.tiff'))):
            raise HTTPException(status_code=400, detail="Unsupported file type")
        
        # Perform OCR
        result = await extract_text_from_image(content, language, mode)
        
        return OCRResponse(
            text=result.text,
            confidence=result.confidence,
            language=result.language,
            word_count=result.word_count,
            processing_time=result.processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OCR failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Classification Endpoints
@router.post("/classify", response_model=ClassificationResponse)
async def classify_document_endpoint(
    file: UploadFile = File(...),
    use_gpt4: bool = Form(default=False),
    current_user: User = Depends(get_current_user)
) -> ClassificationResponse:
    """Classify a document by type."""
    try:
        # Read file
        content = await file.read()
        
        # Validate file type
        if not (file.filename.endswith(('.png', '.jpg', '.jpeg', '.pdf'))):
            raise HTTPException(status_code=400, detail="Only image and PDF files supported")
        
        # Classify document
        result = await classify_document(content, file.filename, use_gpt4)
        classification = result.primary_classification
        
        return ClassificationResponse(
            document_type=classification.document_type.value,
            category=classification.category.value,
            confidence=classification.confidence,
            subtype=classification.subtype,
            key_fields=classification.key_fields
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Classification failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# NER Endpoints
@router.post("/ner")
async def extract_named_entities(
    text: str = Form(...),
    extract_relationships: bool = Form(default=False),
    current_user: User = Depends(get_current_user)
) -> NERResponse:
    """Extract named entities from text."""
    try:
        result = await extract_entities(text, extract_relationships)
        
        return NERResponse(
            entities=result["entities"]["entities"],
            entity_counts=result["entities"]["entity_counts"],
            processing_time=result["entities"]["processing_time"]
        )
        
    except Exception as e:
        logger.error(f"NER extraction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Action Extraction Endpoints
@router.post("/actions")
async def extract_actions(
    text: str = Form(...),
    document_type: str = Form(default="meeting_minutes"),
    use_gpt4: bool = Form(default=True),
    current_user: User = Depends(get_current_user)
) -> ActionExtractionResponse:
    """Extract action items from text."""
    try:
        result = await extract_action_items(text, document_type, use_gpt4)
        
        return ActionExtractionResponse(
            actions=[a.to_dict() for a in result.actions],
            total_found=result.total_found,
            with_deadline=result.with_deadline,
            with_assignee=result.with_assignee
        )
        
    except Exception as e:
        logger.error(f"Action extraction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Transcription Endpoints
@router.post("/transcribe")
async def transcribe_audio_endpoint(
    file: UploadFile = File(...),
    language: Optional[str] = Form(default=None),
    use_parallel: bool = Form(default=True),
    current_user: User = Depends(get_current_user)
) -> TranscriptionResponse:
    """Transcribe audio/video file."""
    try:
        # Read file
        content = await file.read()
        
        # Validate file type
        valid_extensions = ('.mp3', '.mp4', '.wav', '.m4a', '.ogg', '.webm')
        if not file.filename.endswith(valid_extensions):
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type. Supported: {valid_extensions}"
            )
        
        # Transcribe
        result = await transcribe_audio(content, file.filename, language, use_parallel)
        
        return TranscriptionResponse(
            text=result.text,
            language=result.language,
            duration=result.duration,
            segments=[s.to_dict() for s in result.segments],
            word_count=result.word_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Batch Processing Endpoints
@router.post("/batch/process")
async def batch_process(
    file: UploadFile = File(...),
    operations: str = Form(default="ocr,classification"),
    current_user: User = Depends(get_current_user)
) -> BatchProcessResponse:
    """Process document with multiple operations."""
    try:
        import time
        start_time = time.time()
        
        # Read file
        content = await file.read()
        
        # Parse operations
        ops = [op.strip() for op in operations.split(",")]
        
        results = {}
        
        # Perform OCR first if needed
        if "ocr" in ops:
            ocr_result = await extract_text_from_image(content)
            results["ocr"] = ocr_result.to_dict()
            text = ocr_result.text
        else:
            text = ""
        
        # Classification
        if "classification" in ops:
            classify_result = await classify_document(content, file.filename)
            results["classification"] = classify_result.primary_classification.to_dict()
        
        # NER
        if "ner" in ops and text:
            ner_result = await extract_entities(text)
            results["ner"] = ner_result["entities"]
        
        # Action extraction
        if "actions" in ops and text:
            action_result = await extract_action_items(text)
            results["actions"] = action_result.to_dict()
        
        # Generate file ID
        file_id = f"{current_user.id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        processing_time = time.time() - start_time
        
        return BatchProcessResponse(
            file_id=file_id,
            results=results,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Batch processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# File Management Endpoints
@router.get("/files")
async def list_files(
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """List processed documents."""
    try:
        files = []
        
        for filename in os.listdir(UPLOAD_DIR):
            file_path = os.path.join(UPLOAD_DIR, filename)
            stat = os.stat(file_path)
            
            if filename.startswith(str(current_user.id)):
                files.append({
                    "file_id": filename,
                    "file_name": filename,
                    "file_size": stat.st_size,
                    "uploaded_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        
        return sorted(files, key=lambda x: x['uploaded_at'], reverse=True)
        
    except Exception as e:
        logger.error(f"Failed to list files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/files/{file_id}")
async def delete_file(
    file_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Delete a processed file."""
    try:
        if not file_id.startswith(str(current_user.id)):
            raise HTTPException(status_code=403, detail="Not authorized")
        
        file_path = get_file_path(file_id)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        return {"success": True, "message": "File deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Health Check
@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Check Document AI service health."""
    return {
        "status": "healthy",
        "services": {
            "ocr": "available",
            "classification": "available",
            "ner": "available",
            "transcription": "available"
        }
    }
