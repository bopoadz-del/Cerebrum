"""Persistent models for the edge control plane."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import BaseModel


class EdgeDeviceStatus(str, enum.Enum):
    PROVISIONING = "provisioning"
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"


class EdgeDeploymentStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    FAILED = "failed"
    SUPERSEDED = "superseded"


class EdgeDevice(BaseModel):
    __tablename__ = "edge_devices"
    __table_args__ = (
        UniqueConstraint("tenant_id", "external_id", name="uq_edge_device_tenant_external"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    device_type: Mapped[str] = mapped_column(String(64), nullable=False, default="generic")
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=EdgeDeviceStatus.PROVISIONING.value
    )
    software_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    capabilities: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    hardware: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    heartbeat_interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=30)

    heartbeats: Mapped[list["EdgeHeartbeat"]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )
    deployments: Mapped[list["EdgeDeployment"]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )


class EdgeHeartbeat(BaseModel):
    __tablename__ = "edge_heartbeats"

    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("edge_devices.id", ondelete="CASCADE"), index=True
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True
    )
    metrics: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    active_model_version: Mapped[str | None] = mapped_column(String(64))

    device: Mapped[EdgeDevice] = relationship(back_populates="heartbeats")


class EdgeDeployment(BaseModel):
    __tablename__ = "edge_deployments"

    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("edge_devices.id", ondelete="CASCADE"), index=True
    )
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    adapter: Mapped[str] = mapped_column(String(32), nullable=False, default="mock")
    artifact_uri: Mapped[str | None] = mapped_column(String(1024))
    artifact_sha256: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=EdgeDeploymentStatus.PENDING.value, index=True
    )
    inference_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    average_latency_ms: Mapped[float | None] = mapped_column(Float)
    latest_drift_score: Mapped[float | None] = mapped_column(Float)
    retrain_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    device: Mapped[EdgeDevice] = relationship(back_populates="deployments")
