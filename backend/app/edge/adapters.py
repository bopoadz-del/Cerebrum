"""Inference contracts for device runtimes.

Hardware runtimes stay outside the control plane. Implementations can satisfy this
protocol without importing TensorRT or vendor SDKs into the API service.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class InferenceResult:
    output: Any
    latency_ms: float
    model_version: str


class InferenceAdapter(Protocol):
    name: str

    async def load(self, model_uri: str, model_version: str) -> None: ...

    async def infer(self, input_data: Any) -> InferenceResult: ...


class MockInferenceAdapter:
    """Deterministic adapter used by service tests and client-contract development."""

    name = "mock"

    def __init__(self) -> None:
        self._version: str | None = None

    async def load(self, model_uri: str, model_version: str) -> None:
        self._version = model_version

    async def infer(self, input_data: Any) -> InferenceResult:
        if self._version is None:
            raise RuntimeError("No model has been loaded")
        return InferenceResult(
            output={"echo": input_data},
            latency_ms=1.0,
            model_version=self._version,
        )


class TensorRTInferenceAdapter(InferenceAdapter, Protocol):
    """Extension point for a future TensorRT runtime package."""


class YoloInferenceAdapter(InferenceAdapter, Protocol):
    """Extension point for a future YOLO runtime package."""
