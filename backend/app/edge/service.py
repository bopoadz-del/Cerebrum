"""Application service and persistence ports for edge operations."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.edge.models import (
    EdgeDeployment,
    EdgeDeploymentStatus,
    EdgeDevice,
    EdgeDeviceStatus,
    EdgeHeartbeat,
)

logger = get_logger(__name__)


class DeviceNotFoundError(LookupError):
    pass


class DeploymentNotFoundError(LookupError):
    pass


class EdgeRepository(Protocol):
    async def get_device(self, tenant_id: uuid.UUID, external_id: str) -> EdgeDevice | None: ...

    async def save_device(self, device: EdgeDevice) -> EdgeDevice: ...

    async def list_devices(self, tenant_id: uuid.UUID) -> list[EdgeDevice]: ...

    async def save_heartbeat(self, heartbeat: EdgeHeartbeat) -> EdgeHeartbeat: ...

    async def list_heartbeats(
        self, device_id: uuid.UUID, *, limit: int = 20
    ) -> list[EdgeHeartbeat]: ...

    async def get_deployment(
        self, tenant_id: uuid.UUID, deployment_id: uuid.UUID
    ) -> EdgeDeployment | None: ...

    async def save_deployment(self, deployment: EdgeDeployment) -> EdgeDeployment: ...

    async def list_deployments(self, device_id: uuid.UUID) -> list[EdgeDeployment]: ...

    async def commit(self) -> None: ...


class RetrainHook(Protocol):
    async def request_retrain(
        self, *, model_name: str, model_version: str, drift_score: float
    ) -> str | None: ...


class ObservabilityRetrainHook:
    """Emits a stable learning signal until job persistence is unified."""

    async def request_retrain(
        self, *, model_name: str, model_version: str, drift_score: float
    ) -> str | None:
        logger.warning(
            "edge_drift_retrain_candidate",
            model_name=model_name,
            model_version=model_version,
            drift_score=drift_score,
        )
        return None


class SQLAlchemyEdgeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_device(self, tenant_id: uuid.UUID, external_id: str) -> EdgeDevice | None:
        result = await self.session.execute(
            select(EdgeDevice).where(
                EdgeDevice.tenant_id == tenant_id,
                EdgeDevice.external_id == external_id,
            )
        )
        return result.scalar_one_or_none()

    async def save_device(self, device: EdgeDevice) -> EdgeDevice:
        self.session.add(device)
        await self.session.flush()
        return device

    async def list_devices(self, tenant_id: uuid.UUID) -> list[EdgeDevice]:
        result = await self.session.execute(
            select(EdgeDevice)
            .where(EdgeDevice.tenant_id == tenant_id)
            .order_by(EdgeDevice.created_at.desc())
        )
        return list(result.scalars().all())

    async def save_heartbeat(self, heartbeat: EdgeHeartbeat) -> EdgeHeartbeat:
        self.session.add(heartbeat)
        await self.session.flush()
        return heartbeat

    async def list_heartbeats(
        self, device_id: uuid.UUID, *, limit: int = 20
    ) -> list[EdgeHeartbeat]:
        result = await self.session.execute(
            select(EdgeHeartbeat)
            .where(EdgeHeartbeat.device_id == device_id)
            .order_by(EdgeHeartbeat.received_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_deployment(
        self, tenant_id: uuid.UUID, deployment_id: uuid.UUID
    ) -> EdgeDeployment | None:
        result = await self.session.execute(
            select(EdgeDeployment)
            .join(EdgeDevice)
            .where(
                EdgeDeployment.id == deployment_id,
                EdgeDevice.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def save_deployment(self, deployment: EdgeDeployment) -> EdgeDeployment:
        self.session.add(deployment)
        await self.session.flush()
        return deployment

    async def list_deployments(self, device_id: uuid.UUID) -> list[EdgeDeployment]:
        result = await self.session.execute(
            select(EdgeDeployment)
            .where(EdgeDeployment.device_id == device_id)
            .order_by(EdgeDeployment.created_at.desc())
        )
        return list(result.scalars().all())

    async def commit(self) -> None:
        await self.session.commit()


class EdgeControlPlaneService:
    def __init__(
        self,
        repository: EdgeRepository,
        retrain_hook: RetrainHook | None = None,
        drift_threshold: float = 0.2,
    ) -> None:
        self.repository = repository
        self.retrain_hook = retrain_hook or ObservabilityRetrainHook()
        self.drift_threshold = drift_threshold

    async def register_device(
        self,
        *,
        tenant_id: uuid.UUID,
        external_id: str,
        name: str,
        device_type: str,
        software_version: str | None,
        capabilities: list[str],
        hardware: dict[str, Any],
        heartbeat_interval_seconds: int,
    ) -> EdgeDevice:
        device = await self.repository.get_device(tenant_id, external_id)
        if device is None:
            device = EdgeDevice(tenant_id=tenant_id, external_id=external_id, name=name)
        device.name = name
        device.device_type = device_type
        device.software_version = software_version
        device.capabilities = capabilities
        device.hardware = hardware
        device.heartbeat_interval_seconds = heartbeat_interval_seconds
        device.status = EdgeDeviceStatus.PROVISIONING.value
        await self.repository.save_device(device)
        await self.repository.commit()
        logger.info("edge_device_registered", device_id=external_id, tenant_id=str(tenant_id))
        return device

    async def heartbeat(
        self,
        *,
        tenant_id: uuid.UUID,
        external_id: str,
        metrics: dict[str, Any],
        active_model_version: str | None,
    ) -> EdgeHeartbeat:
        device = await self._require_device(tenant_id, external_id)
        now = datetime.now(timezone.utc)
        device.last_heartbeat_at = now
        device.status = EdgeDeviceStatus.ONLINE.value
        heartbeat = EdgeHeartbeat(
            device_id=device.id,
            received_at=now,
            metrics=metrics,
            active_model_version=active_model_version,
        )
        await self.repository.save_device(device)
        await self.repository.save_heartbeat(heartbeat)
        await self.repository.commit()
        return heartbeat

    async def list_devices(self, tenant_id: uuid.UUID) -> list[EdgeDevice]:
        devices = await self.repository.list_devices(tenant_id)
        now = datetime.now(timezone.utc)
        for device in devices:
            if not device.last_heartbeat_at:
                continue
            age = (now - device.last_heartbeat_at).total_seconds()
            if age > device.heartbeat_interval_seconds * 3:
                device.status = EdgeDeviceStatus.OFFLINE.value
        return devices

    async def list_device_heartbeats(
        self, tenant_id: uuid.UUID, external_id: str, *, limit: int = 20
    ) -> list[EdgeHeartbeat]:
        device = await self._require_device(tenant_id, external_id)
        return await self.repository.list_heartbeats(device.id, limit=limit)

    async def list_device_deployments(
        self, tenant_id: uuid.UUID, external_id: str
    ) -> list[EdgeDeployment]:
        device = await self._require_device(tenant_id, external_id)
        return await self.repository.list_deployments(device.id)

    async def create_deployment(
        self,
        *,
        tenant_id: uuid.UUID,
        external_id: str,
        model_name: str,
        model_version: str,
        adapter: str,
        artifact_uri: str | None,
        artifact_sha256: str | None,
    ) -> EdgeDeployment:
        device = await self._require_device(tenant_id, external_id)
        deployment = EdgeDeployment(
            device_id=device.id,
            model_name=model_name,
            model_version=model_version,
            adapter=adapter,
            artifact_uri=artifact_uri,
            artifact_sha256=artifact_sha256,
            status=EdgeDeploymentStatus.PENDING.value,
            inference_count=0,
            error_count=0,
        )
        await self.repository.save_deployment(deployment)
        await self.repository.commit()
        return deployment

    async def report_inference(
        self,
        *,
        tenant_id: uuid.UUID,
        deployment_id: uuid.UUID,
        sample_count: int,
        error_count: int,
        average_latency_ms: float,
        drift_score: float | None,
    ) -> dict[str, Any]:
        deployment = await self.repository.get_deployment(tenant_id, deployment_id)
        if deployment is None:
            raise DeploymentNotFoundError(str(deployment_id))

        previous_count = deployment.inference_count or 0
        total_count = previous_count + sample_count
        previous_latency = deployment.average_latency_ms or 0.0
        deployment.average_latency_ms = (
            (previous_latency * previous_count) + (average_latency_ms * sample_count)
        ) / total_count
        deployment.inference_count = total_count
        deployment.error_count = (deployment.error_count or 0) + error_count
        deployment.latest_drift_score = drift_score

        retrain_job_id = None
        if drift_score is not None and drift_score >= self.drift_threshold:
            retrain_job_id = await self.retrain_hook.request_retrain(
                model_name=deployment.model_name,
                model_version=deployment.model_version,
                drift_score=drift_score,
            )
            deployment.retrain_requested_at = datetime.now(timezone.utc)

        await self.repository.save_deployment(deployment)
        await self.repository.commit()
        return {
            "deployment": deployment,
            "drift_detected": drift_score is not None and drift_score >= self.drift_threshold,
            "retrain_job_id": retrain_job_id,
        }

    async def _require_device(self, tenant_id: uuid.UUID, external_id: str) -> EdgeDevice:
        device = await self.repository.get_device(tenant_id, external_id)
        if device is None:
            raise DeviceNotFoundError(external_id)
        return device
