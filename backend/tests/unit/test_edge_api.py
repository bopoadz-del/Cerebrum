import uuid
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.v1.endpoints.edge import get_edge_service, router
from app.edge.service import EdgeControlPlaneService
from tests.unit.test_edge_service import InMemoryEdgeRepository, RecordingRetrainHook


def test_edge_api_happy_path():
    tenant_id = uuid.uuid4()
    service = EdgeControlPlaneService(
        InMemoryEdgeRepository(),
        retrain_hook=RecordingRetrainHook(),
        drift_threshold=0.2,
    )
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(tenant_id=tenant_id)
    app.dependency_overrides[get_edge_service] = lambda: service

    with TestClient(app) as client:
        registered = client.post(
            "/api/v1/edge/devices/register",
            json={
                "external_id": "jetson-a1",
                "name": "Gate camera",
                "device_type": "jetson_orin",
                "capabilities": ["vision"],
            },
        )
        assert registered.status_code == 201
        assert registered.json()["status"] == "provisioning"

        heartbeat = client.post(
            "/api/v1/edge/devices/jetson-a1/heartbeat",
            json={"metrics": {"temperature_c": 52.0}, "active_model_version": "v1"},
        )
        assert heartbeat.status_code == 200
        assert heartbeat.json()["status"] == "online"

        devices = client.get("/api/v1/edge/devices")
        assert devices.status_code == 200
        assert devices.json()[0]["external_id"] == "jetson-a1"

        heartbeats = client.get("/api/v1/edge/devices/jetson-a1/heartbeats")
        assert heartbeats.status_code == 200
        assert len(heartbeats.json()) == 1
        assert heartbeats.json()[0]["metrics"]["temperature_c"] == 52.0

        deployment = client.post(
            "/api/v1/edge/deployments",
            json={
                "external_id": "jetson-a1",
                "model_name": "site-safety",
                "model_version": "v1",
                "adapter": "mock",
            },
        )
        assert deployment.status_code == 201
        deployment_id = deployment.json()["id"]

        listed = client.get("/api/v1/edge/devices/jetson-a1/deployments")
        assert listed.status_code == 200
        assert listed.json()[0]["id"] == deployment_id

        metrics = client.post(
            f"/api/v1/edge/deployments/{deployment_id}/inference-metrics",
            json={
                "sample_count": 20,
                "error_count": 1,
                "average_latency_ms": 10.5,
                "drift_score": 0.25,
            },
        )
        assert metrics.status_code == 200
        assert metrics.json()["drift_detected"] is True
        assert metrics.json()["deployment"]["inference_count"] == 20
