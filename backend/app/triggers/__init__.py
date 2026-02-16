"""
Central Trigger Engine - Core Event System

Provides event-driven architecture for Cerebrum AI platform.
All triggers are registered here and events flow through this central hub.
"""

from .engine import TriggerEngine, Event, EventType, event_bus
from .file_triggers import FileTriggerManager
from .ml_triggers import MLTriggerManager
from .safety_triggers import SafetyTriggerManager
from .audit_triggers import AuditTriggerManager

# Create manager singletons (exported for main.py imports)
file_trigger_manager = FileTriggerManager()
ml_trigger_manager = MLTriggerManager()
safety_trigger_manager = SafetyTriggerManager()
audit_trigger_manager = AuditTriggerManager()

__all__ = [
    "TriggerEngine",
    "Event",
    "EventType",
    "event_bus",
    "FileTriggerManager",
    "MLTriggerManager",
    "SafetyTriggerManager",
    "AuditTriggerManager",
    # Manager instances
    "file_trigger_manager",
    "ml_trigger_manager",
    "safety_trigger_manager",
    "audit_trigger_manager",
]
