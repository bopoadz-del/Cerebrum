"""
Central Trigger Engine - Core Event System

This module provides the central event bus and trigger engine for the Cerebrum AI platform.
All events flow through this hub, and triggers are registered to respond to specific event types.
"""

import asyncio
import os
import uuid
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict
import traceback

from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)

# Distributed triggers flag (default True in production)
USE_DISTRIBUTED_TRIGGERS = os.getenv("USE_DISTRIBUTED_TRIGGERS", "true").lower() == "true" and not settings.DEBUG


class EventType(Enum):
    """Event types for the trigger system."""
    # File events
    FILE_UPLOADED = auto()
    FILE_PROCESSED = auto()
    FILE_DELETED = auto()
    FILE_UPDATED = auto()
    
    # ML events
    ML_PREDICTION_REQUESTED = auto()
    ML_PREDICTION_COMPLETED = auto()
    ML_MODEL_TRAINED = auto()
    ML_DRIFT_DETECTED = auto()
    
    # Safety events
    SAFETY_VIOLATION_DETECTED = auto()
    SAFETY_ALERT_CREATED = auto()
    SAFETY_INSPECTION_REQUIRED = auto()
    
    # Audit events
    USER_LOGIN = auto()
    USER_LOGOUT = auto()
    USER_CREATED = auto()
    USER_UPDATED = auto()
    USER_DELETED = auto()
    PERMISSION_CHANGED = auto()
    DATA_ACCESSED = auto()
    DATA_MODIFIED = auto()
    
    # BIM events
    BIM_MODEL_UPLOADED = auto()
    BIM_MODEL_PROCESSED = auto()
    CLASH_DETECTED = auto()
    
    # Economics events
    BUDGET_UPDATED = auto()
    COST_OVERRUN_DETECTED = auto()
    INVOICE_PROCESSED = auto()
    
    # Integration events
    INTEGRATION_SYNC_STARTED = auto()
    INTEGRATION_SYNC_COMPLETED = auto()
    INTEGRATION_ERROR = auto()
    
    # System events
    SYSTEM_ERROR = auto()
    SYSTEM_WARNING = auto()
    SYSTEM_MAINTENANCE = auto()
    
    # Custom events
    CUSTOM = auto()


@dataclass
class Event:
    """Event data structure."""
    type: EventType
    source: str  # Component that emitted the event
    payload: Dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None
    priority: int = 5  # 1 = highest, 10 = lowest
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "event_id": self.event_id,
            "type": self.type.name,
            "source": self.source,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "correlation_id": self.correlation_id,
            "priority": self.priority,
        }


# Type alias for event handlers
EventHandler = Callable[[Event], Coroutine[Any, Any, None]]


class TriggerEngine:
    """
    Central trigger engine - the heart of the event system.
    
    All events flow through this engine, and triggers are registered
    to respond to specific event types.
    """
    
    def __init__(self):
        """Initialize the trigger engine."""
        self._handlers: Dict[EventType, List[EventHandler]] = defaultdict(list)
        self._all_handlers: List[EventHandler] = []
        self._running = False
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._task: Optional[asyncio.Task] = None
        self._metrics: Dict[str, int] = defaultdict(int)
        self._error_handlers: List[Callable[[Event, Exception], Coroutine]] = []
        
    def register(
        self,
        event_type: EventType,
        handler: EventHandler,
    ) -> None:
        """
        Register a handler for a specific event type.
        
        Args:
            event_type: Type of event to handle
            handler: Async function to handle the event
        """
        self._handlers[event_type].append(handler)
        logger.debug(f"Registered handler for {event_type.name}")
        
    def register_all(self, handler: EventHandler) -> None:
        """
        Register a handler for all events.
        
        Args:
            handler: Async function to handle all events
        """
        self._all_handlers.append(handler)
        logger.debug("Registered global event handler")
        
    def unregister(
        self,
        event_type: EventType,
        handler: EventHandler,
    ) -> None:
        """
        Unregister a handler for a specific event type.
        
        Args:
            event_type: Type of event
            handler: Handler to remove
        """
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
            logger.debug(f"Unregistered handler for {event_type.name}")
            
    def on_error(
        self,
        handler: Callable[[Event, Exception], Coroutine],
    ) -> None:
        """
        Register an error handler.
        
        Args:
            handler: Async function to handle errors
        """
        self._error_handlers.append(handler)
        
    async def emit(self, event: Event) -> None:
        """
        Emit an event to the event bus.
        
        In production with USE_DISTRIBUTED_TRIGGERS=True, events are
        enqueued to Celery for worker processing. Otherwise, events
        are processed locally via asyncio queue.
        
        Args:
            event: Event to emit
        """
        # Use distributed processing in production
        if USE_DISTRIBUTED_TRIGGERS:
            try:
                from .distributed_bus import enqueue_trigger_event
                enqueue_trigger_event(event)
                self._metrics["events_emitted"] += 1
                logger.debug(
                    f"Event emitted (distributed): {event.type.name}",
                    event_id=event.event_id,
                )
                return
            except Exception as e:
                logger.error(
                    "Failed to enqueue distributed event, falling back to local",
                    error=str(e),
                    event_id=event.event_id,
                )
                # Fall through to local processing
        
        # Local asyncio processing (dev/test or fallback)
        await self._event_queue.put(event)
        self._metrics["events_emitted"] += 1
        logger.debug(f"Event emitted (local): {event.type.name}", event_id=event.event_id)
        
    async def emit_now(self, event: Event) -> None:
        """
        Emit and process an event immediately (synchronous).
        
        Args:
            event: Event to process
        """
        await self._process_event(event)
        
    def create_event(
        self,
        event_type: EventType,
        source: str,
        payload: Dict[str, Any],
        **kwargs,
    ) -> Event:
        """
        Create a new event.
        
        Args:
            event_type: Type of event
            source: Source component
            payload: Event data
            **kwargs: Additional event fields
            
        Returns:
            Created event
        """
        return Event(
            type=event_type,
            source=source,
            payload=payload,
            **kwargs,
        )
        
    async def start(self) -> None:
        """Start the trigger engine event loop."""
        if self._running:
            return
            
        self._running = True
        self._task = asyncio.create_task(self._event_loop())
        logger.info("Trigger engine started")
        
    async def stop(self) -> None:
        """Stop the trigger engine."""
        if not self._running:
            return
            
        self._running = False
        
        # Wait for queue to empty
        await self._event_queue.join()
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
                
        logger.info("Trigger engine stopped")
        
    async def _event_loop(self) -> None:
        """Main event processing loop."""
        while self._running:
            try:
                event = await self._event_queue.get()
                await self._process_event(event)
                self._event_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in event loop", error=str(e))
                
    async def _process_event(self, event: Event) -> None:
        """
        Process a single event.
        
        Args:
            event: Event to process
        """
        self._metrics["events_processed"] += 1
        
        # Get handlers for this event type
        handlers = self._handlers.get(event.type, [])
        
        # Add global handlers
        all_handlers = handlers + self._all_handlers
        
        if not all_handlers:
            logger.debug(f"No handlers for event {event.type.name}")
            return
            
        # Execute handlers concurrently
        tasks = []
        for handler in all_handlers:
            task = asyncio.create_task(self._execute_handler(handler, event))
            tasks.append(task)
            
        # Wait for all handlers to complete
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            
    async def _execute_handler(
        self,
        handler: EventHandler,
        event: Event,
    ) -> None:
        """
        Execute a single handler with error handling.
        
        Args:
            handler: Handler to execute
            event: Event to process
        """
        try:
            await handler(event)
        except Exception as e:
            logger.error(
                f"Handler error for {event.type.name}",
                error=str(e),
                handler=handler.__name__,
                event_id=event.event_id,
            )
            
            # Call error handlers
            for error_handler in self._error_handlers:
                try:
                    await error_handler(event, e)
                except Exception as eh_error:
                    logger.error("Error handler failed", error=str(eh_error))
                    
    def get_metrics(self) -> Dict[str, int]:
        """Get engine metrics."""
        return dict(self._metrics)
        
    def get_handler_count(self) -> Dict[str, int]:
        """Get count of handlers per event type."""
        return {
            event_type.name: len(handlers)
            for event_type, handlers in self._handlers.items()
        }


# Global event bus instance
event_bus = TriggerEngine()


# Decorator for registering event handlers
def on_event(event_type: EventType):
    """
    Decorator to register an event handler.
    
    Args:
        event_type: Type of event to handle
        
    Example:
        @on_event(EventType.FILE_UPLOADED)
        async def handle_file_upload(event: Event):
            print(f"File uploaded: {event.payload}")
    """
    def decorator(func: EventHandler) -> EventHandler:
        event_bus.register(event_type, func)
        return func
    return decorator


# Decorator for registering global event handlers
def on_all_events(func: EventHandler) -> EventHandler:
    """
    Decorator to register a global event handler.
    
    Example:
        @on_all_events
        async def log_all_events(event: Event):
            print(f"Event: {event.type.name}")
    """
    event_bus.register_all(func)
    return func
