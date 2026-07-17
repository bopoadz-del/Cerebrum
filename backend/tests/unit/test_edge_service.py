import uuid

import pytest

from app.edge.adapters import MockInferenceAdapter
from app.edge.models import EdgeDeployment, EdgeDevice, EdgeHeartbeat
from app.edge.service import EdgeControlPlaneService
from app.executor.models import FormulaExecutionLog  # noqa: F401 - registers shared mapper


class InMemoryEdgeRepository:
    def __init__(self):
        self.devices: dict[tuple[uuid.UUID, str], EdgeDevice] = {}
        self.deployments: dict[uuid.UUID, EdgeDeployment] = {}
        self.heartbeats: list[EdgeHeartbeat] = []

    async def get_device(self, tenant_id, external_id):
        return self.devices.get((tenant_id, external_id))

    async def save_device(self, device):
        if device.id is None:
            device.id = uuid.uuid4()
        self.devices[(device.tenant_id, device.external_id)] = device
        return device

    async def list_devices(self, tenant_id):
        return [d for (owner, _), d in self.devices.items() if owner == tenant_id]

    async def save_heartbeat(self, heartbeat):
        if heartbeat.id is None:
            heartbeat.id = uuid.uuid4()
        self.heartbeats.append(heartbeat)
        return heartbeat

    async def list_heartbeats(self, device_id, *, limit=20):
        rows = [h for h in self.heartbeats if h.device_id == device_id]
        rows.sort(key=lambda h: h.received_at or "", reverse=True)
        return rows[:limit]

    async def get_deployment(self, tenant_id, deployment_id):
        deployment = self.deployments.get(deployment_id)
        if deployment is None:
            return None
        device = next(d for d in self.devices.values() if d.id == deployment.device_id)
        return deployment if device.tenant_id == tenant_id else None

    async def save_deployment(self, deployment):
        if deployment.id is None:
            deployment.id = uuid.uuid4()
        self.deployments[deployment.id] = deployment
        return deployment

    async def list_deployments(self, device_id):
        return [d for d in self.deployments.values() if d.device_id == device_id]

    async def commit(self):
        return None


class RecordingRetrainHook:
    def __init__(self):
        self.calls = []

    async def request_retrain(self, **signal):
        self.calls.append(signal)
        return "retrain-test-1"


@pytest.mark.asyncio
async def test_edge_service_tracks_health_deployment_and_drift():
    tenant_id = uuid.uuid4()
    repository = InMemoryEdgeRepository()
    hook = RecordingRetrainHook()
    service = EdgeControlPlaneService(repository, retrain_hook=hook, drift_threshold=0.2)

    device = await service.register_device(
        tenant_id=tenant_id,
        external_id="jetson-a1",
        name="Gate camera",
        device_type="jetson_orin",
        software_version="1.0.0",
        capabilities=["vision"],
        hardware={"gpu": "orin"},
        heartbeat_interval_seconds=30,
    )
    heartbeat = await service.heartbeat(
        tenant_id=tenant_id,
        external_id=device.external_id,
        metrics={"temperature_c": 54.0},
        active_model_version="2026.07",
    )
    deployment = await service.create_deployment(
        tenant_id=tenant_id,
        external_id=device.external_id,
        model_name="site-safety",
        model_version="2026.07",
        adapter="mock",
        artifact_uri=None,
        artifact_sha256=None,
    )
    report = await service.report_inference(
        tenant_id=tenant_id,
        deployment_id=deployment.id,
        sample_count=10,
        error_count=1,
        average_latency_ms=12.5,
        drift_score=0.3,
    )

    assert heartbeat.metrics["temperature_c"] == 54.0
    assert (await service.list_devices(tenant_id))[0].status == "online"
    assert report["deployment"].inference_count == 10
    assert report["drift_detected"] is True
    assert report["retrain_job_id"] == "retrain-test-1"
    assert hook.calls[0]["model_name"] == "site-safety"


@pytest.mark.asyncio
async def test_mock_inference_adapter_is_deterministic():
    adapter = MockInferenceAdapter()
    await adapter.load("memory://site-safety", "v1")

    result = await adapter.infer({"frame": 1})

    assert result.output == {"echo": {"frame": 1}}
    assert result.model_version == "v1"
