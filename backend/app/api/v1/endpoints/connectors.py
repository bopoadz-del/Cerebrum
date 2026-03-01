import os
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
from app.api.deps import get_current_user, get_current_user_async, get_db
from app.models.integration import IntegrationToken
from app.models.user import User
from app.api.deps import get_async_db

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
    import uuid
    result = await db.execute(
        select(IntegrationToken).where(
            and_(
                IntegrationToken.user_id == uuid.UUID(user_id),
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
    db: AsyncSession = Depends(get_async_db),
) -> GoogleDriveStatusResponse:
    """Check if Google Drive is connected for the current user."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        user_id = str(current_user.id)
        logger.info(f"Checking Drive status for user {user_id}")
        
        token = await get_google_drive_token(db, user_id)
        
        if not token:
            logger.info(f"No Drive token found for user {user_id}")
            return GoogleDriveStatusResponse(
                connected=False,
                email="",
                last_sync="",
            )
        
        # Check if token is expired
        from datetime import datetime, timezone
        is_expired = False
        if token.expiry:
            # Handle both naive and aware datetimes
            expiry = token.expiry
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            is_expired = expiry < datetime.now(timezone.utc)
        
        logger.info(f"Drive token found for user {user_id}, expired={is_expired}")
        
        return GoogleDriveStatusResponse(
            connected=True and not is_expired,
            email=token.account_email or current_user.email or "",
            last_sync=token.updated_at.isoformat() if token.updated_at else "",
        )
    except Exception as e:
        # Log error and return not connected
        logger.error(f"Error in get_google_drive_status: {e}", exc_info=True)
        return GoogleDriveStatusResponse(
            connected=False,
            email="",
            last_sync="",
        )


@router.get(
    "/google-drive/auth",
    summary="Get Google Drive OAuth URL",
)
async def get_google_drive_auth(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
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
    state = str(current_user.id)
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


# OAuth callback endpoint (must be here since google_drive.py router is disabled)
@router.get("/google-drive/callback")
async def google_drive_callback(
    code: str,
    state: str,
):
    """Handle OAuth callback from Google (called by Google, no auth required)."""
    from fastapi.responses import HTMLResponse
    from app.core.config import settings
    from app.db.session import db_manager
    from app.models.integration import IntegrationToken, IntegrationProvider
    from app.models.user import User
    from sqlalchemy import select
    from datetime import datetime, timedelta
    import httpx
    import urllib.parse
    import json
    import uuid
    
    # HTML response helper
    def make_response(success: bool, message: str, code_val: str = "", state_val: str = ""):
        code_js = json.dumps(code_val)
        state_js = json.dumps(state_val)
        error_js = json.dumps(message)
        if success:
            return HTMLResponse(content=f"""
            <!DOCTYPE html>
            <html>
            <head><title>Google Drive Connected</title>
            <script>
                if (window.opener) {{
                    window.opener.postMessage({{
                        type: 'GOOGLE_DRIVE_AUTH_SUCCESS',
                        code: {code_js},
                        state: {state_js}
                    }}, 'https://cerebrum-frontend.onrender.com');
                }}
                setTimeout(() => window.close(), 500);
            </script></head>
            <body><h2>Google Drive Connected!</h2><p>You can close this window.</p></body>
            </html>
            """)
        else:
            return HTMLResponse(content=f"""
            <!DOCTYPE html>
            <html>
            <head><title>Authentication Failed</title>
            <script>
                if (window.opener) {{
                    window.opener.postMessage({{
                        type: 'GOOGLE_DRIVE_AUTH_ERROR',
                        error: {error_js}
                    }}, 'https://cerebrum-frontend.onrender.com');
                }}
                setTimeout(() => window.close(), 3000);
            </script></head>
            <body><h2>Authentication Failed</h2><p>{message}</p></body>
            </html>
            """, status_code=400)
    
    try:
        # URL decode state in case it was encoded
        decoded_state = urllib.parse.unquote(state)
        
        # Extract user_id from state (format: nonce:user_id)
        if ":" in decoded_state:
            user_id_str = decoded_state.split(":")[-1]
        else:
            user_id_str = decoded_state
        
        try:
            user_id = uuid.UUID(user_id_str)
        except ValueError:
            return make_response(False, f"Invalid user ID in state: {user_id_str}")
        
        # Exchange code for tokens
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            token_data = resp.json()
        
        # Get user email from Google
        email = None
        try:
            async with httpx.AsyncClient() as client:
                userinfo = await client.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    headers={"Authorization": f"Bearer {token_data['access_token']}"}
                )
                if userinfo.status_code == 200:
                    email = userinfo.json().get("email")
        except Exception:
            pass  # Email is optional
        
        # Save tokens to database using sync session
        try:
            db_manager.initialize()
            from sqlalchemy.orm import sessionmaker
            Session = sessionmaker(bind=db_manager._sync_engine)
            db = Session()
            
            # Verify user exists
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                db.close()
                return make_response(False, "User not found")
            
            # Check for existing token
            existing = db.query(IntegrationToken).filter(
                IntegrationToken.user_id == user_id,
                IntegrationToken.service == IntegrationProvider.GOOGLE_DRIVE
            ).first()
            
            expires_in = int(token_data.get('expires_in', 3600) or 3600)
            expiry = datetime.utcnow() + timedelta(seconds=expires_in)
            scopes = token_data.get('scope', '') or ''
            
            if existing:
                existing.access_token = token_data['access_token']
                existing.refresh_token = token_data.get('refresh_token') or existing.refresh_token
                existing.scopes = scopes
                existing.expiry = expiry
                existing.client_id = settings.GOOGLE_CLIENT_ID
                existing.client_secret = settings.GOOGLE_CLIENT_SECRET
                existing.is_active = True
                existing.revoked_at = None
                existing.rotation_count = (existing.rotation_count or 0) + 1
                if email:
                    existing.account_email = email
            else:
                token = IntegrationToken(
                    token_id=uuid.uuid4().hex,
                    user_id=user_id,
                    service=IntegrationProvider.GOOGLE_DRIVE,
                    access_token=token_data['access_token'],
                    refresh_token=token_data.get('refresh_token'),
                    token_uri='https://oauth2.googleapis.com/token',
                    client_id=settings.GOOGLE_CLIENT_ID,
                    client_secret=settings.GOOGLE_CLIENT_SECRET,
                    scopes=scopes,
                    expiry=expiry,
                    is_active=True,
                    account_email=email,
                )
                db.add(token)
            
            db.commit()
            db.close()
            
        except Exception as db_err:
            return make_response(False, f"Database error: {str(db_err)}")
        
        # Return success HTML
        return make_response(True, "Success", code, state)
        
    except Exception as e:
        return make_response(False, str(e))


# Also need the /auth/url endpoint that the frontend expects
@router.get("/google-drive/auth/url")
async def get_google_drive_auth_url(
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get Google OAuth URL with proper state."""
    from app.core.config import settings
    import secrets
    
    client_id = settings.GOOGLE_CLIENT_ID
    if not client_id or client_id == "your_client_id_here":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth not configured",
        )
    
    # Create state with user_id for verification
    nonce = secrets.token_urlsafe(16)
    state = f"{nonce}:{current_user.id}"
    
    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={client_id}"
        f"&redirect_uri={settings.GOOGLE_REDIRECT_URI}"
        "&response_type=code"
        "&scope=https://www.googleapis.com/auth/drive.readonly"
        "+https://www.googleapis.com/auth/drive.file"
        "+https://www.googleapis.com/auth/drive.metadata.readonly"
        f"&state={state}"
        "&access_type=offline"
        "&prompt=consent"
    )
    
    return {"auth_url": auth_url, "state": state}

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
    summary="Scan Google Drive for projects",
)
async def scan_google_drive(
    current_user: User = Depends(get_current_user_async),
    db: AsyncSession = Depends(get_async_db),
) -> Dict[str, Any]:
    """Scan Google Drive, detect projects, and return them."""
    import uuid
    from sqlalchemy.orm import Session
    from app.services.drive_project_sync import discover_and_upsert_drive_projects
    
    # Convert async session to sync for the service
    # The service uses sync SQLAlchemy
    from app.db.session import db_manager
    db_manager.initialize()
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(bind=db_manager._sync_engine)
    sync_db = SessionLocal()
    
    try:
        result = discover_and_upsert_drive_projects(
            sync_db,
            uuid.UUID(str(current_user.id)),
            min_score=1.0,  # Lower threshold to catch more folders
            max_root_folders=50,
            index_now=True,
        )
        sync_db.close()
        return result
    except Exception as e:
        sync_db.close()
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")


@router.post("/google-drive/search")
async def search_google_drive(
    query: str,
    project: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> Dict[str, Any]:
    """Search files in Google Drive (placeholder - returns empty results)."""
    # TODO: Implement actual Google Drive search with indexing
    return {
        "query": query,
        "results": [],
        "count": 0,
    }


@router.post("/google-drive/index")
async def index_google_drive(
    project_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> Dict[str, Any]:
    """Trigger indexing of Google Drive files using ZVec."""
    import uuid
    from app.db.session import db_manager
    from app.services.drive_project_sync import discover_and_upsert_drive_projects
    
    db_manager.initialize()
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(bind=db_manager._sync_engine)
    sync_db = SessionLocal()
    
    try:
        # Run discovery and indexing
        result = discover_and_upsert_drive_projects(
            sync_db,
            uuid.UUID(str(current_user.id)),
            min_score=1.0,
            max_root_folders=50,
            index_now=True,  # This triggers ZVec indexing
            max_files_per_project=100,
        )
        sync_db.close()
        return result
    except Exception as e:
        sync_db.close()
        raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")


@router.get("/google-drive/files")
async def list_google_drive_files(
    folder_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> List[Dict[str, Any]]:
    """List files from Google Drive for a specific folder."""
    import uuid
    from app.db.session import db_manager
    from app.services.google_drive_service import GoogleDriveService
    
    db_manager.initialize()
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(bind=db_manager._sync_engine)
    sync_db = SessionLocal()
    
    try:
        svc = GoogleDriveService(sync_db)
        files = await svc.list_files(uuid.UUID(str(current_user.id)), folder_id)
        sync_db.close()
        return files
    except Exception as e:
        sync_db.close()
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


@router.get("/google-drive/projects/{project_id}/files")
async def list_project_files(
    project_id: str,
    current_user: User = Depends(get_current_user_async),
    db: AsyncSession = Depends(get_async_db),
) -> List[Dict[str, Any]]:
    """List files within a specific Google Drive project (folder).
    
    Accepts either the mapping id (id column) or project_id (project_id column).
    """
    import uuid
    import logging
    from sqlalchemy import text
    from app.db.session import db_manager
    from app.services.google_drive_service import GoogleDriveService
    
    logger = logging.getLogger(__name__)
    user_id = uuid.UUID(str(current_user.id))
    
    # Try looking up by project_id first, then by id (mapping id)
    result = await db.execute(
        text("""
            SELECT root_folder_id, root_folder_name 
            FROM google_drive_projects 
            WHERE project_id = :project_id::UUID 
            AND user_id = :user_id
            LIMIT 1
        """).bindparams(project_id=project_id, user_id=user_id)
    )
    row = result.fetchone()
    
    # If not found by project_id, try by id (mapping id)
    if not row:
        result = await db.execute(
            text("""
                SELECT root_folder_id, root_folder_name 
                FROM google_drive_projects 
                WHERE id = :project_id::UUID 
                AND user_id = :user_id
                LIMIT 1
            """).bindparams(project_id=project_id, user_id=user_id)
        )
        row = result.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    
    root_folder_id, root_folder_name = row
    logger.info(f"Listing files for project {project_id}, folder {root_folder_id}, user {user_id}")
    
    # List files from the project's root folder
    db_manager.initialize()
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(bind=db_manager._sync_engine)
    sync_db = SessionLocal()
    
    try:
        svc = GoogleDriveService(sync_db)
        files = await svc.list_files(user_id, root_folder_id)
        sync_db.close()
        return files
    except ValueError as e:
        # Not authenticated error
        sync_db.close()
        logger.error(f"Authentication error listing files: {e}")
        raise HTTPException(status_code=401, detail="Google Drive not authenticated. Please reconnect.")
    except Exception as e:
        sync_db.close()
        logger.error(f"Error listing files: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


@router.post(
    "/google-drive/disconnect",
    summary="Disconnect Google Drive",
)
async def disconnect_google_drive(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> Dict[str, Any]:
    """Disconnect Google Drive and revoke tokens."""
    token = await get_google_drive_token(db, str(current_user.id))
    if token:
        token.is_active = False
        db.commit()
    
    return {
        "success": True,
        "message": "Google Drive disconnected",
    }


# =============================================================================
# Google Drive Smart Projects (DB-backed)
# =============================================================================

@router.post(
    "/google-drive/projects/sync",
    summary="Trigger Smart Project discovery for Google Drive",
)
async def trigger_google_drive_project_sync(
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Enqueue background job to discover Drive-rooted Projects (metadata-only).
    """
    from app.tasks import sync_drive_projects

    task = sync_drive_projects.delay(user_id=str(current_user.id))
    return {"status": "queued", "task_id": task.id}


@router.get(
    "/google-drive/projects",
    response_model=GoogleDriveProjectsResponse,
    summary="List Smart Projects discovered from Google Drive",
)
async def list_google_drive_projects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> GoogleDriveProjectsResponse:
    """
    Returns detected Drive projects from the google_drive_projects table.
    """
    import uuid
    from sqlalchemy import text
    
    user_id = uuid.UUID(str(current_user.id))
    
    # Use raw query with proper bindparams
    result = await db.execute(
        text("""
            SELECT project_id, root_folder_name, indexing_status, updated_at
            FROM google_drive_projects
            WHERE user_id = :user_id
            AND deleted = false
            ORDER BY updated_at DESC
        """).bindparams(user_id=user_id)
    )
    rows = result.fetchall()

    projects: List[GoogleDriveProject] = []
    for row in rows:
        project_id, root_folder_name, indexing_status, updated_at = row
        projects.append(
            GoogleDriveProject(
                id=str(project_id),
                name=root_folder_name,
                file_count=0,
                status=indexing_status or "idle",
                updated_at=updated_at.isoformat() if updated_at else "",
            )
        )

    return GoogleDriveProjectsResponse(projects=projects)


@router.get("/google-drive/debug")
async def debug_google_drive(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> Dict[str, Any]:
    """Debug endpoint to check database state."""
    from sqlalchemy import text
    import traceback
    import uuid
    
    try:
        user_id = uuid.UUID(str(current_user.id))
        
        # Check if table exists
        table_check = await db.execute(
            text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'google_drive_projects')")
        )
        table_exists = table_check.scalar()
        
        if not table_exists:
            return {"error": "google_drive_projects table does not exist"}
        
        # Check all projects (no user filter)
        result_all = await db.execute(
            text("SELECT COUNT(*) FROM google_drive_projects")
        )
        total_projects = result_all.scalar()
        
        # Check projects for this user - use bindparam properly
        result = await db.execute(
            text("SELECT COUNT(*) FROM google_drive_projects WHERE user_id = :user_id").bindparams(user_id=user_id)
        )
        project_count = result.scalar()
        
        # Check integration_tokens
        result2 = await db.execute(
            text("SELECT COUNT(*) FROM integration_tokens WHERE user_id = :user_id AND service = 'google_drive'").bindparams(user_id=user_id)
        )
        token_count = result2.scalar()
        
        # Get ALL projects (for debugging)
        result3 = await db.execute(
            text("SELECT user_id, project_id, root_folder_name, deleted FROM google_drive_projects LIMIT 5")
        )
        rows = result3.fetchall()
        all_projects = [{"user_id": str(r[0]), "project_id": str(r[1]), "root_folder_name": r[2], "deleted": r[3]} for r in rows]
        
        return {
            "table_exists": table_exists,
            "user_id": str(current_user.id),
            "total_projects_in_db": total_projects,
            "project_count_for_user": project_count,
            "token_count": token_count,
            "sample_projects": all_projects,
        }
    except Exception as e:
        return {
            "error": str(e),
            "traceback": traceback.format_exc(),
        }

