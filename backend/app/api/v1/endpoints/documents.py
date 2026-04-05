"""
Document AI API Endpoints
RESTful API for document processing including OCR, classification, and transcription.
"""

import os
import io
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, File, UploadFile, Form, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from app.api.deps import get_current_user, User, get_db
# GOOGLE DRIVE REMOVED: from app.services.google_drive_service import GoogleDriveService, GoogleDriveAuthError, GoogleDriveError
from sqlalchemy import select
from sqlalchemy.orm import Session
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
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/tmp/document_uploads")
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
        if not (file.filename.endswith(('.png', '.jpg', '.jpeg', '.pdf', '.tiff', '.webp'))):
            raise HTTPException(status_code=400, detail="Unsupported file type")
        
        # Perform OCR - handle PDFs differently from images
        from app.pipelines.ocr import TesseractOCR, OCRLanguage, OCRMode
        
        ocr = TesseractOCR()
        lang = OCRLanguage(language) if language in [l.value for l in OCRLanguage] else OCRLanguage.ENGLISH
        proc_mode = OCRMode(mode) if mode in [m.value for m in OCRMode] else OCRMode.STANDARD
        
        if file.filename.lower().endswith('.pdf'):
            result = await ocr.process_pdf(content, lang, proc_mode)
        else:
            result = await ocr.process_image(content, lang, proc_mode, preprocess)
        
        return OCRResponse(
            text=result.text,
            confidence=result.confidence,
            language=result.language,
            word_count=result.word_count,
            processing_time=result.processing_time
        )
        
    except HTTPException:
        raise
    except ImportError as e:
        logger.error(f"OCR library missing: {e}")
        raise HTTPException(status_code=503, detail=f"OCR service not available: {str(e)}")
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
        if not (file.filename.endswith(('.png', '.jpg', '.jpeg', '.pdf', '.webp'))):
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
        # Check if OpenAI API key is configured
        from app.core.config import settings
        api_key = getattr(settings, 'OPENAI_API_KEY', None)
        if not api_key or api_key == "your-openai-key-here":
            raise HTTPException(
                status_code=503,
                detail="Audio transcription is currently unavailable. OpenAI API key not configured. Please contact the administrator to enable this feature."
            )
        
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
    except RuntimeError as e:
        # Handle specific runtime errors from transcription module
        if "OpenAI API key" in str(e):
            raise HTTPException(
                status_code=503,
                detail="Audio transcription is currently unavailable. OpenAI API key not configured. Please contact the administrator to enable this feature."
            )
        logger.error(f"Transcription failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
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
        
        # Perform OCR first if needed - handle PDFs differently
        if "ocr" in ops:
            from app.pipelines.ocr import TesseractOCR, OCRLanguage, OCRMode
            
            ocr = TesseractOCR()
            lang = OCRLanguage.ENGLISH
            proc_mode = OCRMode.STANDARD
            
            try:
                if file.filename.lower().endswith('.pdf'):
                    ocr_result = await ocr.process_pdf(content, lang, proc_mode)
                else:
                    ocr_result = await ocr.process_image(content, lang, proc_mode)
                results["ocr"] = ocr_result.to_dict()
                text = ocr_result.text
            except ImportError as e:
                logger.warning(f"OCR library not available: {e}")
                results["ocr"] = {"error": f"OCR not available: {str(e)}"}
                text = ""
        else:
            text = ""
        
        # Classification
        if "classification" in ops:
            try:
                classify_result = await classify_document(content, file.filename)
                results["classification"] = classify_result.primary_classification.to_dict()
            except Exception as e:
                logger.warning(f"Classification failed: {e}")
                results["classification"] = {"error": str(e)}
        
        # NER
        if "ner" in ops and text:
            try:
                ner_result = await extract_entities(text)
                results["ner"] = ner_result["entities"]
            except Exception as e:
                logger.warning(f"NER failed: {e}")
                results["ner"] = {"error": str(e)}
        
        # Action extraction
        if "actions" in ops and text:
            try:
                action_result = await extract_action_items(text)
                results["actions"] = action_result.to_dict()
            except Exception as e:
                logger.warning(f"Action extraction failed: {e}")
                results["actions"] = {"error": str(e)}
        
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


# Invoice Processing Endpoint (for chat commands)
@router.post("/process-invoice")
async def process_invoice(
    background_tasks: BackgroundTasks,
    source: str = Form(default="google_drive"),
    auto_detect: bool = Form(default=True),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Process an invoice from Google Drive or upload."""
    import uuid
    
    task_id = str(uuid.uuid4())
    
    # In a full implementation, this would:
    # 1. Fetch the invoice from Google Drive or storage
    # 2. Extract text using OCR
    # 3. Parse invoice fields (vendor, amount, date, line items)
    # 4. Validate against POs
    # 5. Store results
    
    return {
        "task_id": task_id,
        "status": "queued",
        "message": "Invoice processing started",
        "source": source,
        "estimated_time": "2-3 minutes"
    }


# Chat File Upload Endpoint
@router.post("/upload/chat")
async def upload_chat_file(
    request: Request,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Upload a file via chat interface.
    
    Stores the file and queues background indexing.
    Returns immediately with file metadata.
    
    Enhanced for mobile browser compatibility with detailed logging.
    """
    import uuid
    from app.tasks import index_single_document
    
    # Enhanced logging for mobile debugging
    logger.info(
        "Chat file upload started",
        user_id=str(current_user.id),
        filename=file.filename,
        content_type=file.content_type,
        client_host=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "unknown"),
    )
    
    try:
        # Validate file size (max 50MB)
        max_size = 50 * 1024 * 1024  # 50MB
        file_content = await file.read()
        if len(file_content) > max_size:
            logger.warning(
                "File too large",
                filename=file.filename,
                size=len(file_content),
                max_size=max_size,
            )
            raise HTTPException(status_code=413, detail="File too large (max 50MB)")
        
        logger.info(
            "File size validated",
            filename=file.filename,
            size=len(file_content),
        )
        
        # Generate unique file ID
        file_id = f"{current_user.id}_{uuid.uuid4().hex}"
        file_ext = os.path.splitext(file.filename)[1].lower()
        safe_filename = f"{file_id}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, safe_filename)
        
        # Save file
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        logger.info(
            "File saved successfully",
            file_id=file_id,
            file_path=file_path,
        )
        
        # Determine file type category
        mime_type = file.content_type or "application/octet-stream"
        file_category = "document"
        if mime_type.startswith("image/"):
            file_category = "image"
        elif mime_type.startswith("audio/"):
            file_category = "audio"
        elif mime_type.startswith("video/"):
            file_category = "video"
        
        # Fallback: detect category from file extension if mime_type is generic
        if file_category == "document" and mime_type == "application/octet-stream":
            image_exts = ['.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp', '.tiff', '.tif']
            audio_exts = ['.mp3', '.wav', '.ogg', '.m4a', '.flac', '.aac']
            video_exts = ['.mp4', '.mov', '.avi', '.webm', '.mkv', '.flv']
            if file_ext in image_exts:
                file_category = "image"
                mime_type = f"image/{file_ext.lstrip('.')}"
            elif file_ext in audio_exts:
                file_category = "audio"
                mime_type = f"audio/{file_ext.lstrip('.')}"
            elif file_ext in video_exts:
                file_category = "video"
                mime_type = f"video/{file_ext.lstrip('.')}"
        
        # Check if text extraction is supported
        text_supported_exts = ['.pdf', '.txt', '.md', '.doc', '.docx', '.png', '.jpg', '.jpeg', '.tiff', '.webp']
        can_extract_text = file_ext in text_supported_exts or mime_type.startswith("text/")
        
        # Queue background indexing if text extraction is supported
        indexing_queued = False
        if can_extract_text:
            try:
                metadata = {
                    'name': file.filename,
                    'source': 'chat_upload',
                    'mime_type': mime_type,
                    'category': file_category,
                }
                # Queue Celery task
                task = index_single_document.delay(
                    file_id=file_id,
                    file_path=file_path,
                    user_id=str(current_user.id),
                    metadata=metadata
                )
                indexing_queued = True
                logger.info(f"Queued indexing task {task.id} for {file.filename}")
            except Exception as e:
                logger.warning(f"Failed to queue indexing: {e}")
        
        # Generate file URL
        file_url = f"/api/v1/documents/upload/chat/{file_id}"
        
        logger.info(
            "Chat file upload completed successfully",
            file_id=file_id,
            filename=file.filename,
            category=file_category,
            indexing_queued=indexing_queued,
        )
        
        return {
            "success": True,
            "file_id": file_id,
            "filename": file.filename,
            "size": len(file_content),
            "mime_type": mime_type,
            "category": file_category,
            "url": file_url,
            "indexing_queued": indexing_queued,
            "can_search": can_extract_text,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Chat file upload failed: {e}",
            exc_info=True,
            user_id=str(current_user.id),
            filename=file.filename if file else "unknown",
        )
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/upload/chat/{file_id}")
async def get_chat_file(
    file_id: str,
    current_user: User = Depends(get_current_user)
):
    """Retrieve an uploaded chat file."""
    # Security check: file_id should start with user's ID
    if not file_id.startswith(str(current_user.id)):
        raise HTTPException(status_code=403, detail="Not authorized to access this file")
    
    # Find file with any extension
    for ext in ['.pdf', '.txt', '.md', '.doc', '.docx', '.png', '.jpg', '.jpeg', '.webp',
                '.mp3', '.mp4', '.mov', '.webm', '']:
        file_path = os.path.join(UPLOAD_DIR, f"{file_id}{ext}")
        if os.path.exists(file_path):
            return FileResponse(file_path)
    
    raise HTTPException(status_code=404, detail="File not found")


# Explicit OPTIONS handler for CORS preflight (mobile browser compatibility)
@router.options("/upload/chat")
async def upload_chat_preflight(request: Request):
    """Handle CORS preflight requests for mobile browsers."""
    origin = request.headers.get("origin", "*")
    return JSONResponse(
        content={"message": "Preflight OK"},
        headers={
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Authorization, Content-Type, X-Request-ID",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "86400",
        }
    )


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


# Google Drive Integration Endpoints

class DriveFileProcessResponse(BaseModel):
    """Response for Drive file processing."""
    message: str
    document_id: Optional[str] = None
    drive_file_id: str
    filename: str
    status: str
    processing_time: float
    summary: Optional[str] = None
    entities_count: int = 0
    results: Dict[str, Any] = {}


class DriveProcessedFile(BaseModel):
    """Processed Drive file info."""
    document_id: str
    drive_file_id: Optional[str] = None
    filename: str
    status: str
    summary: Optional[str] = None
    entity_count: int = 0
    created_at: Optional[str] = None
    project_name: Optional[str] = None


@router.post("/drive/{drive_file_id}/process", response_model=DriveFileProcessResponse)
async def process_drive_file(
    drive_file_id: str,
    operations: str = "ocr,classification,ner",
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> DriveFileProcessResponse:
    """
    Process a Google Drive file with AI pipeline.
    
    Downloads from Drive, runs OCR/NER/Classification, saves to Document table.
    
    Args:
        drive_file_id: Google Drive file ID
        operations: Comma-separated list of operations (ocr,classification,ner)
    
    Returns:
        Processing results with document_id and AI summary
    """
    from app.models.document import Document
    import time

    drive_service = None  # GoogleDriveService removed

    try:
        # 1. Get metadata
        metadata = await drive_service.get_file(current_user.id, drive_file_id)

        # 2. Check if already processed
        stmt = select(Document).filter(
            Document.drive_id == drive_file_id,
            Document.user_id == current_user.id
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing and existing.status == "indexed":
            return DriveFileProcessResponse(
                message="File already processed",
                document_id=str(existing.id),
                drive_file_id=drive_file_id,
                filename=existing.filename,
                status="completed",
                processing_time=0.0,
                summary=existing.ai_summary
            )

        # 3. Create or update Document record
        if existing:
            doc = existing
            doc.status = "processing"
        else:
            doc = Document(
                drive_id=drive_file_id,
                filename=metadata['name'],
                mime_type=metadata.get('mime_type'),
                user_id=current_user.id,
                status="processing",
                project_name=metadata['name'].split('_')[0] if '_' in metadata['name'] else None
            )
            db.add(doc)

        db.commit()

        # 4. Check file size before downloading
        max_size = 50 * 1024 * 1024  # 50MB limit
        file_size = metadata.get('size', 0) or 0
        if int(file_size) > max_size:
            doc.status = "error"
            doc.ai_summary = "File too large (>50MB)"
            db.commit()
            raise HTTPException(status_code=413, detail="File too large for processing")

        # 5. Download file
        file_bytes, filename, mime_type = await drive_service.download_file(
            current_user.id, drive_file_id
        )

        # 6. Process based on file type
        results = {}
        ops = [op.strip() for op in operations.split(",")]
        text_content = ""

        start_time = time.time()

        # OCR for images/PDFs
        if "ocr" in ops and any(t in mime_type for t in ['pdf', 'image', 'officedocument', 'document']):
            try:
                ocr_result = await extract_text_from_image(file_bytes)
                results["ocr"] = ocr_result.to_dict() if hasattr(ocr_result, 'to_dict') else {"text": str(ocr_result)}
                text_content = results["ocr"].get("text", "")
            except Exception as e:
                logger.warning(f"OCR failed: {e}")
                results["ocr_error"] = str(e)

        # Classification
        if "classification" in ops:
            try:
                classify_result = await classify_document(file_bytes, filename)
                if hasattr(classify_result, 'primary_classification'):
                    results["classification"] = classify_result.primary_classification.to_dict()
                else:
                    results["classification"] = {"result": str(classify_result)}
            except Exception as e:
                logger.warning(f"Classification failed: {e}")
                results["classification_error"] = str(e)

        # NER
        if "ner" in ops and text_content:
            try:
                ner_result = await extract_entities(text_content)
                results["ner"] = ner_result.get("entities", {}).get("entities", [])
            except Exception as e:
                logger.warning(f"NER failed: {e}")
                results["ner_error"] = str(e)

        # ChromaDB INDEXING - Index document for semantic search
        if text_content and len(text_content) > 50:
            try:
                from app.services.chroma_service import get_chroma_service
                chroma = get_chroma_service()
                
                doc_id = f"drive_{drive_file_id}"
                chroma_metadata = {
                    'name': metadata['name'],
                    'source': 'google_drive',
                    'mime_type': metadata.get('mimeType'),
                    'user_id': str(current_user.id),
                    'content_preview': text_content[:500],
                    'drive_file_id': drive_file_id,
                    'document_id': str(doc.id),
                    'entities': results.get('ner', [])[:5],  # Store top 5 entities
                }
                chroma.add_document(doc_id, text_content, chroma_metadata)
                results['chroma_indexed'] = True
            except Exception as e:
                logger.warning(f"ChromaDB indexing failed for {drive_file_id}: {e}")
                results['chroma_indexed'] = False

        # 7. Update Document record with results
        processing_time = time.time() - start_time

        doc.status = "indexed"
        doc.content = text_content[:50000] if text_content else None  # Limit storage
        doc.ai_summary = _generate_summary(results, text_content)
        doc.entities = results.get("ner", [])
        doc.processing_metadata = {
            "operations": ops,
            "processing_time": processing_time,
            "file_size": len(file_bytes),
            "mime_type": mime_type,
            "results": {k: v for k, v in results.items() if not k.endswith('_error')}
        }

        db.commit()

        return DriveFileProcessResponse(
            message="Processing completed",
            document_id=str(doc.id),
            drive_file_id=drive_file_id,
            filename=metadata['name'],
            status="indexed",
            processing_time=processing_time,
            summary=doc.ai_summary,
            entities_count=len(doc.entities) if doc.entities else 0,
            results=results
        )

# GOOGLE DRIVE REMOVED:     except GoogleDriveAuthError as e:
# GOOGLE DRIVE REMOVED:         raise HTTPException(status_code=401, detail=str(e))
# GOOGLE DRIVE REMOVED:     except GoogleDriveError as e:
# GOOGLE DRIVE REMOVED:         raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Drive file processing failed: {e}", exc_info=True)
        # Update status to error if doc exists
        if 'doc' in locals():
            doc.status = "error"
            doc.ai_summary = f"Processing failed: {str(e)}"
            db.commit()
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


def _generate_summary(results: dict, text_content: str) -> str:
    """Generate human-readable summary from results."""
    summary_parts = []

    # Classification
    if "classification" in results:
        cls = results["classification"]
        if isinstance(cls, dict):
            if "document_type" in cls:
                summary_parts.append(f"Type: {cls['document_type']}")
            elif "label" in cls:
                summary_parts.append(f"Document type: {cls['label']}")

    # Entities
    if "ner" in results and results["ner"]:
        entities = results["ner"]
        if len(entities) > 0:
            entity_types = set(
                e.get("type", e.get("label", "unknown")) 
                for e in entities[:5]
            )
            summary_parts.append(f"Key elements: {', '.join(entity_types)}")

    # Text stats
    if text_content:
        word_count = len(text_content.split())
        summary_parts.append(f"Extracted {word_count} words")

    return " | ".join(summary_parts) if summary_parts else "Document processed successfully"


@router.get("/drive/processed", response_model=List[DriveProcessedFile])
async def list_processed_drive_files(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[DriveProcessedFile]:
    """List all AI-processed Drive files for current user."""
    from app.models.document import Document

    stmt = select(Document).filter(
        Document.user_id == current_user.id,
        Document.drive_id.isnot(None)
    ).order_by(Document.created_at.desc())
    result = await db.execute(stmt)
    docs = result.scalars().all()

    return [
        DriveProcessedFile(
            document_id=str(d.id),
            drive_file_id=d.drive_id,
            filename=d.filename,
            status=d.status,
            summary=d.ai_summary,
            entity_count=len(d.entities) if d.entities else 0,
            created_at=d.created_at.isoformat() if d.created_at else None,
            project_name=d.project_name
        )
        for d in docs
    ]


@router.get("/search")
async def search_documents(
    query: str = Query(..., description="Search query"),
    top_k: int = Query(default=5, ge=1, le=20, description="Number of results"),
    source: Optional[str] = Query(default=None, description="Filter by source (google_drive, chat_upload)"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Semantic search across all indexed documents using ChromaDB.
    
    Searches through documents processed from Google Drive and chat uploads.
    Returns ranked results based on semantic similarity to the query.
    """
    try:
        from app.services.chroma_service import get_chroma_service
        
        chroma = get_chroma_service()
        
        # Check if ChromaDB is ready
        if not chroma.is_ready():
            return {
                "query": query,
                "results": [],
                "total": 0,
                "warning": "ChromaDB service not available (vector DB not initialized)"
            }
        
        # Perform search
        results = chroma.search_similar(query, top_k=top_k)
        
        # Filter by user_id and optionally by source
        filtered_results = []
        for r in results:
            metadata = r.get('metadata', {})
            # Only return results for current user
            if str(metadata.get('user_id')) == str(current_user.id):
                # Filter by source if specified
                if source is None or metadata.get('source') == source:
                    filtered_results.append({
                        "id": r['id'],
                        "score": r['score'],
                        "name": metadata.get('name'),
                        "source": metadata.get('source'),
                        "mime_type": metadata.get('mime_type'),
                        "content_preview": metadata.get('content_preview'),
                        "drive_file_id": metadata.get('drive_file_id'),
                        "document_id": metadata.get('document_id'),
                        "entities": metadata.get('entities', [])
                    })
        
        return {
            "query": query,
            "results": filtered_results,
            "total": len(filtered_results),
            "source_filter": source
        }
        
    except Exception as e:
        logger.error(f"Document search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/chroma/stats")
async def get_chroma_stats(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get ChromaDB database statistics."""
    try:
        from app.services.chroma_service import get_chroma_service
        
        chroma = get_chroma_service()
        stats = await chroma.get_stats()
        
        return {
            "ready": stats.get('ready', False),
            "total_documents": stats.get('count', 0),
            "service": "ChromaDB",
            "mode": stats.get('mode', 'unknown')
        }
        
    except Exception as e:
        logger.error(f"Failed to get ChromaDB stats: {e}")
        return {
            "ready": False,
            "total_documents": 0,
            "error": str(e)
        }


@router.post("/chroma/reindex")
async def reindex_with_ml_embeddings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Reindex all documents with ML embeddings.
    
    Use this when switching from hash-based to ML embeddings
    to regenerate all vectors with the sentence-transformers model.
    """
    try:
        from app.services.chroma_service import get_chroma_service
        from app.models.document import Document
        
        chroma = get_chroma_service()
        
        # Get all documents from database
        stmt = select(Document).filter(
            Document.user_id == current_user.id,
            Document.status == "indexed"
        )
        result = await db.execute(stmt)
        documents = result.scalars().all()
        
        if not documents:
            return {
                "status": "success",
                "message": "No documents to reindex",
                "processed": 0
            }
        
        # Prepare for reindexing
        docs_to_index = []
        for doc in documents:
            docs_to_index.append({
                'id': f"doc_{doc.id}",
                'text': doc.content or '',
                'metadata': {
                    'name': doc.filename,
                    'source': 'reindex',
                    'mime_type': doc.mime_type,
                    'user_id': str(current_user.id),
                    'document_id': str(doc.id)
                }
            })
        
        # Reindex with current embedding model
        result = chroma.reindex_all(docs_to_index)
        
        return {
            "status": result["status"],
            "processed": result.get("success_count", 0),
            "errors": result.get("error_count", 0),
            "total": len(documents),
            "embedding_model": result.get("embedding_model", {})
        }
        
    except Exception as e:
        logger.error(f"Reindex failed: {e}")
        raise HTTPException(status_code=500, detail=f"Reindex failed: {str(e)}")


@router.post("/chroma/hydrate")
async def trigger_hydration(
    full_scan: bool = False,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Trigger hydration task to sync local files with ChromaDB index.
    
    This is useful for:
    - Reindexing files that failed during upload
    - Cleaning up orphaned index entries
    - Full re-scan of upload directory
    
    The task runs asynchronously on the slow worker queue.
    """
    try:
        from app.tasks import process_upload_hydration
        
        # Queue hydration task
        task = process_upload_hydration.delay(full_scan=full_scan)
        
        return {
            "status": "queued",
            "task_id": task.id,
            "message": "Hydration task started. Check /chroma/stats for progress.",
            "full_scan": full_scan
        }
        
    except Exception as e:
        logger.error(f"Failed to queue hydration: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start hydration: {str(e)}")


# Backward compatibility alias
@router.get("/zvec/stats")
async def get_zvec_stats_legacy(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Legacy endpoint - redirects to ChromaDB stats."""
    return await get_chroma_stats(current_user)


# =============================================================================
# Phase 3.2: Enhanced Document Extraction
# =============================================================================

@router.post("/extract")
async def extract_document_data_endpoint(
    file: UploadFile = File(...),
    doc_type: Optional[str] = Form(default=None, description="Document type: invoice, receipt, contract"),
    use_llm: bool = Form(default=True, description="Use LLM for extraction"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Extract structured data from documents using OCR + LLM.
    
    Supports invoices, receipts, contracts with automatic field extraction:
    - Invoice: vendor, invoice_number, dates, amounts, line_items
    - Receipt: merchant, date, items, total
    - Contract: parties, dates, value, key_terms
    
    Uses local LLM (Ollama) with rule-based fallback for reliability.
    """
    try:
        from app.pipelines.document_extraction import DocumentExtractionPipeline, DocumentType
        
        # Read file
        content = await file.read()
        
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Empty file")
        
        if len(content) > 20 * 1024 * 1024:  # 20MB limit
            raise HTTPException(status_code=413, detail="File too large (max 20MB)")
        
        # Parse document type
        doc_type_enum = None
        if doc_type:
            try:
                doc_type_enum = DocumentType(doc_type.lower())
            except ValueError:
                pass
        
        # Extract
        pipeline = DocumentExtractionPipeline(use_llm=use_llm)
        result = await pipeline.extract_document(content, file.filename, doc_type_enum)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document extraction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


@router.post("/extract/enhanced-ocr")
async def enhanced_ocr_endpoint(
    file: UploadFile = File(...),
    language: str = Form(default="eng"),
    mode: str = Form(default="auto", description="OCR mode: auto, tesseract, easyocr"),
    deskew: bool = Form(default=True),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Enhanced OCR with deskewing, contrast enhancement, and multi-engine support.
    
    Features:
    - Automatic deskewing (rotation correction)
    - CLAHE contrast enhancement
    - Auto-selection between Tesseract (documents) and EasyOCR (scene text)
    - Better accuracy for scanned and photographed documents
    """
    try:
        from app.pipelines.ocr import EnhancedOCR, OCREngine, OCRLanguage, OCRMode as OCRModeEnum
        
        # Read file
        content = await file.read()
        
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Empty file")
        
        if len(content) > 10 * 1024 * 1024:  # 10MB limit for OCR
            raise HTTPException(status_code=413, detail="File too large (max 10MB)")
        
        # Determine engine
        engine_map = {
            "auto": OCREngine.AUTO,
            "tesseract": OCREngine.TESSERACT,
            "easyocr": OCREngine.EASYOCR
        }
        engine = engine_map.get(mode.lower(), OCREngine.AUTO)
        
        # Process
        ocr = EnhancedOCR(default_engine=engine)
        
        lang = OCRLanguage(language) if language in [l.value for l in OCRLanguage] else OCRLanguage.ENGLISH
        
        if file.filename.lower().endswith('.pdf'):
            result = await ocr.process_pdf(content, language=lang)
        else:
            result = await ocr.process_image(content, language=lang, engine=engine)
        
        return {
            "text": result.text,
            "confidence": result.confidence,
            "language": result.language,
            "word_count": result.word_count,
            "page_count": result.page_count,
            "processing_time": result.processing_time,
            "engine_used": result.metadata.get("engine", "tesseract"),
            "blocks": [b.to_dict() for b in result.blocks]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Enhanced OCR failed: {e}")
        raise HTTPException(status_code=500, detail=f"OCR failed: {str(e)}")


@router.post("/classify")
async def classify_document_endpoint(
    file: UploadFile = File(...),
    use_llm: bool = Form(default=True, description="Use LLM for classification"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Classify document type using ML (local LLM) with rule-based fallback.
    
    Detects document types:
    - invoice, receipt, contract, change_order
    - safety_report, daily_report
    - blueprint, specification, submittal
    - rfi, rfq, permit
    - meeting_minutes, correspondence
    
    Returns document type, category, confidence, and key indicators.
    """
    try:
        from app.pipelines.document_classification_v2 import DocumentClassificationPipeline
        
        # Read file
        content = await file.read()
        
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Empty file")
        
        if len(content) > 20 * 1024 * 1024:  # 20MB limit
            raise HTTPException(status_code=413, detail="File too large (max 20MB)")
        
        # Classify
        pipeline = DocumentClassificationPipeline(use_llm=use_llm)
        result = await pipeline.classify(content, file.filename)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document classification failed: {e}")
        raise HTTPException(status_code=500, detail=f"Classification failed: {str(e)}")
