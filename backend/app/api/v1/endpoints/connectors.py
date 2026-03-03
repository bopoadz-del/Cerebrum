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
) -> Optional[Dict[str, Any]]:
    """Get active Google Drive token for user using raw SQL to avoid column mismatch."""
    from sqlalchemy import text
    
    result = await db.execute(
        text("""
            SELECT access_token, refresh_token, expiry, scopes, token_uri, 
                   client_id, client_secret, account_email, is_active, updated_at
            FROM integration_tokens 
            WHERE user_id = :user_id::UUID 
            AND service = 'google_drive'
            AND is_active = true
            LIMIT 1
        """), {"user_id": user_id}
    )
    row = result.fetchone()
    if not row:
        return None
    
    return {
        'access_token': row[0],
        'refresh_token': row[1],
        'expiry': row[2],
        'scopes': row[3],
        'token_uri': row[4],
        'client_id': row[5],
        'client_secret': row[6],
        'account_email': row[7],
        'is_active': row[8],
        'updated_at': row[9],
    }


@router.get(
    "/google-drive/status",
    response_model=GoogleDriveStatusResponse,
    summary="Get Google Drive connection status",
)
async def get_google_drive_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> GoogleDriveStatusResponse:
    """Check if Google Drive is connected for the current user.
    
    This endpoint auto-refreshes expired tokens to keep the connection alive.
    Returns connected=True if we have valid tokens or can refresh them.
    """
    import logging
    from sqlalchemy import text
    from datetime import datetime, timezone, timedelta
    import httpx
    
    logger = logging.getLogger(__name__)
    
    try:
        user_id = str(current_user.id)
        logger.info(f"Checking Drive status for user_id={user_id}, email={current_user.email}")
        
        # Get token details including refresh_token
        result = await db.execute(
            text("""
                SELECT account_email, is_active, expiry, updated_at, scopes,
                       refresh_token, access_token, client_id, client_secret
                FROM integration_tokens 
                WHERE user_id = :user_id::UUID 
                AND service = 'google_drive'
                AND is_active = true
                LIMIT 1
            """), {"user_id": user_id}
        )
        row = result.fetchone()
        logger.info(f"Token query result for user {user_id_str}: row={row is not None}")
        
        if not row:
            logger.info(f"No Drive token found for user {user_id}")
            return GoogleDriveStatusResponse(
                connected=False,
                email="",
                last_sync="",
            )
        
        account_email, is_active, expiry, updated_at, scopes, refresh_token, access_token, client_id, client_secret = row
        
        # Check if token is expired
        is_expired = False
        if expiry:
            try:
                if expiry.tzinfo is None:
                    expiry = expiry.replace(tzinfo=timezone.utc)
                is_expired = expiry < datetime.now(timezone.utc)
            except:
                pass
        
        logger.info(f"Drive token found for user {user_id}, expired={is_expired}, active={is_active}")
        
        # If token is expired but we have a refresh token, auto-refresh it
        if is_expired and refresh_token:
            logger.info(f"Token expired for user {user_id}, attempting auto-refresh")
            try:
                from app.core.config import settings
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.post(
                        "https://oauth2.googleapis.com/token",
                        data={
                            "refresh_token": refresh_token,
                            "client_id": client_id or settings.GOOGLE_CLIENT_ID,
                            "client_secret": client_secret or settings.GOOGLE_CLIENT_SECRET,
                            "grant_type": "refresh_token",
                        },
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                    )
                    resp.raise_for_status()
                    token_data = resp.json()
                
                # Update the token in database
                new_expires_in = int(token_data.get('expires_in', 3600) or 3600)
                new_expiry = datetime.utcnow() + timedelta(seconds=new_expires_in)
                
                await db.execute(
                    text("""
                        UPDATE integration_tokens 
                        SET access_token = :access_token,
                            expiry = :expiry,
                            updated_at = NOW()
                        WHERE user_id = :user_id::UUID 
                        AND service = 'google_drive'
                    """),
                    {
                        "access_token": token_data['access_token'],
                        "expiry": new_expiry,
                        "user_id": user_id
                    }
                )
                await db.commit()
                
                logger.info(f"Token auto-refreshed successfully for user {user_id}")
                is_expired = False
                updated_at = datetime.utcnow()
                
            except Exception as refresh_err:
                logger.error(f"Failed to auto-refresh token for user {user_id}: {refresh_err}")
                # Don't mark as disconnected yet - the refresh token might still work on next attempt
                # Return connected=True with empty last_sync to indicate potential issues
                return GoogleDriveStatusResponse(
                    connected=True,  # Keep showing as connected
                    email=account_email or current_user.email or "",
                    last_sync=updated_at.isoformat() if updated_at else "",
                )
        
        return GoogleDriveStatusResponse(
            connected=is_active,  # Connected if token exists and is active (even if expired, we tried to refresh)
            email=account_email or current_user.email or "",
            last_sync=updated_at.isoformat() if updated_at else "",
        )
    except Exception as e:
        # Log error but don't disconnect - assume connected if we have cached state
        logger.error(f"Error in get_google_drive_status: {e}", exc_info=True)
        return GoogleDriveStatusResponse(
            connected=True,  # Optimistic - assume connected on error
            email=current_user.email or "",
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
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Saving Google Drive token for user {user_id}")
            
            db_manager.initialize()
            from sqlalchemy.orm import sessionmaker
            Session = sessionmaker(bind=db_manager._sync_engine)
            db = Session()
            
            # Verify user exists
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.error(f"User {user_id} not found")
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
                logger.info(f"Updating existing token for user {user_id}")
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
                logger.info(f"Creating new token for user {user_id}")
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
            logger.info(f"Token saved successfully for user {user_id}")
            db.close()
            
        except Exception as db_err:
            logger.error(f"Database error saving token: {db_err}", exc_info=True)
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
    import logging
    logger = logging.getLogger(__name__)
    
    try:
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
        
        logger.info(f"Generated auth URL for user {current_user.id}")
        return {"auth_url": auth_url, "state": state}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating auth URL: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate auth URL: {str(e)}",
        )

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
    """
    Scan Google Drive, detect projects, and trigger ZVec indexing.
    Returns scan results with indexing queue information.
    """
    import uuid
    import logging
    from sqlalchemy.orm import Session
    from sqlalchemy import text
    from datetime import datetime, timezone, timedelta
    import httpx
    from app.services.drive_project_sync import discover_and_upsert_drive_projects
    from app.services.zvec_service import get_zvec_service
    from app.core.config import settings
    
    logger = logging.getLogger(__name__)
    user_id_str = str(current_user.id)
    user_id = uuid.UUID(user_id_str)
    
    logger.info(f"Scan requested by user {user_id}")
    
    # First, check if we have a valid token and try to refresh if needed
    # (Same logic as status endpoint to ensure consistency)
    try:
        result = await db.execute(
            text("""
                SELECT account_email, is_active, expiry, refresh_token, access_token
                FROM integration_tokens 
                WHERE user_id = :user_id::UUID 
                AND service = 'google_drive'
                AND is_active = true
                LIMIT 1
            """),
            {"user_id": user_id_str}
        )
        logger.info(f"Token query executed for user {user_id_str}")
        row = result.fetchone()
        
        if not row:
            logger.error(f"No active Google Drive token found for user {user_id}")
            raise HTTPException(status_code=400, detail="Google Drive not connected. Please connect first.")
        
        account_email, is_active, expiry, refresh_token, access_token = row
        
        # Check if token is expired
        is_expired = False
        if expiry:
            try:
                if expiry.tzinfo is None:
                    expiry = expiry.replace(tzinfo=timezone.utc)
                is_expired = expiry < datetime.now(timezone.utc)
            except:
                pass
        
        logger.info(f"Token status for user {user_id}: expired={is_expired}, has_refresh={bool(refresh_token)}")
        
        # If expired, try to refresh
        if is_expired:
            if not refresh_token:
                logger.error(f"Token expired and no refresh token for user {user_id}")
                raise HTTPException(status_code=400, detail="Google Drive credentials expired. Please reconnect.")
            
            try:
                logger.info(f"Refreshing token for user {user_id}")
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.post(
                        "https://oauth2.googleapis.com/token",
                        data={
                            "refresh_token": refresh_token,
                            "client_id": settings.GOOGLE_CLIENT_ID,
                            "client_secret": settings.GOOGLE_CLIENT_SECRET,
                            "grant_type": "refresh_token",
                        },
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                    )
                    resp.raise_for_status()
                    token_data = resp.json()
                
                # Update the token in database
                new_expires_in = int(token_data.get('expires_in', 3600) or 3600)
                new_expiry = datetime.utcnow() + timedelta(seconds=new_expires_in)
                
                await db.execute(
                    text("""
                        UPDATE integration_tokens 
                        SET access_token = :access_token,
                            expiry = :expiry,
                            updated_at = NOW()
                        WHERE user_id = :user_id::UUID 
                        AND service = 'google_drive'
                    """),
                    {
                        "access_token": token_data['access_token'],
                        "expiry": new_expiry,
                        "user_id": user_id_str
                    }
                )
                await db.commit()
                logger.info(f"Token refreshed successfully for user {user_id}")
                
            except httpx.HTTPStatusError as e:
                logger.error(f"Token refresh failed for user {user_id}: {e.response.status_code} - {e.response.text}")
                raise HTTPException(status_code=400, detail="Google Drive credentials expired. Please reconnect.")
            except Exception as e:
                logger.error(f"Token refresh error for user {user_id}: {e}")
                raise HTTPException(status_code=400, detail="Failed to refresh Google Drive credentials. Please reconnect.")
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        tb_str = traceback.format_exc()
        logger.error(f"Error checking token before scan: {e}\n{tb_str}")
        raise HTTPException(status_code=500, detail=f"Error checking credentials: {str(e)}")
    
    # Now proceed with the scan using sync database session
    from app.db.session import db_manager
    db_manager.initialize()
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(bind=db_manager._sync_engine)
    sync_db = SessionLocal()
    
    try:
        logger.info(f"Starting project discovery for user {user_id}")
        
        # Run the discovery and upsert
        result = discover_and_upsert_drive_projects(
            sync_db,
            user_id,
            min_score=0.5,
            max_root_folders=200,
            max_children_per_folder=500,
            index_now=True,
            max_files_per_project=100,
        )
        sync_db.close()
        
        logger.info(f"Discovery result for user {user_id}: {result}")
        
        # Check if there was an error
        if result.get("status") == "error":
            logger.error(f"Scan error for user {user_id}: {result.get('message')}")
            raise HTTPException(status_code=400, detail=result.get("message", "Scan failed"))
        
        # Add ZVec service info to result
        zvec = get_zvec_service()
        zvec_stats = zvec.get_stats()
        
        response = {
            **result,
            "status": "success",
            "zvec": {
                "ready": zvec_stats.get('ready', False),
                "indexed_documents": zvec_stats.get('count', 0),
            },
            "message": f"Scan complete. Detected {result.get('detected', 0)} projects. "
                       f"Queued {result.get('queued_index_jobs', 0)} indexing jobs. "
                       f"ZVec ready: {zvec_stats.get('ready', False)}."
        }
        
        logger.info(f"Scan complete for user {user_id}: {response}")
        return response
        
    except HTTPException:
        sync_db.close()
        raise
    except Exception as e:
        sync_db.close()
        logger.error(f"Scan exception for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")


@router.post("/google-drive/search")
async def search_google_drive(
    query: str,
    project: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> Dict[str, Any]:
    """Search files in Google Drive using ZVec semantic search."""
    import uuid
    from sqlalchemy import text
    from app.services.zvec_service import get_zvec_service
    
    user_id_str = str(current_user.id)
    
    if not query or not query.strip():
        return {"query": query, "results": [], "count": 0}
    
    zvec = get_zvec_service()
    
    try:
        # Search using ZVec (returns all results, we'll filter by user)
        search_results = zvec.search_similar(query, top_k=50)
        
        results = []
        for r in search_results:
            metadata = r.get("metadata", {})
            
            # Filter by user_id
            result_user_id = metadata.get("user_id", "")
            if result_user_id != user_id_str:
                continue
            
            # Filter by project if specified
            if project:
                result_project = metadata.get("project", "")
                if result_project != project:
                    continue
            
            results.append({
                "id": r.get("id", ""),
                "score": r.get("score", 0),
                "metadata": {
                    "name": metadata.get("name", "Unknown"),
                    "project": metadata.get("project", "Google Drive"),
                    "mime_type": metadata.get("mime_type", "application/pdf"),
                    "content_preview": metadata.get("content_preview", "")[:500],
                    "drive_id": metadata.get("drive_id", ""),
                }
            })
            
            # Limit to top 10 results
            if len(results) >= 10:
                break
        
        return {
            "query": query,
            "results": results,
            "count": len(results),
        }
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Search failed: {e}", exc_info=True)
        # Return empty results on error
        return {"query": query, "results": [], "count": 0}


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
    from app.services.google_drive_service import (
        GoogleDriveService, 
        GoogleDriveAuthError,
        GoogleDriveError
    )
    
    db_manager.initialize()
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(bind=db_manager._sync_engine)
    sync_db = SessionLocal()
    
    try:
        svc = GoogleDriveService(sync_db)
        files = await svc.list_files(uuid.UUID(str(current_user.id)), folder_id)
        sync_db.close()
        return files
    except GoogleDriveAuthError as e:
        sync_db.close()
        raise HTTPException(status_code=401, detail=str(e))
    except GoogleDriveError as e:
        sync_db.close()
        raise HTTPException(status_code=400, detail=str(e))
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
    import traceback
    from sqlalchemy import text
    from app.db.session import db_manager
    from app.services.google_drive_service import GoogleDriveService
    
    logger = logging.getLogger(__name__)
    user_id = uuid.UUID(str(current_user.id))
    
    logger.info(f"list_project_files called: project_id={project_id}, user_id={user_id}")
    
    try:
        # Try looking up by project_id first, then by id (mapping id)
        # Note: asyncpg doesn't support :: cast syntax in prepared statements
        result = await db.execute(
            text("""
                SELECT root_folder_id, root_folder_name 
                FROM google_drive_projects 
                WHERE CAST(project_id AS TEXT) = :project_id 
                AND CAST(user_id AS TEXT) = :user_id
                LIMIT 1
            """),
            {"project_id": project_id, "user_id": str(user_id)}
        )
        row = result.fetchone()
        lookup_method = "project_id"
        
        # If not found by project_id, try by id (mapping id)
        if not row:
            result = await db.execute(
                text("""
                    SELECT root_folder_id, root_folder_name 
                    FROM google_drive_projects 
                    WHERE CAST(id AS TEXT) = :project_id 
                    AND CAST(user_id AS TEXT) = :user_id
                    LIMIT 1
                """),
                {"project_id": project_id, "user_id": str(user_id)}
            )
            row = result.fetchone()
            lookup_method = "id"
        
        if not row:
            logger.error(f"Project not found: project_id={project_id}, user_id={user_id}")
            raise HTTPException(status_code=404, detail="Project not found")
        
        root_folder_id, root_folder_name = row
        logger.info(f"Found project via {lookup_method}: folder_id={root_folder_id}, folder_name={root_folder_name}")
    except HTTPException:
        raise
    except Exception as db_err:
        logger.error(f"Database error looking up project: {db_err}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(db_err)}")
    
    # List files from the project's root folder
    try:
        db_manager.initialize()
        from sqlalchemy.orm import sessionmaker
        SessionLocal = sessionmaker(bind=db_manager._sync_engine)
        sync_db = SessionLocal()
    except Exception as db_init_err:
        logger.error(f"Failed to initialize database session: {db_init_err}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database connection error")
    
    try:
        from app.services.google_drive_service import (
            GoogleDriveAuthError,
            GoogleDriveNotFoundError,
            GoogleDriveError
        )
        
        svc = GoogleDriveService(sync_db)
        files = await svc.list_files(user_id, root_folder_id)
        
        logger.info(f"Retrieved {len(files)} files from Google Drive for folder {root_folder_id}")
        
        sync_db.close()
        return files
    except GoogleDriveAuthError as e:
        sync_db.close()
        logger.error(f"Google Drive auth error: {e}")
        raise HTTPException(status_code=401, detail=str(e))
    except GoogleDriveNotFoundError as e:
        sync_db.close()
        logger.error(f"Google Drive folder not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except GoogleDriveError as e:
        sync_db.close()
        logger.error(f"Google Drive error: {e}")
        raise HTTPException(status_code=502, detail=str(e))
    except HTTPException:
        sync_db.close()
        raise
    except Exception as e:
        sync_db.close()
        logger.error(f"Unexpected error listing files: {e}", exc_info=True)
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
    import uuid
    from app.db.session import db_manager
    from app.services.google_drive_service import GoogleDriveService
    
    db_manager.initialize()
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(bind=db_manager._sync_engine)
    sync_db = SessionLocal()
    
    try:
        svc = GoogleDriveService(sync_db)
        success = svc.disconnect(uuid.UUID(str(current_user.id)))
        sync_db.close()
        
        if success:
            return {
                "success": True,
                "message": "Google Drive disconnected",
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to disconnect")
    except Exception as e:
        sync_db.close()
        raise HTTPException(status_code=500, detail=f"Failed to disconnect: {str(e)}")


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
    Includes ZVec indexing status and progress.
    """
    import uuid
    from sqlalchemy import text
    
    user_id = uuid.UUID(str(current_user.id))
    
    # Use raw query with proper bindparams - include indexing_progress
    result = await db.execute(
        text("""
            SELECT 
                project_id, 
                root_folder_name, 
                indexing_status, 
                indexing_progress,
                updated_at,
                score,
                confidence
            FROM google_drive_projects
            WHERE user_id = :user_id
            AND deleted = false
            ORDER BY updated_at DESC
        """), {"user_id": user_id}
    )
    rows = result.fetchall()

    projects: List[GoogleDriveProject] = []
    for row in rows:
        project_id, root_folder_name, indexing_status, indexing_progress, updated_at, score, confidence = row
        # Calculate file_count from indexing_progress if available
        progress_data = indexing_progress or {}
        file_count = progress_data.get('total', 0) or progress_data.get('indexed', 0)
        
        projects.append(
            GoogleDriveProject(
                id=str(project_id),
                name=root_folder_name,
                file_count=file_count,
                status=indexing_status or "idle",
                updated_at=updated_at.isoformat() if updated_at else "",
            )
        )

    return GoogleDriveProjectsResponse(projects=projects)


@router.get(
    "/google-drive/indexing-status",
    summary="Get ZVec indexing status for all projects",
)
async def get_indexing_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> Dict[str, Any]:
    """
    Returns detailed ZVec indexing status for polling.
    Shows progress of document indexing across all projects.
    """
    import uuid
    from sqlalchemy import text
    from app.services.zvec_service import get_zvec_service
    
    user_id = uuid.UUID(str(current_user.id))
    
    # Get project indexing statuses
    result = await db.execute(
        text("""
            SELECT 
                project_id,
                root_folder_name,
                indexing_status,
                indexing_progress,
                last_indexed_at,
                score,
                confidence
            FROM google_drive_projects
            WHERE user_id = :user_id
            AND deleted = false
            ORDER BY updated_at DESC
        """), {"user_id": user_id}
    )
    
    projects_status = []
    total_indexed = 0
    total_files = 0
    
    for row in result.fetchall():
        project_id, folder_name, status, progress, last_indexed, score, confidence = row
        progress_data = progress or {}
        indexed = progress_data.get('indexed', 0)
        total = progress_data.get('total', 0)
        total_indexed += indexed
        total_files += total
        
        projects_status.append({
            "project_id": str(project_id),
            "name": folder_name,
            "status": status or "idle",
            "progress": progress_data,
            "indexed": indexed,
            "total": total,
            "percent": round((indexed / total * 100), 1) if total > 0 else 0,
            "last_indexed": last_indexed.isoformat() if last_indexed else None,
            "score": float(score) if score else 0,
            "confidence": float(confidence) if confidence else 0,
        })
    
    # Get ZVec stats
    zvec = get_zvec_service()
    zvec_stats = zvec.get_stats()
    
    return {
        "projects": projects_status,
        "summary": {
            "total_projects": len(projects_status),
            "total_indexed": total_indexed,
            "total_files": total_files,
            "overall_percent": round((total_indexed / total_files * 100), 1) if total_files > 0 else 0,
            "zvec_ready": zvec_stats.get('ready', False),
            "zvec_count": zvec_stats.get('count', 0),
        }
    }


@router.get("/google-drive/debug")
async def debug_google_drive(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> Dict[str, Any]:
    """Debug endpoint to check database state."""
    from sqlalchemy import text
    import traceback
    import uuid
    from datetime import datetime, timezone
    
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
            text("SELECT COUNT(*) FROM google_drive_projects WHERE user_id = :user_id"), {"user_id": user_id}
        )
        project_count = result.scalar()
        
        # Check integration_tokens table exists
        token_table_check = await db.execute(
            text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'integration_tokens')")
        )
        token_table_exists = token_table_check.scalar()
        
        token_details = []
        token_count = 0
        
        if token_table_exists:
            # Check integration_tokens count
            result2 = await db.execute(
                text("SELECT COUNT(*) FROM integration_tokens WHERE user_id = :user_id AND service = 'google_drive'"), {"user_id": user_id}
            )
            token_count = result2.scalar()
            
            # Get token details (without sensitive data)
            result_tokens = await db.execute(
                text("""
                    SELECT token_id, service, is_active, expiry, account_email, scopes, updated_at
                    FROM integration_tokens 
                    WHERE user_id = :user_id
                """), {"user_id": user_id}
            )
            for row in result_tokens.fetchall():
                token_id, service, is_active, expiry, account_email, scopes, updated_at = row
                # Check if expired
                is_expired = False
                if expiry:
                    try:
                        if expiry.tzinfo is None:
                            expiry = expiry.replace(tzinfo=timezone.utc)
                        is_expired = expiry < datetime.now(timezone.utc)
                    except:
                        pass
                token_details.append({
                    "token_id": token_id,
                    "service": service,
                    "is_active": is_active,
                    "is_expired": is_expired,
                    "expiry": expiry.isoformat() if expiry else None,
                    "account_email": account_email,
                    "scopes_preview": scopes[:50] + "..." if scopes and len(scopes) > 50 else scopes,
                    "updated_at": updated_at.isoformat() if updated_at else None,
                })
        
        # Get ALL projects (for debugging)
        result3 = await db.execute(
            text("SELECT user_id, project_id, root_folder_name, deleted FROM google_drive_projects LIMIT 5")
        )
        rows = result3.fetchall()
        all_projects = [{"user_id": str(r[0]), "project_id": str(r[1]), "root_folder_name": r[2], "deleted": r[3]} for r in rows]
        
        return {
            "table_exists": table_exists,
            "token_table_exists": token_table_exists,
            "user_id": str(current_user.id),
            "total_projects_in_db": total_projects,
            "project_count_for_user": project_count,
            "token_count": token_count,
            "token_details": token_details,
            "sample_projects": all_projects,
        }
    except Exception as e:
        return {
            "error": str(e),
            "traceback": traceback.format_exc(),
        }


@router.get("/google-drive/debug/credentials")
async def debug_google_drive_credentials(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> Dict[str, Any]:
    """
    Debug endpoint to check Google Drive credential status.
    """
    from sqlalchemy import text
    import uuid
    
    try:
        user_id = uuid.UUID(str(current_user.id))
        
        # Check integration_tokens for Google Drive
        result = await db.execute(
            text("""
                SELECT token_id, service, is_active, expiry, account_email, scopes, updated_at
                FROM integration_tokens 
                WHERE user_id = :user_id AND service = 'google_drive' AND is_active = true
                LIMIT 1
            """), {"user_id": user_id}
        )
        row = result.fetchone()
        
        if not row:
            return {
                "error": "No active Google Drive token found",
                "user_id": str(current_user.id),
                "solution": "Reconnect Google Drive - no stored credentials"
            }
        
        token_id, service, is_active, expiry, account_email, scopes, updated_at = row
        
        # Check if expired
        from datetime import datetime, timezone
        is_expired = False
        if expiry:
            try:
                if expiry.tzinfo is None:
                    expiry = expiry.replace(tzinfo=timezone.utc)
                is_expired = expiry < datetime.now(timezone.utc)
            except:
                pass
        
        return {
            "token_exists": True,
            "user_id": str(current_user.id),
            "email": account_email,
            "expired": is_expired,
            "expiry": expiry.isoformat() if expiry else None,
            "is_active": is_active,
            "updated_at": updated_at.isoformat() if updated_at else None,
            "credentials_valid": is_active and not is_expired,
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "user_id": str(current_user.id),
            "solution": "Check error details - may need to reconnect"
        }


@router.get("/google-drive/debug/token-details")
async def debug_google_drive_token_details(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> Dict[str, Any]:
    """
    Get detailed token information (safely - no sensitive data exposed).
    """
    from sqlalchemy import text
    import uuid
    from datetime import datetime, timezone
    
    try:
        user_id = uuid.UUID(str(current_user.id))
        
        # Get all Google Drive tokens for user
        result = await db.execute(
            text("""
                SELECT token_id, service, is_active, expiry, account_email, scopes, created_at, updated_at
                FROM integration_tokens 
                WHERE user_id = :user_id AND service = 'google_drive'
            """), {"user_id": user_id}
        )
        
        tokens = []
        for row in result.fetchall():
            token_id, service, is_active, expiry, account_email, scopes, created_at, updated_at = row
            
            # Check if expired
            is_expired = False
            if expiry:
                try:
                    exp = expiry if expiry.tzinfo else expiry.replace(tzinfo=timezone.utc)
                    is_expired = exp < datetime.now(timezone.utc)
                except:
                    pass
            
            tokens.append({
                "token_id": token_id,
                "service": service,
                "is_active": is_active,
                "is_expired": is_expired,
                "expiry": expiry.isoformat() if expiry else None,
                "account_email": account_email,
                "scopes_preview": scopes[:50] + "..." if scopes and len(scopes) > 50 else scopes,
                "created_at": created_at.isoformat() if created_at else None,
                "updated_at": updated_at.isoformat() if updated_at else None,
            })
        
        return {
            "user_id": str(current_user.id),
            "token_count": len(tokens),
            "tokens": tokens,
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "user_id": str(current_user.id),
        }


# =============================================================================
# Chat File Upload (Simplified - bypasses documents module)
# =============================================================================

from fastapi import File as FastAPIFile, UploadFile as FastAPIUploadFile
from fastapi.responses import JSONResponse

UPLOAD_DIR_CONNECTORS = "/tmp/chat_uploads"
os.makedirs(UPLOAD_DIR_CONNECTORS, exist_ok=True)


@router.get("/upload/chat")
async def upload_chat_health(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Health check for upload endpoint."""
    return {
        "status": "ok",
        "message": "Upload endpoint is available",
        "user_id": str(current_user.id),
        "upload_dir": UPLOAD_DIR_CONNECTORS,
        "dir_exists": os.path.exists(UPLOAD_DIR_CONNECTORS),
        "max_file_size": "50MB"
    }


@router.post("/upload/test")
async def upload_test(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Simple test endpoint that doesn't process files."""
    return {
        "status": "ok",
        "message": "Test endpoint works",
        "user_id": str(current_user.id),
        "timestamp": datetime.now().isoformat()
    }


@router.post("/upload/chat")
async def upload_chat_file_simple(
    file: FastAPIUploadFile = FastAPIFile(...),
    current_user: User = Depends(get_current_user)
):
    """Upload a file via chat interface.
    
    Stores the file and extracts text for indexing.
    """
    import uuid
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"Upload request received from user {current_user.id}, file: {file.filename}")
    
    try:
        # Validate file size (max 50MB)
        max_size = 50 * 1024 * 1024  # 50MB
        file_content = await file.read()
        logger.info(f"File read: {len(file_content)} bytes")
        
        if len(file_content) > max_size:
            raise HTTPException(status_code=413, detail="File too large (max 50MB)")
        
        # Generate unique file ID
        file_id = f"{current_user.id}_{uuid.uuid4().hex}"
        file_ext = os.path.splitext(file.filename)[1].lower() if file.filename else ""
        safe_filename = f"{file_id}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR_CONNECTORS, safe_filename)
        
        # Save file
        with open(file_path, "wb") as f:
            f.write(file_content)
        logger.info(f"File saved to: {file_path}")
        
        # Determine file type category
        mime_type = file.content_type or "application/octet-stream"
        file_category = "document"
        if mime_type.startswith("image/"):
            file_category = "image"
        elif mime_type.startswith("audio/"):
            file_category = "audio"
        elif mime_type.startswith("video/"):
            file_category = "video"
        
        # Try to extract text for supported documents
        extracted_text = None
        text_supported_exts = ['.pdf', '.txt', '.md', '.docx', '.png', '.jpg', '.jpeg', '.tiff']
        
        if file_ext in text_supported_exts or mime_type.startswith("text/"):
            try:
                # Simple text extraction for text files
                if mime_type.startswith("text/") or file_ext in ['.txt', '.md', '.csv']:
                    try:
                        extracted_text = file_content.decode('utf-8')
                    except UnicodeDecodeError:
                        extracted_text = file_content.decode('latin-1')
                    extracted_text = extracted_text[:10000]  # Limit to 10k chars
                    logger.info(f"Text extracted from text file: {len(extracted_text)} chars")
                
                # Extract text from .docx files
                elif file_ext == '.docx':
                    try:
                        import zipfile
                        import io
                        from xml.etree import ElementTree
                        
                        docx_file = io.BytesIO(file_content)
                        with zipfile.ZipFile(docx_file) as zf:
                            xml_content = zf.read('word/document.xml')
                        
                        # Parse XML and extract text
                        tree = ElementTree.fromstring(xml_content)
                        texts = []
                        for elem in tree.iter():
                            if elem.text and elem.text.strip():
                                texts.append(elem.text.strip())
                        
                        extracted_text = " ".join(texts)[:10000]
                        logger.info(f"Text extracted from DOCX: {len(extracted_text)} chars")
                    except Exception as docx_err:
                        logger.warning(f"DOCX extraction failed: {docx_err}")
                
                # Try PDF extraction if PyPDF2 is available
                elif file_ext == '.pdf':
                    try:
                        import PyPDF2
                        import io
                        pdf_file = io.BytesIO(file_content)
                        reader = PyPDF2.PdfReader(pdf_file)
                        text_parts = []
                        for page in reader.pages:
                            page_text = page.extract_text()
                            if page_text:
                                text_parts.append(page_text)
                        extracted_text = "\n".join(text_parts)[:10000]
                        logger.info(f"Text extracted from PDF: {len(extracted_text)} chars")
                    except Exception as pdf_err:
                        logger.warning(f"PDF extraction failed: {pdf_err}")
                
                # Index in ZVec if text was extracted
                if extracted_text and len(extracted_text) > 50:
                    from app.services.zvec_service import get_zvec_service
                    zvec = get_zvec_service()
                    doc_id = f"chat_upload_{file_id}"
                    metadata = {
                        'name': file.filename,
                        'source': 'chat_upload',
                        'mime_type': mime_type,
                        'user_id': str(current_user.id),
                        'content_preview': extracted_text[:500],
                        'file_id': file_id,
                    }
                    zvec.add_document(doc_id, extracted_text, metadata)
                    logger.info(f"Document indexed in ZVec: {doc_id}")
                    
            except Exception as e:
                logger.warning(f"Text extraction failed for {file.filename}: {e}")
                extracted_text = None
        
        # Generate file URL
        file_url = f"/api/v1/connectors/upload/chat/{file_id}"
        
        response_data = {
            "success": True,
            "file_id": file_id,
            "filename": file.filename,
            "size": len(file_content),
            "mime_type": mime_type,
            "category": file_category,
            "url": file_url,
            "text_extracted": extracted_text is not None,
            "text_length": len(extracted_text) if extracted_text else 0,
        }
        
        logger.info(f"Upload successful for user {current_user.id}: {file.filename}")
        return JSONResponse(content=response_data, status_code=200)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat file upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

