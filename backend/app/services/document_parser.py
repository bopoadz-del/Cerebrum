"""
Document Parser Service - Extract text from Google Drive files

Supports PDF, Google Docs, and plain text files from Google Drive.
"""

import io
from typing import Optional, Dict, Any

import aiohttp

# Try to import PyPDF2 for PDF processing
try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False


# MIME type mappings for Google Drive exports
GOOGLE_EXPORT_MIME_TYPES = {
    'application/vnd.google-apps.document': 'text/plain',
    'application/vnd.google-apps.spreadsheet': 'text/csv',
    'application/vnd.google-apps.presentation': 'text/plain',
}

# Supported import MIME types
SUPPORTED_MIME_TYPES = {
    'application/pdf',
    'text/plain',
    'text/html',
    'application/vnd.google-apps.document',
    'application/vnd.google-apps.spreadsheet',
    'application/vnd.google-apps.presentation',
}


async def extract_text_from_drive_file(
    file_id: str, 
    access_token: str,
    mime_type: str = 'application/vnd.google-apps.document'
) -> Optional[str]:
    """
    Download file from Google Drive and extract text content.
    
    Args:
        file_id: Google Drive file ID
        access_token: OAuth access token
        mime_type: MIME type of the file
    
    Returns:
        Extracted text content or None if extraction fails
    """
    try:
        # Handle Google Workspace files (Docs, Sheets, etc.)
        if mime_type.startswith('application/vnd.google-apps.'):
            return await _export_google_workspace_file(file_id, access_token, mime_type)
        
        # Handle PDF files
        elif mime_type == 'application/pdf':
            return await _download_and_extract_pdf(file_id, access_token)
        
        # Handle plain text files
        elif mime_type in ('text/plain', 'text/html'):
            return await _download_text_file(file_id, access_token)
        
        else:
            print(f"Unsupported MIME type: {mime_type}")
            return None
            
    except Exception as e:
        print(f"Text extraction error for file {file_id}: {e}")
        return None


async def _export_google_workspace_file(
    file_id: str, 
    access_token: str,
    mime_type: str
) -> Optional[str]:
    """Export Google Workspace file to text format."""
    export_mime = GOOGLE_EXPORT_MIME_TYPES.get(mime_type, 'text/plain')
    
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}/export"
    params = {'mimeType': export_mime}
    headers = {'Authorization': f'Bearer {access_token}'}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as resp:
            if resp.status == 200:
                text = await resp.text()
                # Limit to 10k chars for embedding
                return text[:10000] if text else None
            else:
                error_text = await resp.text()
                print(f"Export failed for {file_id}: {resp.status} - {error_text}")
                return None


async def _download_and_extract_pdf(
    file_id: str, 
    access_token: str
) -> Optional[str]:
    """Download PDF and extract text using PyPDF2."""
    if not PYPDF2_AVAILABLE:
        print("PyPDF2 not available, cannot extract PDF text")
        return None
    
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
    headers = {'Authorization': f'Bearer {access_token}'}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                print(f"PDF download failed: {resp.status}")
                return None
            
            try:
                pdf_content = await resp.read()
                pdf_file = io.BytesIO(pdf_content)
                reader = PyPDF2.PdfReader(pdf_file)
                
                text = ""
                # Extract from first 10 pages max
                for i, page in enumerate(reader.pages):
                    if i >= 10:
                        break
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                    except Exception as e:
                        print(f"Error extracting page {i}: {e}")
                
                return text[:10000] if text else None
                
            except Exception as e:
                print(f"PDF parsing error: {e}")
                return None


async def _download_text_file(
    file_id: str, 
    access_token: str
) -> Optional[str]:
    """Download plain text file content."""
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
    headers = {'Authorization': f'Bearer {access_token}'}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                text = await resp.text()
                return text[:10000] if text else None
            else:
                print(f"Text file download failed: {resp.status}")
                return None


def detect_project_from_filename(filename: str) -> str:
    """
    Detect project name from filename.
    
    Examples:
        "ProjectA_invoice_2024.pdf" -> "ProjectA"
        "Safety_Report_Q4.pdf" -> "Safety Report Q4"
        "document.txt" -> "General"
    
    Args:
        filename: Name of the file
    
    Returns:
        Detected project name
    """
    # Remove extension
    name = filename.rsplit('.', 1)[0] if '.' in filename else filename
    
    # Try to extract project from underscore/camelCase patterns
    if '_' in name:
        # First part before underscore is likely project
        parts = name.split('_')
        project = parts[0]
        # Convert camelCase to Title Case if needed
        return _to_title_case(project)
    
    # If no underscore, try to detect from keywords
    keywords = {
        'safety': 'Safety',
        'invoice': 'Invoices',
        'contract': 'Contracts',
        'report': 'Reports',
        'proposal': 'Proposals',
    }
    
    name_lower = name.lower()
    for keyword, project in keywords.items():
        if keyword in name_lower:
            return project
    
    # Default
    return "General"


def _to_title_case(text: str) -> str:
    """Convert camelCase or snake_case to Title Case."""
    # Handle camelCase
    import re
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1 \2', text)
    s2 = re.sub('([a-z0-9])([A-Z])', r'\1 \2', s1)
    return s2.replace('_', ' ').replace('-', ' ').title()


def get_file_metadata(
    file_id: str,
    filename: str,
    mime_type: str,
    user_id: str,
    content_preview: str = ""
) -> Dict[str, Any]:
    """
    Build metadata dictionary for a file.
    
    Args:
        file_id: Google Drive file ID
        filename: File name
        mime_type: MIME type
        user_id: User ID
        content_preview: Preview of content (first 500 chars)
    
    Returns:
        Metadata dictionary
    """
    project = detect_project_from_filename(filename)
    
    return {
        'name': filename,
        'project': project,
        'type': mime_type,
        'drive_id': file_id,
        'user_id': user_id,
        'content_preview': content_preview[:500]
    }
