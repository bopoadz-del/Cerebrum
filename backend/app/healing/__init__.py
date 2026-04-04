"""
Self-Healing Module

Error detection and automatic patch generation for self-repairing code.
"""
from .error_detection import (
    ErrorEvent,
    ErrorSeverity,
    SentryWebhookHandler,
    ErrorPatternAnalyzer,
    HealthMonitor
)
from .patch_generation import (
    PatchResult,
    PatchGenerator,
    SelfHealingEngine
)

__all__ = [
    # Error Detection
    "ErrorEvent",
    "ErrorSeverity",
    "SentryWebhookHandler",
    "ErrorPatternAnalyzer",
    "HealthMonitor",
    # Patch Generation
    "PatchResult",
    "PatchGenerator",
    "SelfHealingEngine"
]
