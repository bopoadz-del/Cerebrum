"""
Edge Computing (Jetson) API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

from app.api.deps import get_current_user
from app.edge.device_registry import EdgeDeviceRegistry, EdgeDevice, DeviceStatus
from app.edge.heartbeat import HeartbeatManager
from app.edge.deployment import EdgeDeploymentManager, DeploymentStatus, DeploymentType
from app.edge.hybrid_inference import HybridInferenceOrchestrator, InferenceLocation
from app.edge.secure_tunnel import SecureTunnelManager, TunnelProtocol
from app.edge.safety_ai import SafetyAIDetector, HazardLevel, PPEType


router = APIRouter(prefix="/edge", tags=["edge"])


# Pydantic models
class DeviceRegisterRequest(BaseModel):
    device_id: str
    device_type: str = "jetson_nano"
    hardware_version: str = ""
    software_version: str = ""
    cuda_version: Optional[str] = None
    tensorrt_version: Optional[str] = None
    total_memory_mb: int = 0
    storage_total_gb: int = 0
    gpu_count: int = 0
    capabilities: List[str] = []
    location: Optional[Dict[str, float]] = None


class DeploymentCreateRequest(BaseModel):
    name: str
    version: str
    type: str
    file_url: str
    metadata: Optional[Dict[str, Any]] = {}


class DeployToDeviceRequest(BaseModel):
    device_id: str
    package_id: str


class DeployToGroupRequest(BaseModel):
    device_ids: List[str]
    package_id: str
    rollout_strategy: str = "parallel"
    batch_size: int = 5


class InferenceRequest(BaseModel):
    model_name: str
    model_version: str
    input_data: Any
    preferred_location: str = "auto"
    priority: str = "normal"
    max_latency_ms: Optional[int] = None


class TunnelCreateRequest(BaseModel):
    device_id: str
    protocol: str = "websocket"
    local_port: int
    remote_port: int
    timeout_seconds: int = 3600


class SafetyZoneCreate(BaseModel):
    zone_id: str
    name: str
    polygon: List[tuple]
    required_ppe: List[str]
    hazard_level: str = "medium"
    max_occupancy: int = 10


# Dependencies
async def get_device_registry():
    return EdgeDeviceRegistry()


async def get_heartbeat_manager():
    return HeartbeatManager()


async def get_deployment_manager():
    return EdgeDeploymentManager()


async def get_inference_orchestrator():
    return HybridInferenceOrchestrator()


async def get_tunnel_manager():
    return SecureTunnelManager()


async def get_safety_detector():
    return SafetyAIDetector()


# Device management endpoints
@router.post("/devices/register")
async def register_device(
    request: DeviceRegisterRequest,
    registry: EdgeDeviceRegistry = Depends(get_device_registry),
    current_user = Depends(get_current_user)
):
    """Register a new edge device."""
    
    from app.edge.device_registry import DeviceInfo
    
    device_info = DeviceInfo(
        device_id=request.device_id,
        device_type=request.device_type,
        hardware_version=request.hardware_version,
        software_version=request.software_version,
        cuda_version=request.cuda_version,
        tensorrt_version=request.tensorrt_version,
        total_memory_mb=request.total_memory_mb,
        storage_total_gb=request.storage_total_gb,
        gpu_count=request.gpu_count,
        capabilities=request.capabilities
    )
    
    device = await registry.register_device(device_info, location=request.location)
    return {"device_id": device.device_id, "status": device.status.value}


@router.get("/devices")
async def list_devices(
    status: Optional[str] = None,
    registry: EdgeDeviceRegistry = Depends(get_device_registry),
    current_user = Depends(get_current_user)
):
    """List all edge devices."""
    
    devices = await registry.list_devices(
        status=DeviceStatus(status) if status else None
    )
    return {"devices": [d.__dict__ for d in devices]}


@router.get("/devices/{device_id}")
async def get_device(
    device_id: str,
    registry: EdgeDeviceRegistry = Depends(get_device_registry),
    current_user = Depends(get_current_user)
):
    """Get device details."""
    
    device = await registry.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    return device.__dict__


@router.post("/devices/{device_id}/heartbeat")
async def device_heartbeat(
    device_id: str,
    metrics: Dict[str, Any],
    registry: EdgeDeviceRegistry = Depends(get_device_registry),
    current_user = Depends(get_current_user)
):
    """Receive device heartbeat."""
    
    await registry.update_heartbeat(device_id, metrics)
    return {"status": "received"}


# WebSocket endpoint for device connections
@router.websocket("/ws/{device_id}")
async def device_websocket(
    websocket: WebSocket,
    device_id: str,
    heartbeat_manager: HeartbeatManager = Depends(get_heartbeat_manager)
):
    """WebSocket endpoint for edge devices."""
    
    await websocket.accept()
    
    # Register connection
    await heartbeat_manager.register_connection(
        device_id=device_id,
        websocket=websocket
    )
    
    try:
        while True:
            message = await websocket.receive_json()
            
            if message.get("type") == "heartbeat":
                await heartbeat_manager.handle_heartbeat(message)
            elif message.get("type") == "status_update":
                # Handle status updates
                pass
            elif message.get("type") == "deployment_status":
                # Handle deployment status updates
                pass
                
    except WebSocketDisconnect:
        await heartbeat_manager.unregister_connection(device_id)


# Deployment endpoints
@router.post("/deployments/packages")
async def create_deployment_package(
    request: DeploymentCreateRequest,
    manager: EdgeDeploymentManager = Depends(get_deployment_manager),
    current_user = Depends(get_current_user)
):
    """Create a deployment package."""
    
    package = await manager.create_package(
        name=request.name,
        version=request.version,
        package_type=DeploymentType(request.type),
        file_path="",  # Would come from file upload
        file_url=request.file_url,
        metadata=request.metadata
    )
    
    return {
        "package_id": package.package_id,
        "name": package.name,
        "version": package.version,
        "size_bytes": package.size_bytes
    }


@router.post("/deployments/deploy")
async def deploy_to_device(
    request: DeployToDeviceRequest,
    manager: EdgeDeploymentManager = Depends(get_deployment_manager),
    current_user = Depends(get_current_user)
):
    """Deploy package to a device."""
    
    job = await manager.deploy_to_device(
        device_id=request.device_id,
        package_id=request.package_id
    )
    
    return {"job_id": job.job_id, "status": job.status.value}


@router.post("/deployments/deploy-group")
async def deploy_to_group(
    request: DeployToGroupRequest,
    manager: EdgeDeploymentManager = Depends(get_deployment_manager),
    current_user = Depends(get_current_user)
):
    """Deploy package to a group of devices."""
    
    result = await manager.deploy_to_group(
        device_ids=request.device_ids,
        package_id=request.package_id,
        rollout_strategy=request.rollout_strategy,
        batch_size=request.batch_size
    )
    
    return result


@router.get("/deployments/jobs/{job_id}")
async def get_deployment_status(
    job_id: str,
    manager: EdgeDeploymentManager = Depends(get_deployment_manager),
    current_user = Depends(get_current_user)
):
    """Get deployment job status."""
    
    status = await manager.get_deployment_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return status


# Inference endpoints
@router.post("/inference")
async def run_inference(
    request: InferenceRequest,
    orchestrator: HybridInferenceOrchestrator = Depends(get_inference_orchestrator),
    current_user = Depends(get_current_user)
):
    """Run inference with automatic cloud/edge selection."""
    
    from app.edge.hybrid_inference import InferencePriority
    
    result = await orchestrator.infer(
        model_name=request.model_name,
        model_version=request.model_version,
        input_data=request.input_data,
        preferred_location=InferenceLocation(request.preferred_location),
        priority=InferencePriority[request.priority.upper()],
        max_latency_ms=request.max_latency_ms
    )
    
    return {
        "request_id": result.request_id,
        "location": result.location.value,
        "output": result.output,
        "latency_ms": result.latency_ms,
        "fallback_used": result.fallback_used
    }


@router.get("/inference/stats")
async def get_inference_stats(
    model_name: Optional[str] = None,
    time_window_hours: int = 24,
    orchestrator: HybridInferenceOrchestrator = Depends(get_inference_orchestrator),
    current_user = Depends(get_current_user)
):
    """Get inference statistics."""
    
    stats = await orchestrator.get_inference_stats(
        model_name=model_name,
        time_window_hours=time_window_hours
    )
    
    return stats


# Tunnel endpoints
@router.post("/tunnels")
async def create_tunnel(
    request: TunnelCreateRequest,
    manager: SecureTunnelManager = Depends(get_tunnel_manager),
    current_user = Depends(get_current_user)
):
    """Create a secure tunnel to a device."""
    
    session = await manager.create_session(
        device_id=request.device_id,
        protocol=TunnelProtocol(request.protocol),
        local_port=request.local_port,
        remote_port=request.remote_port,
        created_by=current_user["id"],
        timeout_seconds=request.timeout_seconds
    )
    
    return {
        "session_id": session.session_id,
        "status": session.status.value,
        "expires_at": session.expires_at.isoformat()
    }


@router.get("/tunnels")
async def list_tunnels(
    device_id: Optional[str] = None,
    manager: SecureTunnelManager = Depends(get_tunnel_manager),
    current_user = Depends(get_current_user)
):
    """List active tunnels."""
    
    sessions = await manager.list_sessions(device_id=device_id)
    return {"sessions": sessions}


@router.delete("/tunnels/{session_id}")
async def close_tunnel(
    session_id: str,
    manager: SecureTunnelManager = Depends(get_tunnel_manager),
    current_user = Depends(get_current_user)
):
    """Close a tunnel session."""
    
    success = await manager.close_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"status": "closed"}


# Safety AI endpoints
@router.post("/safety/zones")
async def create_safety_zone(
    request: SafetyZoneCreate,
    detector: SafetyAIDetector = Depends(get_safety_detector),
    current_user = Depends(get_current_user)
):
    """Create a safety zone."""
    
    from app.edge.safety_ai import SafetyZone
    
    zone = SafetyZone(
        zone_id=request.zone_id,
        name=request.name,
        polygon=request.polygon,
        required_ppe=[PPEType(ppe) for ppe in request.required_ppe],
        hazard_level=HazardLevel(request.hazard_level),
        max_occupancy=request.max_occupancy
    )
    
    await detector.register_safety_zone(zone)
    
    return {"zone_id": zone.zone_id, "name": zone.name}


@router.post("/safety/analyze")
async def analyze_safety(
    camera_id: str,
    zone_id: Optional[str] = None,
    detector: SafetyAIDetector = Depends(get_safety_detector),
    current_user = Depends(get_current_user)
):
    """Analyze safety in a camera feed."""
    
    import numpy as np
    
    # Placeholder - in production, get actual image from camera
    dummy_image = np.zeros((1080, 1920, 3), dtype=np.uint8)
    
    result = await detector.process_frame(
        image=dummy_image,
        camera_id=camera_id,
        zone_id=zone_id
    )
    
    return result


@router.get("/safety/alerts")
async def get_safety_alerts(
    zone_id: Optional[str] = None,
    level: Optional[str] = None,
    acknowledged: Optional[bool] = None,
    detector: SafetyAIDetector = Depends(get_safety_detector),
    current_user = Depends(get_current_user)
):
    """Get safety alerts."""
    
    alerts = await detector.get_alerts(
        zone_id=zone_id,
        level=HazardLevel(level) if level else None,
        acknowledged=acknowledged
    )
    
    return {"alerts": alerts}


@router.post("/safety/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    detector: SafetyAIDetector = Depends(get_safety_detector),
    current_user = Depends(get_current_user)
):
    """Acknowledge a safety alert."""
    
    success = await detector.acknowledge_alert(alert_id, current_user["id"])
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return {"status": "acknowledged"}


@router.get("/safety/zones/{zone_id}/compliance")
async def get_zone_compliance(
    zone_id: str,
    time_window_minutes: int = 60,
    detector: SafetyAIDetector = Depends(get_safety_detector),
    current_user = Depends(get_current_user)
):
    """Get PPE compliance for a zone."""
    
    compliance = await detector.get_zone_compliance(
        zone_id=zone_id,
        time_window_minutes=time_window_minutes
    )
    
    return compliance


@router.get("/safety/report")
async def generate_safety_report(
    start_date: datetime,
    end_date: datetime,
    detector: SafetyAIDetector = Depends(get_safety_detector),
    current_user = Depends(get_current_user)
):
    """Generate safety compliance report."""
    
    report = await detector.generate_safety_report(start_date, end_date)
    return report
