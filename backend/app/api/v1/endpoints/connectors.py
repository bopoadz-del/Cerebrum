"""
Connectors API Endpoints (Google Drive removed)
"""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors import get_connector_status, list_connectors, get_connector
from app.api.deps import get_current_user, get_async_db
from app.models.user import User

router = APIRouter(prefix="/connectors", tags=["Connectors"])

GDRIVE_NOT_AVAILABLE = {"detail": "Google Drive integration is disabled."}


class ConnectorStatus(BaseModel):
    stub_available: bool
    production_available: bool
    using_stub: bool
    mode: str


class ConnectorsStatusResponse(BaseModel):
    connectors: Dict[str, ConnectorStatus]
    total: int


class ConnectorInfo(BaseModel):
    name: str
    service_name: str
    version: str
    status: str
    healthy: bool


@router.get("/status", response_model=ConnectorsStatusResponse)
async def get_connectors_status(
    current_user = Depends(get_current_user),
) -> ConnectorsStatusResponse:
    status_dict = get_connector_status()
    connectors = {name: ConnectorStatus(**info) for name, info in status_dict.items()}
    return ConnectorsStatusResponse(connectors=connectors, total=len(connectors))


@router.get("/list", response_model=List[str])
async def list_available_connectors(current_user = Depends(get_current_user)) -> List[str]:
    return list_connectors()


@router.get("/{connector_name}/health")
async def get_connector_health(
    connector_name: str,
    current_user = Depends(get_current_user),
):
    try:
        connector = get_connector(connector_name)
        return connector.health_check()
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Connector not found: {connector_name}")


@router.get("/{connector_name}/info")
async def get_connector_info(
    connector_name: str,
    current_user = Depends(get_current_user),
) -> ConnectorInfo:
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
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Connector not found: {connector_name}")


# Google Drive endpoints - all return 503
@router.get("/google-drive/status")
async def gdrive_status(current_user = Depends(get_current_user)):
    raise HTTPException(status_code=503, **GDRIVE_NOT_AVAILABLE)

@router.get("/google-drive/auth")
async def gdrive_auth(current_user = Depends(get_current_user)):
    raise HTTPException(status_code=503, **GDRIVE_NOT_AVAILABLE)

@router.get("/google-drive/auth/url")
async def gdrive_auth_url(current_user = Depends(get_current_user)):
    raise HTTPException(status_code=503, **GDRIVE_NOT_AVAILABLE)

@router.get("/google-drive/callback")
async def gdrive_callback():
    raise HTTPException(status_code=503, **GDRIVE_NOT_AVAILABLE)

@router.post("/google-drive/scan")
async def gdrive_scan(current_user = Depends(get_current_user)):
    raise HTTPException(status_code=503, **GDRIVE_NOT_AVAILABLE)

@router.post("/google-drive/search")
async def gdrive_search(current_user = Depends(get_current_user)):
    raise HTTPException(status_code=503, **GDRIVE_NOT_AVAILABLE)

@router.post("/google-drive/index")
async def gdrive_index(current_user = Depends(get_current_user)):
    raise HTTPException(status_code=503, **GDRIVE_NOT_AVAILABLE)

@router.get("/google-drive/files")
async def gdrive_files(current_user = Depends(get_current_user)):
    raise HTTPException(status_code=503, **GDRIVE_NOT_AVAILABLE)

@router.get("/google-drive/projects/{project_id}/files")
async def gdrive_project_files(project_id: str, current_user = Depends(get_current_user)):
    raise HTTPException(status_code=503, **GDRIVE_NOT_AVAILABLE)

@router.get("/google-drive/folders/{folder_id}/contents")
async def gdrive_folder_contents(folder_id: str, current_user = Depends(get_current_user)):
    raise HTTPException(status_code=503, **GDRIVE_NOT_AVAILABLE)

@router.post("/google-drive/disconnect")
async def gdrive_disconnect(current_user = Depends(get_current_user)):
    raise HTTPException(status_code=503, **GDRIVE_NOT_AVAILABLE)

@router.post("/google-drive/projects/sync")
async def gdrive_sync(current_user = Depends(get_current_user)):
    raise HTTPException(status_code=503, **GDRIVE_NOT_AVAILABLE)

@router.get("/google-drive/projects")
async def gdrive_projects(current_user = Depends(get_current_user)):
    raise HTTPException(status_code=503, **GDRIVE_NOT_AVAILABLE)

@router.get("/google-drive/indexing-status")
async def gdrive_indexing_status(current_user = Depends(get_current_user)):
    raise HTTPException(status_code=503, **GDRIVE_NOT_AVAILABLE)

@router.get("/google-drive/debug")
async def gdrive_debug(current_user = Depends(get_current_user)):
    raise HTTPException(status_code=503, **GDRIVE_NOT_AVAILABLE)
