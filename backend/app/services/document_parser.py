"""
Document Parser Service - Extract text from Google Drive files via API

Uses Google Drive API export and media endpoints to extract text content
without downloading files to local storage.
"""

from typing import Optional, Dict, Any
import aiohttp


# Google Workspace MIME type mappings for text export
GOOGLE_EXPORT_FORMATS = {
    'application/vnd.google-apps.document': 'text/plain',
    'application/vnd.google-apps.spreadsheet': 'text/csv',
    'application/vnd.google-apps.presentation': 'text/plain',
    'application/vnd.google-apps.drawing': 'image/svg+xml',
}

# Supported MIME types for processing
SUPPORTED_MIME_TYPES = {
    'application/pdf',
    'text/plain',
    'text/html',
    'application/vnd.google-apps.document',
    'application/vnd.google-apps.spreadsheet',
    'application/vnd.google-apps.presentation',
}

# Max content size to extract (characters)
MAX_CONTENT_LENGTH = 10000


async def extract_text_from_drive_file(
    file_id: str, 
    access_token: str,
    mime_type: str = 'application/vnd.google-apps.document'
) -> Optional[str]:
    """
    Extract text from Google Drive file using Drive API.
    
    For Google Workspace files: Uses /export endpoint to get text format
    For PDFs: Streams content via ?alt=media and extracts text
    For text files: Streams content directly
    
    No files are saved to disk - everything is processed in memory.
    
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
        
        # Handle PDF files - stream and extract
        elif mime_type == 'application/pdf':
            return await _stream_and_extract_pdf(file_id, access_token)
        
        # Handle plain text files - stream directly
        elif mime_type in ('text/plain', 'text/html'):
            return await _stream_text_file(file_id, access_token)
        
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
    """
    Export Google Workspace file to text format via Drive API.
    
    Uses the /export endpoint which converts Docs/Sheets/etc to text on-the-fly.
    No download to disk - text is returned directly in response.
    """
    export_mime = GOOGLE_EXPORT_FORMATS.get(mime_type, 'text/plain')
    
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}/export"
    params = {'mimeType': export_mime}
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': export_mime
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as resp:
            if resp.status == 200:
                text = await resp.text()
                # Limit content size for embedding
                return text[:MAX_CONTENT_LENGTH] if text else None
            else:
                error_text = await resp.text()
                print(f"Export failed for {file_id}: {resp.status} - {error_text[:200]}")
                return None


async def _stream_and_extract_pdf(
    file_id: str, 
    access_token: str
) -> Optional[str]:
    """
    Stream PDF content from Drive API and extract text in memory.
    
    Uses ?alt=media to get binary content, then extracts text using PyPDF2.
    PDF is processed in memory - never saved to disk.
    """
    import io
    
    # Try PyPDF2 first
    try:
        import PyPDF2
        PYPDF_AVAILABLE = True
    except ImportError:
        PYPDF_AVAILABLE = False
    
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
    params = {'alt': 'media'}
    headers = {'Authorization': f'Bearer {access_token}'}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as resp:
            if resp.status != 200:
                print(f"PDF stream failed: {resp.status}")
                return None
            
            # Read PDF content into memory
            pdf_bytes = await resp.read()
            
            if not PYPDF_AVAILABLE:
                # Fallback: return first 1000 chars as raw text if possible
                try:
                    # Some PDFs have extractable text in the raw bytes
                    text = pdf_bytes.decode('utf-8', errors='ignore')
                    return text[:MAX_CONTENT_LENGTH] if text else None
                except:
                    return None
            
            # Extract text using PyPDF2 in memory
            try:
                pdf_file = io.BytesIO(pdf_bytes)
                reader = PyPDF2.PdfReader(pdf_file)
                
                text_parts = []
                total_chars = 0
                
                # Extract from pages until we hit max length
                for page in reader.pages:
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(page_text)
                            total_chars += len(page_text)
                            if total_chars >= MAX_CONTENT_LENGTH:
                                break
                    except Exception as e:
                        print(f"Error extracting page: {e}")
                        continue
                
                full_text = "\n".join(text_parts)
                return full_text[:MAX_CONTENT_LENGTH] if full_text else None
                
            except Exception as e:
                print(f"PDF parsing error: {e}")
                return None


async def _stream_text_file(
    file_id: str, 
    access_token: str
) -> Optional[str]:
    """
    Stream text file content directly from Drive API.
    
    Uses ?alt=media to get file content as text stream.
    """
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
    params = {'alt': 'media'}
    headers = {'Authorization': f'Bearer {access_token}'}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as resp:
            if resp.status == 200:
                text = await resp.text()
                return text[:MAX_CONTENT_LENGTH] if text else None
            else:
                print(f"Text file stream failed: {resp.status}")
                return None


def detect_project_from_filename(filename: str) -> str:
    """
    Detect project name from filename patterns.
    
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
    
    # Try to extract project from underscore patterns
    if '_' in name:
        parts = name.split('_')
        project = parts[0]
        return _to_title_case(project)
    
    # Try to detect from keywords
    keywords = {
        'safety': 'Safety',
        'invoice': 'Invoices',
        'contract': 'Contracts',
        'report': 'Reports',
        'proposal': 'Proposals',
        'budget': 'Budget',
        'schedule': 'Schedule',
        'drawing': 'Drawings',
    }
    
    name_lower = name.lower().replace('-', ' ').replace('_', ' ')
    for keyword, project in keywords.items():
        if keyword in name_lower:
            return project
    
    # Default
    return "General"


def _to_title_case(text: str) -> str:
    """Convert camelCase or snake_case to Title Case."""
    import re
    # Handle camelCase
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
        Metadata dictionary for ZVec indexing
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


async def list_drive_files(
    access_token: str,
    query: str = "",
    page_size: int = 100
) -> list:
    """
    List files from Google Drive using API.
    
    Args:
        access_token: OAuth token
        query: Search query (e.g., "mimeType='application/pdf'")
        page_size: Number of files to return
    
    Returns:
        List of file metadata dicts
    """
    url = "https://www.googleapis.com/drive/v3/files"
    params = {
        'pageSize': page_size,
        'fields': 'files(id,name,mimeType,size,modifiedTime,webViewLink)',
        'q': query if query else "trashed=false"
    }
    headers = {'Authorization': f'Bearer {access_token}'}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get('files', [])
            else:
                print(f"Failed to list files: {resp.status}")
                return []
