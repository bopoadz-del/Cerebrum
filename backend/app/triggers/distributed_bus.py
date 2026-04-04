"""
Distributed Trigger Bus - Celery-based Event Distribution

Provides distributed event processing using Celery workers.
Events emitted from the API are enqueued and processed by workers,
enabling horizontal scaling and reliability.
"""

import json
from typing import Any, Dict
from datetime import datetime

from celery import Celery
from celery.exceptions import CeleryError

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Celery app configuration
celery_app = Celery(
    "trigger_events",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max per task
    task_soft_time_limit=240,  # Soft limit at 4 minutes
    worker_prefetch_multiplier=1,  # Fair task distribution
)

# Import managers for handler execution
from . import (
    file_trigger_manager,
    ml_trigger_manager,
    safety_trigger_manager,
    audit_trigger_manager,
)
from .engine import Event, EventType


class IdempotencyStore:
    """Redis-based idempotency store for deduplication."""
    
    def __init__(self):
        import redis
        self.redis_client = redis.from_url(settings.redis_url)
        self.ttl_seconds = 3600  # 1 hour TTL for processed events
    
    def is_processed(self, event_id: str) -> bool:
        """Check if event has already been processed."""
        key = f"trg:done:{event_id}"
        return self.redis_client.exists(key) > 0
    
    def mark_processed(self, event_id: str) -> bool:
        """
        Mark event as processed (setnx = set if not exists).
        
        Returns:
            True if this is the first time seeing this event
            False if event was already processed
        """
        key = f"trg:done:{event_id}"
        # setnx returns 1 if key was set, 0 if it already existed
        was_set = self.redis_client.setnx(key, "1")
        if was_set:
            # Set expiration to clean up old entries
            self.redis_client.expire(key, self.ttl_seconds)
        return bool(was_set)


# Global idempotency store
_idempotency_store = None


def get_idempotency_store() -> IdempotencyStore:
    """Get or create idempotency store singleton."""
    global _idempotency_store
    if _idempotency_store is None:
        _idempotency_store = IdempotencyStore()
    return _idempotency_store


@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def process_trigger_event(self, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Celery task to process a trigger event.
    
    This task is called by workers to process events that were
    emitted from the API. Includes idempotency checking to prevent
    duplicate processing.
    
    Args:
        event_dict: Serialized event data
        
    Returns:
        Processing result
    """
    event_id = event_dict.get("event_id")
    event_type_name = event_dict.get("type")
    
    logger.info(
        "Processing trigger event",
        event_id=event_id,
        event_type=event_type_name,
        task_id=self.request.id,
    )
    
    # Check idempotency - prevent duplicate processing
    idempotency = get_idempotency_store()
    if not idempotency.mark_processed(event_id):
        logger.info(
            "Event already processed, skipping",
            event_id=event_id,
        )
        return {
            "status": "skipped",
            "reason": "already_processed",
            "event_id": event_id,
        }
    
    try:
        # Reconstruct event
        event = _deserialize_event(event_dict)
        
        # Route to appropriate manager based on event type
        handler_count = _route_event_to_manager(event)
        
        logger.info(
            "Event processed successfully",
            event_id=event_id,
            handlers_executed=handler_count,
        )
        
        return {
            "status": "success",
            "event_id": event_id,
            "handlers_executed": handler_count,
        }
        
    except Exception as e:
        logger.error(
            "Failed to process trigger event",
            event_id=event_id,
            error=str(e),
        )
        
        # Retry on failure (up to max_retries)
        if self.request.retries < self.max_retries:
            logger.warning(
                "Retrying event processing",
                event_id=event_id,
                retry_count=self.request.retries + 1,
            )
            raise self.retry(exc=e)
        
        return {
            "status": "failed",
            "event_id": event_id,
            "error": str(e),
        }


def _deserialize_event(event_dict: Dict[str, Any]) -> Event:
    """Deserialize event dictionary back to Event object."""
    # Parse timestamp
    timestamp_str = event_dict.get("timestamp")
    timestamp = datetime.fromisoformat(timestamp_str) if timestamp_str else datetime.utcnow()
    
    # Get event type
    event_type_name = event_dict.get("type")
    try:
        event_type = EventType[event_type_name]
    except KeyError:
        logger.warning(f"Unknown event type: {event_type_name}, using CUSTOM")
        event_type = EventType.CUSTOM
    
    return Event(
        type=event_type,
        source=event_dict.get("source", "unknown"),
        payload=event_dict.get("payload", {}),
        event_id=event_dict.get("event_id"),
        timestamp=timestamp,
        tenant_id=event_dict.get("tenant_id"),
        user_id=event_dict.get("user_id"),
        correlation_id=event_dict.get("correlation_id"),
        priority=event_dict.get("priority", 5),
    )


def _route_event_to_manager(event: Event) -> int:
    """
    Route event to the appropriate manager for handling.
    
    Returns:
        Number of handlers executed
    """
    import asyncio
    
    handler_count = 0
    
    # Map event types to managers
    file_event_types = {
        EventType.FILE_UPLOADED,
        EventType.FILE_PROCESSED,
        EventType.FILE_DELETED,
        EventType.FILE_UPDATED,
    }
    
    ml_event_types = {
        EventType.ML_PREDICTION_REQUESTED,
        EventType.ML_PREDICTION_COMPLETED,
        EventType.ML_MODEL_TRAINED,
        EventType.ML_DRIFT_DETECTED,
    }
    
    safety_event_types = {
        EventType.SAFETY_VIOLATION_DETECTED,
        EventType.SAFETY_ALERT_CREATED,
        EventType.SAFETY_INSPECTION_REQUIRED,
    }
    
    audit_event_types = {
        EventType.USER_LOGIN,
        EventType.USER_LOGOUT,
        EventType.USER_CREATED,
        EventType.USER_UPDATED,
        EventType.USER_DELETED,
        EventType.PERMISSION_CHANGED,
        EventType.DATA_ACCESSED,
        EventType.DATA_MODIFIED,
    }
    
    # Execute handlers synchronously (Celery tasks run sync)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        if event.type in file_event_types:
            # Run file trigger handlers
            loop.run_until_complete(file_trigger_manager.handle_event(event))
            handler_count += 1
            
        elif event.type in ml_event_types:
            # Run ML trigger handlers
            loop.run_until_complete(ml_trigger_manager.handle_event(event))
            handler_count += 1
            
        elif event.type in safety_event_types:
            # Run safety trigger handlers
            loop.run_until_complete(safety_trigger_manager.handle_event(event))
            handler_count += 1
            
        elif event.type in audit_event_types:
            # Run audit trigger handlers
            loop.run_until_complete(audit_trigger_manager.handle_event(event))
            handler_count += 1
            
        else:
            # Default: try all managers
            logger.debug(f"No specific handler for {event.type.name}, trying all managers")
            
    finally:
        loop.close()
    
    return handler_count


def enqueue_trigger_event(event: Event) -> str:
    """
    Enqueue a trigger event for distributed processing.
    
    Args:
        event: Event to enqueue
        
    Returns:
        Celery task ID
    """
    event_dict = event.to_dict()
    
    # Send to trigger_events queue
    task = process_trigger_event.apply_async(
        args=[event_dict],
        queue="trigger_events",
    )
    
    logger.info(
        "Trigger event enqueued",
        event_id=event.event_id,
        task_id=task.id,
        queue="trigger_events",
    )
    
    return task.id


# Celery task routing configuration
celery_app.conf.task_routes = {
    "app.triggers.distributed_bus.process_trigger_event": {"queue": "trigger_events"},
}
