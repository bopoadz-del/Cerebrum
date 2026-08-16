"""Wire schemas for the edge control plane."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DeviceRegistration(BaseModel):
    external_id: str = Field(min_length=3, max_length=128)
    name: str = Field(min_length=1, max_length=255)
    device_type: str = Field(default="generic", max_length=64)
    software_version: str | None = Field(default=None, max_length=64)
    capabilities: list[str] = Field(default_factory=list)
    hardware: dict[str, Any] = Field(default_factory=dict)
    heartbeat_interval_seconds: int = Field(default=30, ge=5, le=3600)


class HeartbeatReport(BaseModel):
    metrics: dict[str, Any] = Field(default_factory=dict)
    active_model_version: str | None = Field(default=None, max_length=64)


class DeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    external_id: str
    name: str
    device_type: str
    status: str
    software_version: str | None
    capabilities: list[str]
    hardware: dict[str, Any]
    last_heartbeat_at: datetime | None
    heartbeat_interval_seconds: int


class HeartbeatResponse(BaseModel):
    received_at: datetime
    status: str


class HeartbeatDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    received_at: datetime
    metrics: dict[str, Any]
    active_model_version: str | None


class DeploymentCreate(BaseModel):
    external_id: str = Field(min_length=3, max_length=128)
    model_name: str = Field(min_length=1, max_length=255)
    model_version: str = Field(min_length=1, max_length=64)
    adapter: Literal["mock", "tensorrt", "yolo"] = "mock"
    artifact_uri: str | None = Field(default=None, max_length=1024)
    artifact_sha256: str | None = Field(default=None, pattern=r"^[a-fA-F0-9]{64}$")


class DeploymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    device_id: uuid.UUID
    model_name: str
    model_version: str
    adapter: str
    artifact_uri: str | None
    artifact_sha256: str | None
    status: str
    inference_count: int
    error_count: int
    average_latency_ms: float | None
    latest_drift_score: float | None
    retrain_requested_at: datetime | None


class InferenceMetricsReport(BaseModel):
    sample_count: int = Field(ge=1)
    error_count: int = Field(default=0, ge=0)
    average_latency_ms: float = Field(ge=0)
    drift_score: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def error_count_within_samples(self) -> "InferenceMetricsReport":
        if self.error_count > self.sample_count:
            raise ValueError("error_count cannot exceed sample_count")
        return self


class InferenceMetricsResponse(BaseModel):
    deployment: DeploymentResponse
    drift_detected: bool
    retrain_job_id: str | None
