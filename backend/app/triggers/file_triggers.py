"""
File Triggers - Auto-process file uploads

Automatically processes files when they are uploaded:
- Document OCR and text extraction
- IFC/BIM model processing
- Image analysis
- Virus scanning
- Thumbnail generation
"""

import asyncio
from typing import Dict, Any, Optional
from pathlib import Path

from app.core.logging import get_logger
from app.triggers.engine import Event, EventType, event_bus
from app.workers.celery_config import slow_task

logger = get_logger(__name__)


class FileTriggerManager:
    """
    Manages file-related triggers and automatic processing.
    """
    
    def __init__(self):
        """Initialize the file trigger manager."""
        self._processors: Dict[str, Any] = {}
        self._register_handlers()
        
    def _register_handlers(self) -> None:
        """Register all file event handlers."""
        event_bus.register(EventType.FILE_UPLOADED, self._on_file_uploaded)
        event_bus.register(EventType.FILE_UPDATED, self._on_file_updated)
        event_bus.register(EventType.FILE_DELETED, self._on_file_deleted)
        logger.info("File trigger handlers registered")
        
    async def _on_file_uploaded(self, event: Event) -> None:
        """
        Handle file upload event.
        
        Args:
            event: File upload event
        """
        payload = event.payload
        file_id = payload.get("file_id")
        file_path = payload.get("file_path")
        file_name = payload.get("file_name")
        mime_type = payload.get("mime_type")
        
        logger.info(
            "File uploaded - auto-processing",
            file_id=file_id,
            file_name=file_name,
            mime_type=mime_type,
        )
        
        # Determine file type and route to appropriate processor
        if self._is_document(mime_type, file_name):
            await self._process_document(file_id, file_path, payload)
        elif self._is_ifc(file_name):
            await self._process_ifc(file_id, file_path, payload)
        elif self._is_image(mime_type):
            await self._process_image(file_id, file_path, payload)
        else:
            logger.info(f"No auto-processor for file type: {mime_type}")
            
        # Emit file processed event
        await event_bus.emit(
            event_bus.create_event(
                EventType.FILE_PROCESSED,
                source="file_triggers",
                payload={
                    "file_id": file_id,
                    "file_name": file_name,
                    "processed_at": "auto",
                },
                tenant_id=event.tenant_id,
                user_id=event.user_id,
                correlation_id=event.correlation_id,
            )
        )
        
    async def _on_file_updated(self, event: Event) -> None:
        """
        Handle file update event.
        
        Args:
            event: File update event
        """
        payload = event.payload
        file_id = payload.get("file_id")
        
        logger.info("File updated - reprocessing", file_id=file_id)
        
        # Re-process the file
        await self._on_file_uploaded(event)
        
    async def _on_file_deleted(self, event: Event) -> None:
        """
        Handle file deletion event.
        
        Args:
            event: File deletion event
        """
        payload = event.payload
        file_id = payload.get("file_id")
        
        logger.info("File deleted - cleaning up", file_id=file_id)
        
        # Clean up related data
        # This could include:
        # - Removing extracted text
        # - Deleting thumbnails
        # - Cleaning up search indexes
        
    def _is_document(self, mime_type: Optional[str], file_name: str) -> bool:
        """Check if file is a document."""
        doc_types = [
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument",
            "text/plain",
            "text/html",
        ]
        doc_extensions = [".pdf", ".doc", ".docx", ".txt", ".html", ".htm"]
        
        if mime_type and any(t in mime_type for t in doc_types):
            return True
        if any(file_name.lower().endswith(ext) for ext in doc_extensions):
            return True
        return False
        
    def _is_ifc(self, file_name: str) -> bool:
        """Check if file is an IFC model."""
        return file_name.lower().endswith(".ifc")
        
    def _is_image(self, mime_type: Optional[str]) -> bool:
        """Check if file is an image."""
        if mime_type and mime_type.startswith("image/"):
            return True
        return False
        
    async def _process_document(
        self,
        file_id: str,
        file_path: str,
        metadata: Dict[str, Any],
    ) -> None:
        """
        Process a document file.
        
        Args:
            file_id: File ID
            file_path: Path to file
            metadata: File metadata
        """
        logger.info("Processing document", file_id=file_id)
        
        # Queue OCR task
        process_document_ocr.delay(file_id, file_path)
        
        # Queue classification task
        classify_document.delay(file_id, file_path)
        
    async def _process_ifc(
        self,
        file_id: str,
        file_path: str,
        metadata: Dict[str, Any],
    ) -> None:
        """
        Process an IFC model file.
        
        Args:
            file_id: File ID
            file_path: Path to file
            metadata: File metadata
        """
        logger.info("Processing IFC model", file_id=file_id)
        
        # Queue IFC processing task
        process_ifc_model.delay(file_id, file_path)
        
    async def _process_image(
        self,
        file_id: str,
        file_path: str,
        metadata: Dict[str, Any],
    ) -> None:
        """
        Process an image file.
        
        Args:
            file_id: File ID
            file_path: Path to file
            metadata: File metadata
        """
        logger.info("Processing image", file_id=file_id)
        
        # Queue image analysis task
        analyze_image.delay(file_id, file_path)


# Celery tasks for background processing
@slow_task(bind=True, max_retries=3)
def process_document_ocr(self, file_id: str, file_path: str) -> Dict[str, Any]:
    """
    Process document OCR in background.
    
    Args:
        file_id: File ID
        file_path: Path to document
        
    Returns:
        OCR results
    """
    try:
        logger.info("Starting OCR processing", file_id=file_id)
        
        # Import here to avoid circular dependencies
        from app.pipelines.ocr import extract_text_from_document
        
        result = extract_text_from_document(file_path)
        
        logger.info("OCR processing completed", file_id=file_id)
        
        return {
            "status": "success",
            "file_id": file_id,
            "text_length": len(result.get("text", "")),
        }
        
    except Exception as exc:
        logger.error("OCR processing failed", file_id=file_id, error=str(exc))
        raise self.retry(exc=exc, countdown=60)


@slow_task(bind=True, max_retries=3)
def classify_document(self, file_id: str, file_path: str) -> Dict[str, Any]:
    """
    Classify document type in background.
    
    Args:
        file_id: File ID
        file_path: Path to document
        
    Returns:
        Classification results
    """
    try:
        logger.info("Starting document classification", file_id=file_id)
        
        from app.pipelines.document_classification import classify_document_type
        
        result = classify_document_type(file_path)
        
        logger.info("Document classification completed", file_id=file_id)
        
        return {
            "status": "success",
            "file_id": file_id,
            "document_type": result.get("type"),
            "confidence": result.get("confidence"),
        }
        
    except Exception as exc:
        logger.error("Document classification failed", file_id=file_id, error=str(exc))
        raise self.retry(exc=exc, countdown=60)


@slow_task(bind=True, max_retries=2)
def process_ifc_model(self, file_id: str, file_path: str) -> Dict[str, Any]:
    """
    Process IFC model in background.
    
    Args:
        file_id: File ID
        file_path: Path to IFC file
        
    Returns:
        Processing results
    """
    try:
        logger.info("Starting IFC processing", file_id=file_id)
        
        from app.pipelines.ifc_geometry import extract_ifc_geometry
        from app.pipelines.ifc_properties import extract_ifc_properties
        
        # Extract geometry
        geometry = extract_ifc_geometry(file_path)
        
        # Extract properties
        properties = extract_ifc_properties(file_path)
        
        logger.info("IFC processing completed", file_id=file_id)
        
        return {
            "status": "success",
            "file_id": file_id,
            "element_count": len(geometry.get("elements", [])),
            "property_count": len(properties.get("properties", {})),
        }
        
    except Exception as exc:
        logger.error("IFC processing failed", file_id=file_id, error=str(exc))
        raise self.retry(exc=exc, countdown=300)


@slow_task(bind=True, max_retries=3)
def analyze_image(self, file_id: str, file_path: str) -> Dict[str, Any]:
    """
    Analyze image in background.
    
    Args:
        file_id: File ID
        file_path: Path to image
        
    Returns:
        Analysis results
    """
    try:
        logger.info("Starting image analysis", file_id=file_id)
        
        # Generate thumbnail
        from PIL import Image
        
        img = Image.open(file_path)
        img.thumbnail((300, 300))
        
        thumbnail_path = f"{file_path}.thumb.jpg"
        img.save(thumbnail_path, "JPEG")
        
        logger.info("Image analysis completed", file_id=file_id)
        
        return {
            "status": "success",
            "file_id": file_id,
            "thumbnail_path": thumbnail_path,
        }
        
    except Exception as exc:
        logger.error("Image analysis failed", file_id=file_id, error=str(exc))
        raise self.retry(exc=exc, countdown=60)


# Global instance
file_trigger_manager = FileTriggerManager()
