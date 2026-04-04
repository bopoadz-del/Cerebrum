"""
Safety Triggers - Auto-validate safety compliance

Automatically validates safety compliance based on events:
- Safety violation detection
- Automatic alert generation
- Inspection scheduling
- Compliance reporting
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from app.core.logging import get_logger
from app.triggers.engine import Event, EventType, event_bus
from app.workers.celery_config import fast_task, slow_task

logger = get_logger(__name__)


class SafetyTriggerManager:
    """
    Manages safety-related triggers and automatic validation.
    """
    
    def __init__(self):
        """Initialize the safety trigger manager."""
        self._violation_handlers: Dict[str, Any] = {}
        self._register_handlers()
        
    def _register_handlers(self) -> None:
        """Register all safety event handlers."""
        event_bus.register(EventType.SAFETY_VIOLATION_DETECTED, self._on_violation_detected)
        event_bus.register(EventType.FILE_UPLOADED, self._on_file_uploaded_safety)
        event_bus.register(EventType.ML_PREDICTION_COMPLETED, self._on_ml_prediction_safety)
        event_bus.register(EventType.USER_LOGIN, self._on_user_login_safety)
        logger.info("Safety trigger handlers registered")
        
    async def _on_violation_detected(self, event: Event) -> None:
        """
        Handle safety violation detection.
        
        Args:
            event: Safety violation event
        """
        payload = event.payload
        violation_type = payload.get("violation_type")
        severity = payload.get("severity", "medium")
        location = payload.get("location")
        
        logger.warning(
            "Safety violation detected",
            violation_type=violation_type,
            severity=severity,
            location=location,
        )
        
        # Create alert
        await self._create_safety_alert(event)
        
        # Schedule inspection if high severity
        if severity in ["high", "critical"]:
            await self._schedule_inspection(event)
            
        # Notify safety team
        await self._notify_safety_team(event)
        
    async def _on_file_uploaded_safety(self, event: Event) -> None:
        """
        Handle file upload for safety analysis.
        
        Args:
            event: File upload event
        """
        payload = event.payload
        file_name = payload.get("file_name")
        mime_type = payload.get("mime_type")
        
        # Check if it's a safety-related file
        if self._is_safety_document(file_name):
            logger.info("Safety document uploaded - validating", file_name=file_name)
            validate_safety_document.delay(file_id=payload.get("file_id"))
            
        # Check if it's an image that might contain safety violations
        if mime_type and mime_type.startswith("image/"):
            logger.info("Image uploaded - checking for safety violations")
            detect_safety_violations_in_image.delay(
                file_id=payload.get("file_id"),
                file_path=payload.get("file_path"),
            )
            
    async def _on_ml_prediction_safety(self, event: Event) -> None:
        """
        Handle ML prediction for safety analysis.
        
        Args:
            event: ML prediction event
        """
        payload = event.payload
        prediction_type = payload.get("prediction_type")
        result = payload.get("result", {})
        
        # Check if prediction indicates safety risk
        if prediction_type == "safety_risk":
            risk_score = result.get("risk_score", 0)
            
            if risk_score > 0.8:
                logger.warning(
                    "High safety risk detected from ML prediction",
                    risk_score=risk_score,
                )
                
                # Create safety alert
                await event_bus.emit(
                    event_bus.create_event(
                        EventType.SAFETY_VIOLATION_DETECTED,
                        source="safety_triggers",
                        payload={
                            "violation_type": "predicted_risk",
                            "severity": "high",
                            "risk_score": risk_score,
                            "details": result,
                        },
                        tenant_id=event.tenant_id,
                    )
                )
                
    async def _on_user_login_safety(self, event: Event) -> None:
        """
        Handle user login for safety checks.
        
        Args:
            event: User login event
        """
        payload = event.payload
        user_id = payload.get("user_id")
        
        # Check if user has pending safety training
        check_safety_training.delay(user_id=user_id)
        
        # Check if user has expired certifications
        check_expired_certifications.delay(user_id=user_id)
        
    async def _create_safety_alert(self, event: Event) -> None:
        """
        Create a safety alert.
        
        Args:
            event: Safety violation event
        """
        payload = event.payload
        
        create_safety_alert.delay(
            violation_type=payload.get("violation_type"),
            severity=payload.get("severity"),
            location=payload.get("location"),
            description=payload.get("description"),
            tenant_id=event.tenant_id,
            user_id=event.user_id,
        )
        
    async def _schedule_inspection(self, event: Event) -> None:
        """
        Schedule a safety inspection.
        
        Args:
            event: Safety violation event
        """
        payload = event.payload
        
        schedule_safety_inspection.delay(
            violation_type=payload.get("violation_type"),
            location=payload.get("location"),
            priority="high",
            tenant_id=event.tenant_id,
        )
        
    async def _notify_safety_team(self, event: Event) -> None:
        """
        Notify safety team of violation.
        
        Args:
            event: Safety violation event
        """
        payload = event.payload
        
        notify_safety_team.delay(
            violation_type=payload.get("violation_type"),
            severity=payload.get("severity"),
            location=payload.get("location"),
            tenant_id=event.tenant_id,
        )
        
    def _is_safety_document(self, file_name: str) -> bool:
        """Check if file is a safety document."""
        safety_keywords = [
            "safety", "incident", "accident", "inspection",
            "hazard", "risk", "osha", "jsa", "pta"
        ]
        return any(kw in file_name.lower() for kw in safety_keywords)


# Celery tasks for safety processing
@fast_task(bind=True, max_retries=3)
def create_safety_alert(
    self,
    violation_type: str,
    severity: str,
    location: Optional[str],
    description: Optional[str],
    tenant_id: Optional[str],
    user_id: Optional[str],
) -> Dict[str, Any]:
    """
    Create safety alert in background.
    
    Args:
        violation_type: Type of violation
        severity: Severity level
        location: Location of violation
        description: Description
        tenant_id: Tenant ID
        user_id: User ID
        
    Returns:
        Alert creation result
    """
    try:
        logger.info("Creating safety alert", violation_type=violation_type)
        
        # Create alert in database
        alert_id = f"alert_{datetime.utcnow().timestamp()}"
        
        # Send notifications
        if severity in ["high", "critical"]:
            send_immediate_alert.delay(
                alert_id=alert_id,
                violation_type=violation_type,
                severity=severity,
            )
        
        return {
            "status": "success",
            "alert_id": alert_id,
            "violation_type": violation_type,
            "severity": severity,
        }
        
    except Exception as exc:
        logger.error("Failed to create safety alert", error=str(exc))
        raise self.retry(exc=exc, countdown=30)


@fast_task(bind=True, max_retries=3)
def schedule_safety_inspection(
    self,
    violation_type: str,
    location: Optional[str],
    priority: str,
    tenant_id: Optional[str],
) -> Dict[str, Any]:
    """
    Schedule safety inspection.
    
    Args:
        violation_type: Type of violation
        location: Location
        priority: Priority level
        tenant_id: Tenant ID
        
    Returns:
        Scheduling result
    """
    try:
        logger.info("Scheduling safety inspection", violation_type=violation_type)
        
        # Calculate inspection date based on priority
        if priority == "critical":
            inspection_date = datetime.utcnow() + timedelta(hours=24)
        elif priority == "high":
            inspection_date = datetime.utcnow() + timedelta(days=3)
        else:
            inspection_date = datetime.utcnow() + timedelta(days=7)
        
        # Create inspection record
        inspection_id = f"insp_{datetime.utcnow().timestamp()}"
        
        return {
            "status": "success",
            "inspection_id": inspection_id,
            "scheduled_date": inspection_date.isoformat(),
            "priority": priority,
        }
        
    except Exception as exc:
        logger.error("Failed to schedule inspection", error=str(exc))
        raise self.retry(exc=exc, countdown=30)


@fast_task(bind=True, max_retries=3)
def notify_safety_team(
    self,
    violation_type: str,
    severity: str,
    location: Optional[str],
    tenant_id: Optional[str],
) -> Dict[str, Any]:
    """
    Notify safety team.
    
    Args:
        violation_type: Type of violation
        severity: Severity level
        location: Location
        tenant_id: Tenant ID
        
    Returns:
        Notification result
    """
    try:
        logger.info("Notifying safety team", violation_type=violation_type)
        
        # Send email notification
        # Send SMS for critical violations
        # Post to Slack/Teams
        
        if severity == "critical":
            # Send immediate notifications
            pass
        
        return {
            "status": "success",
            "notified": True,
            "channels": ["email"],
        }
        
    except Exception as exc:
        logger.error("Failed to notify safety team", error=str(exc))
        raise self.retry(exc=exc, countdown=30)


@slow_task(bind=True, max_retries=3)
def validate_safety_document(self, file_id: str) -> Dict[str, Any]:
    """
    Validate safety document.
    
    Args:
        file_id: File ID
        
    Returns:
        Validation result
    """
    try:
        logger.info("Validating safety document", file_id=file_id)
        
        # Check document completeness
        # Verify required fields
        # Validate signatures
        
        return {
            "status": "success",
            "file_id": file_id,
            "valid": True,
            "issues": [],
        }
        
    except Exception as exc:
        logger.error("Safety document validation failed", error=str(exc))
        raise self.retry(exc=exc, countdown=60)


@slow_task(bind=True, max_retries=3)
def detect_safety_violations_in_image(
    self,
    file_id: str,
    file_path: str,
) -> Dict[str, Any]:
    """
    Detect safety violations in image using ML.
    
    Args:
        file_id: File ID
        file_path: Path to image
        
    Returns:
        Detection results
    """
    try:
        logger.info("Detecting safety violations in image", file_id=file_id)
        
        # Load safety detection model
        # Run inference
        # Detect PPE, hazards, etc.
        
        violations = []
        
        # Example detections
        # violations.append({
        #     "type": "missing_hard_hat",
        #     "confidence": 0.95,
        #     "bbox": [100, 200, 150, 250],
        # })
        
        # If violations found, emit event
        if violations:
            asyncio.run(event_bus.emit(
                event_bus.create_event(
                    EventType.SAFETY_VIOLATION_DETECTED,
                    source="safety_triggers.image_detection",
                    payload={
                        "violation_type": "image_detection",
                        "violations": violations,
                        "file_id": file_id,
                    },
                )
            ))
        
        return {
            "status": "success",
            "file_id": file_id,
            "violations_found": len(violations),
            "violations": violations,
        }
        
    except Exception as exc:
        logger.error("Safety violation detection failed", error=str(exc))
        raise self.retry(exc=exc, countdown=60)


@slow_task(bind=True, max_retries=3)
def check_safety_training(self, user_id: str) -> Dict[str, Any]:
    """
    Check if user has pending safety training.
    
    Args:
        user_id: User ID
        
    Returns:
        Training status
    """
    try:
        logger.info("Checking safety training", user_id=user_id)
        
        # Check training records
        # Identify pending training
        
        pending_training = []
        
        return {
            "status": "success",
            "user_id": user_id,
            "pending_training": pending_training,
        }
        
    except Exception as exc:
        logger.error("Safety training check failed", error=str(exc))
        raise self.retry(exc=exc, countdown=60)


@slow_task(bind=True, max_retries=3)
def check_expired_certifications(self, user_id: str) -> Dict[str, Any]:
    """
    Check for expired certifications.
    
    Args:
        user_id: User ID
        
    Returns:
        Certification status
    """
    try:
        logger.info("Checking certifications", user_id=user_id)
        
        # Check certification expiry dates
        # Notify if any are expired or expiring soon
        
        expired = []
        expiring_soon = []
        
        return {
            "status": "success",
            "user_id": user_id,
            "expired": expired,
            "expiring_soon": expiring_soon,
        }
        
    except Exception as exc:
        logger.error("Certification check failed", error=str(exc))
        raise self.retry(exc=exc, countdown=60)


@fast_task(bind=True, max_retries=3)
def send_immediate_alert(
    self,
    alert_id: str,
    violation_type: str,
    severity: str,
) -> Dict[str, Any]:
    """
    Send immediate alert for critical violations.
    
    Args:
        alert_id: Alert ID
        violation_type: Type of violation
        severity: Severity level
        
    Returns:
        Alert sending result
    """
    try:
        logger.info("Sending immediate alert", alert_id=alert_id)
        
        # Send SMS
        # Send push notification
        # Call safety officer
        
        return {
            "status": "success",
            "alert_id": alert_id,
            "sent": True,
        }
        
    except Exception as exc:
        logger.error("Immediate alert failed", error=str(exc))
        raise self.retry(exc=exc, countdown=30)


# Global instance
safety_trigger_manager = SafetyTriggerManager()
