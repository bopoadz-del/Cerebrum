"""Authenticated edge control-plane endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db_session
from app.edge.schemas import (
    DeploymentCreate,
    DeploymentResponse,
    DeviceRegistration,
    DeviceResponse,
    HeartbeatDetail,
    HeartbeatReport,
    HeartbeatResponse,
    InferenceMetricsReport,
    InferenceMetricsResponse,
)
from app.edge.service import (
    DeploymentNotFoundError,
    DeviceNotFoundError,
    EdgeControlPlaneService,
    SQLAlchemyEdgeRepository,
)
from app.models.user import User

router = APIRouter(prefix="/edge", tags=["edge"])


async def get_edge_service(
    db: AsyncSession = Depends(get_db_session),
) -> EdgeControlPlaneService:
    return EdgeControlPlaneService(SQLAlchemyEdgeRepository(db))


@router.post(
    "/devices/register",
    response_model=DeviceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_device(
    request: DeviceRegistration,
    current_user: User = Depends(get_current_user),
    service: EdgeControlPlaneService = Depends(get_edge_service),
) -> DeviceResponse:
    return await service.register_device(
        tenant_id=current_user.tenant_id,
        external_id=request.external_id,
        name=request.name,
        device_type=request.device_type,
        software_version=request.software_version,
        capabilities=request.capabilities,
        hardware=request.hardware,
        heartbeat_interval_seconds=request.heartbeat_interval_seconds,
    )


@router.post("/devices/{external_id}/heartbeat", response_model=HeartbeatResponse)
async def record_heartbeat(
    external_id: str,
    request: HeartbeatReport,
    current_user: User = Depends(get_current_user),
    service: EdgeControlPlaneService = Depends(get_edge_service),
) -> HeartbeatResponse:
    try:
        heartbeat = await service.heartbeat(
            tenant_id=current_user.tenant_id,
            external_id=external_id,
            metrics=request.metrics,
            active_model_version=request.active_model_version,
        )
    except DeviceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Edge device not found") from exc
    return HeartbeatResponse(received_at=heartbeat.received_at, status="online")


@router.get("/devices", response_model=list[DeviceResponse])
async def list_devices(
    current_user: User = Depends(get_current_user),
    service: EdgeControlPlaneService = Depends(get_edge_service),
) -> list[DeviceResponse]:
    return await service.list_devices(current_user.tenant_id)


@router.get(
    "/devices/{external_id}/heartbeats",
    response_model=list[HeartbeatDetail],
)
async def list_device_heartbeats(
    external_id: str,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    service: EdgeControlPlaneService = Depends(get_edge_service),
) -> list[HeartbeatDetail]:
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    try:
        return await service.list_device_heartbeats(
            current_user.tenant_id, external_id, limit=limit
        )
    except DeviceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Edge device not found") from exc


@router.get(
    "/devices/{external_id}/deployments",
    response_model=list[DeploymentResponse],
)
async def list_device_deployments(
    external_id: str,
    current_user: User = Depends(get_current_user),
    service: EdgeControlPlaneService = Depends(get_edge_service),
) -> list[DeploymentResponse]:
    try:
        return await service.list_device_deployments(
            current_user.tenant_id, external_id
        )
    except DeviceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Edge device not found") from exc


@router.post(
    "/deployments",
    response_model=DeploymentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_deployment(
    request: DeploymentCreate,
    current_user: User = Depends(get_current_user),
    service: EdgeControlPlaneService = Depends(get_edge_service),
) -> DeploymentResponse:
    try:
        return await service.create_deployment(
            tenant_id=current_user.tenant_id,
            external_id=request.external_id,
            model_name=request.model_name,
            model_version=request.model_version,
            adapter=request.adapter,
            artifact_uri=request.artifact_uri,
            artifact_sha256=request.artifact_sha256,
        )
    except DeviceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Edge device not found") from exc


@router.post(
    "/deployments/{deployment_id}/inference-metrics",
    response_model=InferenceMetricsResponse,
)
async def report_inference_metrics(
    deployment_id: uuid.UUID,
    request: InferenceMetricsReport,
    current_user: User = Depends(get_current_user),
    service: EdgeControlPlaneService = Depends(get_edge_service),
) -> InferenceMetricsResponse:
    try:
        return await service.report_inference(
            tenant_id=current_user.tenant_id,
            deployment_id=deployment_id,
            sample_count=request.sample_count,
            error_count=request.error_count,
            average_latency_ms=request.average_latency_ms,
            drift_score=request.drift_score,
        )
    except DeploymentNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Edge deployment not found") from exc
