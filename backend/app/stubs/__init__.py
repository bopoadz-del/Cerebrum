"""
Stub Implementations for External Services

Provides safe fallback implementations when external services are unavailable.
All stubs return predictable data structures that match production interfaces.
"""

from .base import BaseStub, StubResponse, StubError
from .procore import ProcoreStub
from .aconex import AconexStub
from .primavera import PrimaveraStub
from .google_drive import GoogleDriveStub
from .slack import SlackStub
from .openai import OpenAIStub

__all__ = [
    "BaseStub",
    "StubResponse",
    "StubError",
    "ProcoreStub",
    "AconexStub",
    "PrimaveraStub",
    "GoogleDriveStub",
    "SlackStub",
    "OpenAIStub",
    "get_stub",
]


# Registry of available stubs
_STUB_REGISTRY = {
    "procore": ProcoreStub,
    "aconex": AconexStub,
    "primavera": PrimaveraStub,
    "google_drive": GoogleDriveStub,
    "slack": SlackStub,
    "openai": OpenAIStub,
}


def get_stub(service_name: str) -> BaseStub:
    """Get a stub implementation by service name."""
    stub_class = _STUB_REGISTRY.get(service_name.lower())
    if not stub_class:
        raise ValueError(f"No stub available for service: {service_name}")
    return stub_class()
