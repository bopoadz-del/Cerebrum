"""
Connectors API Endpoints

Provides status and management for external service connectors with stub support.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors import get_connector_status, list_connectors, get_connector
from app.api.deps import get_current_user, get_db
from app.models.integration import IntegrationToken
from app.models.user import User

router = APIRouter(prefix="/connectors", tags=["Connectors"])


# =============================================================================
# Response Schemas
# =============================================================================

class ConnectorStatus(BaseModel):
    """Individual connector status."""
    stub_available: bool
    production_available: bool
    using_stub: bool
    mode: str


class ConnectorsStatusResponse(BaseModel):
    """All connectors status response."""
    connectors: Dict[str, ConnectorStatus]
    total: int


class ConnectorInfo(BaseModel):
    """Connector information."""
    name: str
    service_name: str
    version: str
    status: str
    healthy: bool


class ConnectorHealthResponse(BaseModel):
    """Connector health check response."""
    service: str
    status: str
    healthy: bool
    version: str
    calls: int
    last_called: str


# =============================================================================
# API Endpoints
# =============================================================================

@router.get(
    "/status",
    response_model=ConnectorsStatusResponse,
    summary="Get connectors status",
    description="Get status of all registered connectors (stub vs production).",
)
async def get_connectors_status(
    current_user = Depends(get_current_user),
) -> ConnectorsStatusResponse:
    """
    Get status of all external service connectors.
    
    Returns information about which connectors are using stubs vs production.
    """
    status_dict = get_connector_status()
    
    # Convert to Pydantic models
    connectors = {
        name: ConnectorStatus(**info)
        for name, info in status_dict.items()
    }
    
    return ConnectorsStatusResponse(
        connectors=connectors,
        total=len(connectors),
    )


@router.get(
    "/list",
    response_model=List[str],
    summary="List available connectors",
    description="Get list of all registered connector names.",
)
async def list_available_connectors(
    current_user = Depends(get_current_user),
) -> List[str]:
    """List all available connector names."""
    return list_connectors()


@router.get(
    "/{connector_name}/health",
    response_model=ConnectorHealthResponse,
    summary="Get connector health",
    description="Get health status of a specific connector.",
)
async def get_connector_health(
    connector_name: str,
    current_user = Depends(get_current_user),
) -> ConnectorHealthResponse:
    """
    Get health check for a specific connector.
    """
    try:
        connector = get_connector(connector_name)
        health = connector.health_check()
        return ConnectorHealthResponse(**health)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connector not found: {connector_name}",
        )


@router.get(
    "/{connector_name}/info",
    response_model=ConnectorInfo,
    summary="Get connector info",
    description="Get detailed information about a connector.",
)
async def get_connector_info(
    connector_name: str,
    current_user = Depends(get_current_user),
) -> ConnectorInfo:
    """
    Get detailed information about a connector.
    """
    try:
        connector = get_connector(connector_name)
        info = connector.get_info()
        return ConnectorInfo(
            name=connector_name,
            service_name=info.get("service", connector_name),
            version=info.get("version", "unknown"),
            status=info.get("status", "unknown"),
            healthy=info.get("healthy", True),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connector not found: {connector_name}",
        )


@router.post(
    "/{connector_name}/test",
    summary="Test connector",
    description="Test a connector by calling a simple operation.",
)
async def test_connector(
    connector_name: str,
    current_user = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Test a connector by calling a basic operation.
    
    Returns the result of the test call.
    """
    try:
        connector = get_connector(connector_name)
        
        # Try to call a test method based on connector type
        if hasattr(connector, 'get_info'):
            result = connector.get_info()
        elif hasattr(connector, 'health_check'):
            result = connector.health_check()
        else:
            result = {"status": "stubbed", "message": "No test method available"}
        
        return {
            "connector": connector_name,
            "test_result": result,
            "success": True,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Connector test failed: {str(e)}",
        )


# =============================================================================
# Google Drive Specific Endpoints
# =============================================================================

class GoogleDriveStatusResponse(BaseModel):
    """Google Drive connection status."""
    connected: bool
    email: str = ""
    last_sync: str = ""


class GoogleDriveProject(BaseModel):
    """Project discovered from Google Drive."""
    id: str
    name: str
    file_count: int
    status: str
    updated_at: str


class GoogleDriveProjectsResponse(BaseModel):
    """List of projects from Google Drive."""
    projects: List[GoogleDriveProject]


class ZVecSearchResponse(BaseModel):
    """Semantic search response."""
    query: str
    results: List[Dict[str, Any]]
    count: int


class ZVecScanResponse(BaseModel):
    """ZVec scan/index response."""
    files_scanned: int
    indexed: int
    message: str


async def get_google_drive_token(
    db: AsyncSession,
    user_id: str
) -> Optional[IntegrationToken]:
    """Get active Google Drive token for user."""
    result = await db.execute(
        select(IntegrationToken).where(
            and_(
                IntegrationToken.user_id == user_id,
                IntegrationToken.service == "google_drive",
                IntegrationToken.is_active == True
            )
        )
    )
    return result.scalar_one_or_none()


@router.get(
    "/google-drive/status",
    response_model=GoogleDriveStatusResponse,
    summary="Get Google Drive connection status",
)
async def get_google_drive_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GoogleDriveStatusResponse:
    """Check if Google Drive is connected for the current user."""
    token = await get_google_drive_token(db, str(current_user.id))
    
    if not token:
        return GoogleDriveStatusResponse(
            connected=False,
            email="",
            last_sync="",
        )
    
    return GoogleDriveStatusResponse(
        connected=True,
        email=current_user.email,
        last_sync=token.updated_at.isoformat() if token.updated_at else "",
    )


@router.get(
    "/google-drive/auth",
    summary="Get Google Drive OAuth URL",
)
async def get_google_drive_auth(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get Google OAuth URL for connecting Drive."""
    from app.core.config import settings
    import secrets
    
    client_id = settings.GOOGLE_CLIENT_ID
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    
    if not client_id or client_id == "your_client_id_here":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth not configured",
        )
    
    state = secrets.token_urlsafe(32)
    
    # Store state in session or database for verification later
    # For now, we'll use a simple cache approach
    
    # Build Google OAuth URL
    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        "&response_type=code"
        "&scope=https://www.googleapis.com/auth/drive.readonly"
        "+https://www.googleapis.com/auth/drive.file"
        "+https://www.googleapis.com/auth/drive.metadata.readonly"
        f"&state={state}"
        "&access_type=offline"
        "&prompt=consent"
    )
    
    return {
        "auth_url": auth_url,
        "state": state,
    }


# Note: OAuth callback is handled in google_drive.py (no auth required for Google redirect)
# DO NOT add a callback endpoint here - it will conflict with google_drive.py

# Mock projects for now - will be replaced with actual Drive scanning
MOCK_PROJECTS = [
    GoogleDriveProject(
        id="proj_1",
        name="Q4 Financial Analysis",
        file_count=12,
        status="active",
        updated_at="2024-01-15T10:30:00Z",
    ),
    GoogleDriveProject(
        id="proj_2",
        name="Construction Project A",
        file_count=45,
        status="active",
        updated_at="2024-01-14T14:22:00Z",
    ),
    GoogleDriveProject(
        id="proj_3",
        name="Marketing Campaign",
        file_count=8,
        status="draft",
        updated_at="2024-01-13T09:15:00Z",
    ),
]


@router.post(
    "/google-drive/scan",
    response_model=GoogleDriveProjectsResponse,
    summary="Scan Google Drive for projects",
)
async def scan_google_drive(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GoogleDriveProjectsResponse:
    """Scan user's Google Drive and discover projects."""
    # Check if connected
    token = await get_google_drive_token(db, str(current_user.id))
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google Drive not connected",
        )
    
    # TODO: Implement actual Drive scanning using Google Drive API
    # For now, return mock projects
    return GoogleDriveProjectsResponse(projects=MOCK_PROJECTS)


@router.get(
    "/google-drive/files",
    summary="List Google Drive files",
)
async def list_google_drive_files(
    query: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    List files from user's Google Drive via API (no download).
    """
    token = await get_google_drive_token(db, str(current_user.id))
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google Drive not connected",
        )
    
    from app.services.document_parser import list_drive_files
    
    try:
        # Build query for supported file types
        mime_query = " or ".join([
            "mimeType='application/pdf'",
            "mimeType='text/plain'",
            "mimeType='application/vnd.google-apps.document'",
            "mimeType='application/vnd.google-apps.spreadsheet'"
        ])
        drive_query = f"({mime_query}) and trashed=false"
        if query:
            drive_query += f" and name contains '{query}'"
        
        files = await list_drive_files(token.access_token, query=drive_query)
        
        return {
            "files": files,
            "count": len(files)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list files: {str(e)}"
        )


@router.post(
    "/google-drive/index",
    response_model=ZVecScanResponse,
    summary="Index Google Drive files into ZVec for semantic search",
)
async def index_google_drive_files(
    file_ids: Optional[List[str]] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ZVecScanResponse:
    """
    Scan Drive files via API, extract text in memory, and index into ZVec.
    No files are downloaded to disk - processed entirely via Drive API.
    """
    token = await get_google_drive_token(db, str(current_user.id))
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google Drive not connected",
        )
    
    from app.services.zvec_service import get_zvec_service
    from app.services.document_parser import (
        extract_text_from_drive_file,
        detect_project_from_filename,
        list_drive_files
    )
    from app.models.document import Document
    
    try:
        zvec = get_zvec_service()
        
        if not zvec.is_ready():
            return ZVecScanResponse(
                files_scanned=0,
                indexed=0,
                message="ZVec service not ready - embedding model not available"
            )
        
        # If no file_ids provided, list files from Drive
        if not file_ids:
            mime_query = " or ".join([
                "mimeType='application/pdf'",
                "mimeType='text/plain'",
                "mimeType='application/vnd.google-apps.document'"
            ])
            files = await list_drive_files(
                token.access_token, 
                query=f"({mime_query}) and trashed=false",
                page_size=10
            )
            file_ids = [f['id'] for f in files]
        
        indexed_count = 0
        scanned_count = 0
        
        for file_id in file_ids[:10]:  # Process max 10 files per request
            try:
                # Check if already indexed
                from sqlalchemy import select
                result = await db.execute(
                    select(Document).where(
                        Document.drive_id == file_id,
                        Document.user_id == current_user.id
                    )
                )
                existing = result.scalar_one_or_none()
                
                if existing and existing.status == "indexed":
                    continue
                
                # Get file info (we need mime_type)
                files = await list_drive_files(
                    token.access_token,
                    query=f"id='{file_id}'"
                )
                if not files:
                    continue
                    
                file_info = files[0]
                scanned_count += 1
                
                # Extract text via Drive API (in memory, no download)
                text = await extract_text_from_drive_file(
                    file_id,
                    token.access_token,
                    file_info.get('mimeType', 'application/pdf')
                )
                
                if not text or len(text) < 100:
                    continue
                
                # Index in ZVec
                project = detect_project_from_filename(file_info['name'])
                doc_id = f"drive_{file_id}"
                metadata = {
                    'name': file_info['name'],
                    'project': project,
                    'type': file_info.get('mimeType'),
                    'drive_id': file_id,
                    'user_id': str(current_user.id),
                    'content_preview': text[:500]
                }
                
                success = zvec.add_document(doc_id, text, metadata)
                
                if success:
                    # Save to SQL
                    if existing:
                        existing.content = text[:2000]
                        existing.project_name = project
                        existing.status = "indexed"
                        existing.updated_at = datetime.now(timezone.utc)
                    else:
                        from uuid import uuid4
                        doc = Document(
                            id=uuid4(),
                            drive_id=file_id,
                            filename=file_info['name'],
                            content=text[:2000],
                            project_name=project,
                            mime_type=file_info.get('mimeType'),
                            status="indexed",
                            user_id=current_user.id
                        )
                        db.add(doc)
                    
                    indexed_count += 1
                    
            except Exception as e:
                print(f"Failed to index file {file_id}: {e}")
                continue
        
        await db.commit()
        
        return ZVecScanResponse(
            files_scanned=scanned_count,
            indexed=indexed_count,
            message=f"Indexed {indexed_count} documents into ZVec via Drive API (no downloads)"
        )
        
    except Exception as e:
        return ZVecScanResponse(
            files_scanned=0,
            indexed=0,
            message=f"Indexing failed: {str(e)}"
        )


@router.post(
    "/google-drive/search",
    response_model=ZVecSearchResponse,
    summary="Semantic search across Drive files using ZVec",
)
async def semantic_search_drive(
    query: str,
    project: Optional[str] = None,
    top_k: int = 5,
    current_user: User = Depends(get_current_user),
) -> ZVecSearchResponse:
    """
    Semantic search across indexed Drive files using ZVec.
    Works offline - no cloud vector DB needed.
    
    Examples:
        - query="safety violations" → Finds safety reports
        - query="invoice rebar" → Finds invoices with rebar materials
    """
    from app.services.zvec_service import get_zvec_service
    
    try:
        # Get ZVec service
        zvec = get_zvec_service()
        
        if not zvec.is_ready():
            return ZVecSearchResponse(
                query=query,
                results=[],
                count=0
            )
        
        # Perform semantic search
        results = zvec.search_similar(
            query=query,
            top_k=top_k,
            score_threshold=0.3  # Filter low-quality matches
        )
        
        # Filter by project if specified
        if project:
            results = [
                r for r in results 
                if r.get('metadata', {}).get('project') == project
            ]
        
        return ZVecSearchResponse(
            query=query,
            results=results,
            count=len(results)
        )
        
    except Exception as e:
        print(f"Search error: {e}")
        return ZVecSearchResponse(
            query=query,
            results=[],
            count=0
        )


@router.get(
    "/google-drive/zvec-stats",
    summary="Get ZVec database statistics",
)
async def get_zvec_stats(
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get statistics about the ZVec vector database."""
    from app.services.zvec_service import get_zvec_service
    
    try:
        zvec = get_zvec_service()
        stats = zvec.get_stats()
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.get(
    "/google-drive/projects",
    response_model=GoogleDriveProjectsResponse,
    summary="Get cached Google Drive projects",
)
async def get_google_drive_projects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GoogleDriveProjectsResponse:
    """Get list of projects from Google Drive (cached)."""
    # Check if connected
    token = await get_google_drive_token(db, str(current_user.id))
    if not token:
        return GoogleDriveProjectsResponse(projects=[])
    
    # TODO: Return cached projects from database
    # For now, return mock data
    return GoogleDriveProjectsResponse(projects=MOCK_PROJECTS)


@router.post(
    "/google-drive/disconnect",
    summary="Disconnect Google Drive",
)
async def disconnect_google_drive(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Disconnect Google Drive and revoke tokens."""
    token = await get_google_drive_token(db, str(current_user.id))
    if token:
        token.is_active = False
        await db.commit()
    
    return {
        "success": True,
        "message": "Google Drive disconnected",
    }
