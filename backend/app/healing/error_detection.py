"""
Error Detection System

Sentry webhook integration and error pattern analysis.
"""
import json
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ErrorSeverity(str, Enum):
    """Error severity levels."""
    FATAL = "fatal"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ErrorEvent:
    """Represents an error event."""
    event_id: str
    capability_id: Optional[str]
    error_type: str
    error_message: str
    stack_trace: str
    severity: ErrorSeverity
    timestamp: datetime
    context: Dict[str, Any]
    user_agent: Optional[str]
    url: Optional[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "capability_id": self.capability_id,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "stack_trace": self.stack_trace,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context,
            "user_agent": self.user_agent,
            "url": self.url
        }


class SentryWebhookHandler:
    """
    Handles Sentry webhook events for error detection.
    
    Processes:
    - Error events
    - Performance issues
    - Regression alerts
    """
    
    def __init__(self):
        self._error_handlers: List[callable] = []
        self._error_history: List[ErrorEvent] = []
        self._max_history = 1000
    
    def process_webhook(self, payload: Dict[str, Any]) -> Optional[ErrorEvent]:
        """
        Process a Sentry webhook payload.
        
        Args:
            payload: Sentry webhook JSON payload
        
        Returns:
            ErrorEvent if processed successfully
        """
        try:
            # Extract event data
            event_data = payload.get("event", {})
            
            event_id = event_data.get("event_id", "unknown")
            
            # Extract error type and message
            exception = event_data.get("exception", {})
            values = exception.get("values", [])
            
            if not values:
                logger.warning("No exception values in Sentry event")
                return None
            
            exc_info = values[0]
            error_type = exc_info.get("type", "UnknownError")
            error_message = exc_info.get("value", "")
            
            # Extract stack trace
            stack_trace = self._extract_stack_trace(exc_info)
            
            # Determine severity
            level = event_data.get("level", "error")
            severity = self._map_severity(level)
            
            # Extract capability ID from context
            capability_id = self._extract_capability_id(event_data)
            
            # Extract context
            context = event_data.get("extra", {})
            
            # Create error event
            event = ErrorEvent(
                event_id=event_id,
                capability_id=capability_id,
                error_type=error_type,
                error_message=error_message,
                stack_trace=stack_trace,
                severity=severity,
                timestamp=datetime.utcnow(),
                context=context,
                user_agent=event_data.get("request", {}).get("headers", {}).get("User-Agent"),
                url=event_data.get("request", {}).get("url")
            )
            
            # Store in history
            self._add_to_history(event)
            
            # Notify handlers
            self._notify_handlers(event)
            
            logger.info(f"Processed error event: {event_id} ({error_type})")
            return event
        
        except Exception as e:
            logger.error(f"Failed to process Sentry webhook: {e}")
            return None
    
    def _extract_stack_trace(self, exc_info: Dict) -> str:
        """Extract formatted stack trace from exception info."""
        stacktrace = exc_info.get("stacktrace", {})
        frames = stacktrace.get("frames", [])
        
        lines = []
        for frame in reversed(frames):  # Most recent last
            filename = frame.get("filename", "unknown")
            lineno = frame.get("lineno", 0)
            function = frame.get("function", "unknown")
            context_line = frame.get("context_line", "")
            
            lines.append(f"  File \"{filename}\", line {lineno}, in {function}")
            if context_line:
                lines.append(f"    {context_line.strip()}")
        
        return "\n".join(lines)
    
    def _extract_capability_id(self, event_data: Dict) -> Optional[str]:
        """Extract capability ID from event context."""
        # Try to find capability ID in various places
        extra = event_data.get("extra", {})
        
        # Check explicit capability_id
        if "capability_id" in extra:
            return extra["capability_id"]
        
        # Try to extract from tags
        tags = event_data.get("tags", [])
        for tag in tags:
            if tag[0] == "capability_id":
                return tag[1]
        
        # Try to infer from stack trace
        exception = event_data.get("exception", {})
        values = exception.get("values", [])
        if values:
            stacktrace = values[0].get("stacktrace", {})
            frames = stacktrace.get("frames", [])
            for frame in frames:
                filename = frame.get("filename", "")
                # Look for dynamic module patterns
                match = re.search(r"dynamic_([a-f0-9-]+)", filename)
                if match:
                    return match.group(1)
        
        return None
    
    def _map_severity(self, level: str) -> ErrorSeverity:
        """Map Sentry level to our severity."""
        mapping = {
            "fatal": ErrorSeverity.FATAL,
            "error": ErrorSeverity.ERROR,
            "warning": ErrorSeverity.WARNING,
            "info": ErrorSeverity.INFO,
            "debug": ErrorSeverity.INFO
        }
        return mapping.get(level, ErrorSeverity.ERROR)
    
    def _add_to_history(self, event: ErrorEvent):
        """Add event to history with size limit."""
        self._error_history.append(event)
        
        if len(self._error_history) > self._max_history:
            self._error_history = self._error_history[-self._max_history:]
    
    def _notify_handlers(self, event: ErrorEvent):
        """Notify registered error handlers."""
        for handler in self._error_handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error handler failed: {e}")
    
    def register_handler(self, handler: callable):
        """Register an error handler callback."""
        self._error_handlers.append(handler)
    
    def unregister_handler(self, handler: callable):
        """Unregister an error handler."""
        if handler in self._error_handlers:
            self._error_handlers.remove(handler)
    
    def get_error_history(
        self,
        capability_id: Optional[str] = None,
        severity: Optional[ErrorSeverity] = None,
        limit: int = 100
    ) -> List[ErrorEvent]:
        """Get error history with optional filtering."""
        events = self._error_history
        
        if capability_id:
            events = [e for e in events if e.capability_id == capability_id]
        
        if severity:
            events = [e for e in events if e.severity == severity]
        
        return events[-limit:]
    
    def get_error_stats(self, capability_id: Optional[str] = None) -> Dict[str, Any]:
        """Get error statistics."""
        events = self._error_history
        
        if capability_id:
            events = [e for e in events if e.capability_id == capability_id]
        
        total = len(events)
        by_severity = {}
        by_type = {}
        
        for event in events:
            # Count by severity
            sev = event.severity.value
            by_severity[sev] = by_severity.get(sev, 0) + 1
            
            # Count by type
            err_type = event.error_type
            by_type[err_type] = by_type.get(err_type, 0) + 1
        
        return {
            "total_errors": total,
            "by_severity": by_severity,
            "by_type": by_type,
            "unique_error_types": len(by_type)
        }


class ErrorPatternAnalyzer:
    """Analyzes error patterns to identify systemic issues."""
    
    def __init__(self):
        self._patterns: Dict[str, Dict[str, Any]] = {}
    
    def analyze(self, events: List[ErrorEvent]) -> List[Dict[str, Any]]:
        """
        Analyze error events for patterns.
        
        Returns:
            List of detected patterns
        """
        patterns = []
        
        # Group by error type
        by_type: Dict[str, List[ErrorEvent]] = {}
        for event in events:
            if event.error_type not in by_type:
                by_type[event.error_type] = []
            by_type[event.error_type].append(event)
        
        # Detect spikes
        for error_type, type_events in by_type.items():
            if len(type_events) >= 5:  # Threshold for spike
                patterns.append({
                    "type": "error_spike",
                    "error_type": error_type,
                    "count": len(type_events),
                    "severity": "high",
                    "recommendation": "Consider immediate rollback"
                })
        
        # Detect recurring issues by capability
        by_capability: Dict[str, List[ErrorEvent]] = {}
        for event in events:
            cid = event.capability_id or "unknown"
            if cid not in by_capability:
                by_capability[cid] = []
            by_capability[cid].append(event)
        
        for cid, cap_events in by_capability.items():
            if len(cap_events) >= 10:
                patterns.append({
                    "type": "recurring_issues",
                    "capability_id": cid,
                    "count": len(cap_events),
                    "severity": "medium",
                    "recommendation": "Review capability code for bugs"
                })
        
        return patterns
    
    def is_critical_issue(self, event: ErrorEvent) -> bool:
        """Determine if an error is critical."""
        # Critical error types
        critical_types = [
            "SyntaxError",
            "ImportError",
            "ModuleNotFoundError",
            "RecursionError",
            "MemoryError"
        ]
        
        if event.error_type in critical_types:
            return True
        
        # Check severity
        if event.severity == ErrorSeverity.FATAL:
            return True
        
        return False


class HealthMonitor:
    """Monitors system health and triggers alerts."""
    
    def __init__(self):
        self._health_checks: Dict[str, callable] = {}
        self._status: Dict[str, bool] = {}
    
    def register_health_check(self, name: str, check_fn: callable):
        """Register a health check function."""
        self._health_checks[name] = check_fn
    
    async def run_health_checks(self) -> Dict[str, Any]:
        """Run all health checks."""
        results = {}
        
        for name, check_fn in self._health_checks.items():
            try:
                healthy = await check_fn() if asyncio.iscoroutinefunction(check_fn) else check_fn()
                results[name] = {"healthy": healthy}
                self._status[name] = healthy
            except Exception as e:
                results[name] = {"healthy": False, "error": str(e)}
                self._status[name] = False
        
        return results
    
    def is_healthy(self) -> bool:
        """Check if all systems are healthy."""
        return all(self._status.values())


# Import asyncio for health monitor
import asyncio
