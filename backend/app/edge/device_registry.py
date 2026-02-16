"""
Edge Device Registry for Jetson Integration
Manages edge device registration, status, and metadata.
"""

from datetime import datetime
from typing import Optional, Dict, List, Any
from enum import Enum
import uuid

from sqlalchemy import (
    Column, String, Integer, DateTime, Boolean, 
    Float, ForeignKey, Enum as SQLEnum, JSON
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class DeviceStatus(str, Enum):
    """Edge device status values."""
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    ERROR = "error"
    UPDATING = "updating"
    MAINTENANCE = "maintenance"


class DeviceType(str, Enum):
    """Edge device types."""
    JETSON_NANO = "jetson_nano"
    JETSON_TX2 = "jetson_tx2"
    JETSON_XAVIER = "jetson_xavier"
    JETSON_ORIN = "jetson_orin"
    RASPBERRY_PI = "raspberry_pi"
    OTHER = "other"


class EdgeDevice(Base):
    """Edge device model for device registry."""
    
    __tablename__ = "edge_devices"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String(500))
    
    # Device classification
    device_type = Column(SQLEnum(DeviceType), default=DeviceType.JETSON_XAVIER)
    status = Column(SQLEnum(DeviceStatus), default=DeviceStatus.OFFLINE)
    
    # Network info
    ip_address = Column(String(45))  # IPv6 compatible
    mac_address = Column(String(17))
    port = Column(Integer, default=8080)
    
    # Location
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"))
    location = Column(String(255))
    coordinates = Column(JSONB)  # {lat, lng}
    
    # Hardware specs
    hardware_info = Column(JSONB, default=dict)  # CPU, GPU, RAM, Storage
    capabilities = Column(JSONB, default=list)  # List of supported operations
    
    # Software
    software_version = Column(String(50))
    model_versions = Column(JSONB, default=dict)  # {model_name: version}
    
    # Heartbeat tracking
    last_heartbeat = Column(DateTime)
    heartbeat_interval = Column(Integer, default=30)  # seconds
    
    # Performance metrics
    cpu_usage = Column(Float, default=0.0)
    memory_usage = Column(Float, default=0.0)
    gpu_usage = Column(Float, default=0.0)
    temperature = Column(Float)
    
    # Inference stats
    total_inferences = Column(Integer, default=0)
    avg_inference_time = Column(Float, default=0.0)
    
    # Security
    public_key = Column(String(500))
    api_token = Column(String(255))
    
    # Timestamps
    registered_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    deployments = relationship("ModelDeployment", back_populates="device")
    
    def is_online(self) -> bool:
        """Check if device is considered online."""
        if not self.last_heartbeat:
            return False
        
        elapsed = (datetime.utcnow() - self.last_heartbeat).total_seconds()
        return elapsed < (self.heartbeat_interval * 3)
    
    def update_heartbeat(self, metrics: Optional[Dict[str, Any]] = None) -> None:
        """Update device heartbeat."""
        self.last_heartbeat = datetime.utcnow()
        self.last_seen = datetime.utcnow()
        
        if metrics:
            self.cpu_usage = metrics.get('cpu_usage', self.cpu_usage)
            self.memory_usage = metrics.get('memory_usage', self.memory_usage)
            self.gpu_usage = metrics.get('gpu_usage', self.gpu_usage)
            self.temperature = metrics.get('temperature', self.temperature)
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = {
            "id": str(self.id),
            "device_id": self.device_id,
            "name": self.name,
            "description": self.description,
            "device_type": self.device_type.value if self.device_type else None,
            "status": self.status.value if self.status else None,
            "ip_address": self.ip_address,
            "location": self.location,
            "coordinates": self.coordinates,
            "hardware_info": self.hardware_info,
            "capabilities": self.capabilities,
            "software_version": self.software_version,
            "model_versions": self.model_versions,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "is_online": self.is_online(),
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "gpu_usage": self.gpu_usage,
            "temperature": self.temperature,
            "total_inferences": self.total_inferences,
            "avg_inference_time": self.avg_inference_time,
            "registered_at": self.registered_at.isoformat() if self.registered_at else None,
        }
        
        if include_sensitive:
            data["api_token"] = self.api_token
        
        return data


class ModelDeployment(Base):
    """Model deployment to edge device."""
    
    __tablename__ = "model_deployments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(UUID(as_uuid=True), ForeignKey("edge_devices.id"), nullable=False)
    model_id = Column(UUID(as_uuid=True), ForeignKey("ml_models.id"), nullable=False)
    
    # Deployment info
    version = Column(String(50), nullable=False)
    status = Column(String(50), default="pending")  # pending, deploying, active, failed, rolled_back
    
    # Deployment config
    config = Column(JSONB, default=dict)  # batch_size, input_shape, etc.
    
    # Timestamps
    deployed_at = Column(DateTime)
    activated_at = Column(DateTime)
    last_inference_at = Column(DateTime)
    
    # Stats
    inference_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    avg_latency_ms = Column(Float, default=0.0)
    
    # Relationships
    device = relationship("EdgeDevice", back_populates="deployments")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "device_id": str(self.device_id),
            "model_id": str(self.model_id),
            "version": self.version,
            "status": self.status,
            "config": self.config,
            "deployed_at": self.deployed_at.isoformat() if self.deployed_at else None,
            "inference_count": self.inference_count,
            "avg_latency_ms": self.avg_latency_ms,
        }


class DeviceRegistry:
    """
    Registry for managing edge devices.
    Provides CRUD operations and device discovery.
    """
    
    def __init__(self):
        self._devices: Dict[str, EdgeDevice] = {}  # In-memory cache
    
    async def register_device(
        self,
        device_id: str,
        name: str,
        device_type: DeviceType,
        hardware_info: Dict[str, Any],
        ip_address: Optional[str] = None,
        location: Optional[str] = None,
        capabilities: Optional[List[str]] = None
    ) -> EdgeDevice:
        """
        Register a new edge device.
        
        Args:
            device_id: Unique device identifier
            name: Device name
            device_type: Type of device
            hardware_info: Hardware specifications
            ip_address: Device IP address
            location: Physical location
            capabilities: List of supported capabilities
        
        Returns:
            Registered EdgeDevice
        """
        device = EdgeDevice(
            device_id=device_id,
            name=name,
            device_type=device_type,
            hardware_info=hardware_info,
            ip_address=ip_address,
            location=location,
            capabilities=capabilities or [],
            status=DeviceStatus.ONLINE,
            last_heartbeat=datetime.utcnow()
        )
        
        self._devices[device_id] = device
        
        logger.info(f"Registered edge device: {device_id} ({name})")
        
        return device
    
    async def get_device(self, device_id: str) -> Optional[EdgeDevice]:
        """Get device by ID."""
        return self._devices.get(device_id)
    
    async def get_all_devices(
        self,
        status: Optional[DeviceStatus] = None,
        device_type: Optional[DeviceType] = None
    ) -> List[EdgeDevice]:
        """Get all devices with optional filtering."""
        devices = list(self._devices.values())
        
        if status:
            devices = [d for d in devices if d.status == status]
        
        if device_type:
            devices = [d for d in devices if d.device_type == device_type]
        
        return devices
    
    async def update_device_status(
        self,
        device_id: str,
        status: DeviceStatus
    ) -> bool:
        """Update device status."""
        device = await self.get_device(device_id)
        if device:
            device.status = status
            device.updated_at = datetime.utcnow()
            return True
        return False
    
    async def update_heartbeat(
        self,
        device_id: str,
        metrics: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update device heartbeat."""
        device = await self.get_device(device_id)
        if device:
            device.update_heartbeat(metrics)
            
            # Update status based on health
            if metrics:
                if metrics.get('temperature', 0) > 85:
                    device.status = DeviceStatus.ERROR
                elif metrics.get('cpu_usage', 0) > 90:
                    device.status = DeviceStatus.BUSY
                else:
                    device.status = DeviceStatus.ONLINE
            
            return True
        return False
    
    async def unregister_device(self, device_id: str) -> bool:
        """Unregister a device."""
        if device_id in self._devices:
            del self._devices[device_id]
            logger.info(f"Unregistered edge device: {device_id}")
            return True
        return False
    
    async def get_online_devices(self) -> List[EdgeDevice]:
        """Get all online devices."""
        return [d for d in self._devices.values() if d.is_online()]
    
    async def get_devices_by_capability(self, capability: str) -> List[EdgeDevice]:
        """Get devices that support a specific capability."""
        return [
            d for d in self._devices.values()
            if capability in (d.capabilities or [])
        ]


# Singleton instance
device_registry = DeviceRegistry()


def get_device_registry() -> DeviceRegistry:
    """Get device registry instance."""
    return device_registry
