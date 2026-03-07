"""Services package."""

# ZVec service - uses OpenAI if API key available, else local/Mock
try:
    from app.services.zvec_openai_service import get_zvec_service, ZVecOpenAIService
except ImportError:
    from app.services.zvec_service import ZVecService as ZVecOpenAIService, get_zvec_service

from app.services.document_parser import (
    extract_text_from_drive_file,
    detect_project_from_filename,
    get_file_metadata,
    list_drive_files,
)

__all__ = [
    "ZVecOpenAIService",
    "get_zvec_service",
    "extract_text_from_drive_file",
    "detect_project_from_filename",
    "get_file_metadata",
    "list_drive_files",
]
