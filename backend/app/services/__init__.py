"""Services package."""

from app.services.chroma_service import ChromaService, get_chroma_service, ZVecService, get_zvec_service
from app.services.document_parser import (
    extract_text_from_drive_file,
    detect_project_from_filename,
    get_file_metadata,
    list_drive_files,
)

__all__ = [
    "ChromaService",
    "get_chroma_service",
    "ZVecService",  # Backward compatibility alias
    "get_zvec_service",  # Backward compatibility alias
    "extract_text_from_drive_file",
    "detect_project_from_filename",
    "get_file_metadata",
    "list_drive_files",
]
