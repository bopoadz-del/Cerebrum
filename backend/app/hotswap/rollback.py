"""
Rollback System

Instant rollback to previous versions with automatic recovery.
"""
import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class RollbackStatus(str, Enum):
    """Status of a rollback operation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class RollbackPoint:
    """Represents a point to which we can rollback."""
    capability_id: str
    version: str
    code_snapshot: str
    metadata: Dict[str, Any]
    created_at: datetime
    created_by: str
    reason: str


@dataclass
class RollbackOperation:
    """Represents a rollback operation."""
    id: str
    capability_id: str
    from_version: str
    to_version: str
    status: RollbackStatus
    started_at: datetime
    completed_at: Optional[datetime]
    error_message: Optional[str]
    triggered_by: str


class RollbackManager:
    """
    Manages rollback points and operations.
    
    Features:
    - Create rollback points before deployments
    - Instant rollback to previous versions
    - Rollback history tracking
    - Automatic rollback on failure detection
    """
    
    def __init__(self, storage_path: str = "/tmp/cerebrum_rollbacks"):
        self.storage_path = storage_path
        self._rollback_points: Dict[str, List[RollbackPoint]] = {}
        self._operations: Dict[str, RollbackOperation] = {}
        self._ensure_storage()
    
    def _ensure_storage(self):
        """Ensure storage directory exists."""
        os.makedirs(self.storage_path, exist_ok=True)
    
    def create_rollback_point(
        self,
        capability_id: str,
        version: str,
        code_snapshot: str,
        created_by: str,
        reason: str = "deployment",
        metadata: Dict[str, Any] = None
    ) -> RollbackPoint:
        """
        Create a rollback point before making changes.
        
        Args:
            capability_id: ID of the capability
            version: Version being deployed
            code_snapshot: Code to save for rollback
            created_by: Who created the rollback point
            reason: Reason for creating rollback point
            metadata: Additional metadata
        
        Returns:
            Created RollbackPoint
        """
        point = RollbackPoint(
            capability_id=capability_id,
            version=version,
            code_snapshot=code_snapshot,
            metadata=metadata or {},
            created_at=datetime.utcnow(),
            created_by=created_by,
            reason=reason
        )
        
        # Store in memory
        if capability_id not in self._rollback_points:
            self._rollback_points[capability_id] = []
        
        self._rollback_points[capability_id].append(point)
        
        # Keep only last 10 rollback points per capability
        if len(self._rollback_points[capability_id]) > 10:
            self._rollback_points[capability_id] = self._rollback_points[capability_id][-10:]
        
        # Persist to disk
        self._persist_rollback_point(point)
        
        logger.info(f"Created rollback point for {capability_id} v{version}")
        return point
    
    def _persist_rollback_point(self, point: RollbackPoint):
        """Save rollback point to disk."""
        filename = f"{point.capability_id}_{point.version}_{point.created_at.isoformat()}.json"
        filepath = os.path.join(self.storage_path, filename)
        
        data = {
            **asdict(point),
            "created_at": point.created_at.isoformat()
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def rollback(
        self,
        capability_id: str,
        to_version: Optional[str] = None,
        triggered_by: str = "manual"
    ) -> RollbackOperation:
        """
        Rollback to a previous version.
        
        Args:
            capability_id: ID of capability to rollback
            to_version: Specific version to rollback to (None = previous)
            triggered_by: Who/what triggered the rollback
        
        Returns:
            RollbackOperation with result
        """
        import uuid
        
        operation_id = str(uuid.uuid4())
        
        # Find rollback point
        points = self._rollback_points.get(capability_id, [])
        
        if not points:
            # Try to load from disk
            points = self._load_rollback_points(capability_id)
        
        if not points:
            operation = RollbackOperation(
                id=operation_id,
                capability_id=capability_id,
                from_version="unknown",
                to_version=to_version or "unknown",
                status=RollbackStatus.FAILED,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                error_message="No rollback points found",
                triggered_by=triggered_by
            )
            self._operations[operation_id] = operation
            return operation
        
        # Find target version
        if to_version:
            target_point = next(
                (p for p in points if p.version == to_version), None
            )
        else:
            # Get previous version (second to last)
            target_point = points[-2] if len(points) > 1 else points[0]
        
        if not target_point:
            operation = RollbackOperation(
                id=operation_id,
                capability_id=capability_id,
                from_version=points[-1].version if points else "unknown",
                to_version=to_version or "unknown",
                status=RollbackStatus.FAILED,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                error_message=f"Version {to_version} not found in rollback history",
                triggered_by=triggered_by
            )
            self._operations[operation_id] = operation
            return operation
        
        # Create operation
        current_version = points[-1].version if points else "unknown"
        operation = RollbackOperation(
            id=operation_id,
            capability_id=capability_id,
            from_version=current_version,
            to_version=target_point.version,
            status=RollbackStatus.IN_PROGRESS,
            started_at=datetime.utcnow(),
            completed_at=None,
            error_message=None,
            triggered_by=triggered_by
        )
        self._operations[operation_id] = operation
        
        try:
            # Perform rollback
            self._execute_rollback(target_point)
            
            operation.status = RollbackStatus.COMPLETED
            operation.completed_at = datetime.utcnow()
            
            logger.info(
                f"Rollback completed: {capability_id} from {current_version} "
                f"to {target_point.version}"
            )
        
        except Exception as e:
            operation.status = RollbackStatus.FAILED
            operation.completed_at = datetime.utcnow()
            operation.error_message = str(e)
            
            logger.error(f"Rollback failed: {e}")
        
        return operation
    
    def _execute_rollback(self, point: RollbackPoint):
        """Execute the actual rollback."""
        # This would integrate with the deployment system
        # For now, we just log the intent
        logger.info(f"Executing rollback to {point.version}")
        
        # In a real implementation:
        # 1. Update capability registry
        # 2. Reload module with old code
        # 3. Update routes
        # 4. Verify rollback succeeded
    
    def _load_rollback_points(self, capability_id: str) -> List[RollbackPoint]:
        """Load rollback points from disk."""
        points = []
        
        for filename in os.listdir(self.storage_path):
            if filename.startswith(f"{capability_id}_"):
                filepath = os.path.join(self.storage_path, filename)
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                        point = RollbackPoint(
                            capability_id=data["capability_id"],
                            version=data["version"],
                            code_snapshot=data["code_snapshot"],
                            metadata=data.get("metadata", {}),
                            created_at=datetime.fromisoformat(data["created_at"]),
                            created_by=data["created_by"],
                            reason=data["reason"]
                        )
                        points.append(point)
                except:
                    pass
        
        # Sort by creation time
        points.sort(key=lambda p: p.created_at)
        
        self._rollback_points[capability_id] = points
        return points
    
    def get_rollback_history(self, capability_id: str) -> List[RollbackPoint]:
        """Get rollback history for a capability."""
        if capability_id not in self._rollback_points:
            self._load_rollback_points(capability_id)
        
        return self._rollback_points.get(capability_id, [])
    
    def get_last_rollback_point(self, capability_id: str) -> Optional[RollbackPoint]:
        """Get the most recent rollback point."""
        points = self.get_rollback_history(capability_id)
        return points[-1] if points else None
    
    def auto_rollback_on_error(
        self,
        capability_id: str,
        error_count: int,
        error_threshold: int = 5
    ) -> Optional[RollbackOperation]:
        """
        Automatically trigger rollback if error threshold exceeded.
        
        Args:
            capability_id: ID of capability
            error_count: Current error count
            error_threshold: Threshold for auto-rollback
        
        Returns:
            RollbackOperation if triggered, None otherwise
        """
        if error_count >= error_threshold:
            logger.warning(
                f"Auto-rollback triggered for {capability_id}: "
                f"error count {error_count} >= threshold {error_threshold}"
            )
            return self.rollback(capability_id, triggered_by="auto")
        
        return None
    
    def can_rollback(self, capability_id: str) -> bool:
        """Check if rollback is available for a capability."""
        points = self.get_rollback_history(capability_id)
        return len(points) > 1
    
    def get_operation(self, operation_id: str) -> Optional[RollbackOperation]:
        """Get rollback operation by ID."""
        return self._operations.get(operation_id)
    
    def list_operations(
        self,
        capability_id: Optional[str] = None
    ) -> List[RollbackOperation]:
        """List rollback operations."""
        operations = list(self._operations.values())
        
        if capability_id:
            operations = [op for op in operations if op.capability_id == capability_id]
        
        return sorted(operations, key=lambda op: op.started_at, reverse=True)
    
    def cleanup_old_points(self, max_age_days: int = 30):
        """Clean up old rollback points."""
        cutoff = datetime.utcnow() - datetime.timedelta(days=max_age_days)
        
        for capability_id, points in list(self._rollback_points.items()):
            self._rollback_points[capability_id] = [
                p for p in points if p.created_at > cutoff
            ]


class BlueGreenDeployment:
    """
    Blue-green deployment support for zero-downtime updates.
    
    Maintains two versions:
    - Blue: Current production version
    - Green: New version being deployed
    """
    
    def __init__(self, rollback_manager: RollbackManager):
        self.rollback_manager = rollback_manager
        self._blue_version: Dict[str, str] = {}
        self._green_version: Dict[str, str] = {}
        self._active_color: Dict[str, str] = {}  # capability_id -> "blue" | "green"
    
    def deploy_green(
        self,
        capability_id: str,
        version: str,
        code: str
    ) -> bool:
        """
        Deploy new version to green environment.
        
        Args:
            capability_id: ID of capability
            version: New version
            code: New code
        
        Returns:
            True if deployed successfully
        """
        # Save current blue version
        if capability_id not in self._blue_version:
            self._blue_version[capability_id] = version
        
        # Deploy to green
        self._green_version[capability_id] = version
        
        # Create rollback point
        self.rollback_manager.create_rollback_point(
            capability_id=capability_id,
            version=version,
            code_snapshot=code,
            created_by="blue_green_deployment",
            reason="blue_green_deploy"
        )
        
        logger.info(f"Deployed {capability_id} v{version} to green")
        return True
    
    def switch_traffic(self, capability_id: str) -> bool:
        """
        Switch traffic from blue to green.
        
        Args:
            capability_id: ID of capability
        
        Returns:
            True if switched successfully
        """
        current = self._active_color.get(capability_id, "blue")
        new_color = "green" if current == "blue" else "blue"
        
        self._active_color[capability_id] = new_color
        
        logger.info(f"Switched {capability_id} traffic to {new_color}")
        return True
    
    def rollback_blue_green(self, capability_id: str) -> bool:
        """Rollback to the other color."""
        current = self._active_color.get(capability_id, "blue")
        other = "blue" if current == "green" else "green"
        
        self._active_color[capability_id] = other
        
        logger.info(f"Rolled back {capability_id} to {other}")
        return True
    
    def get_active_version(self, capability_id: str) -> Optional[str]:
        """Get currently active version."""
        color = self._active_color.get(capability_id, "blue")
        if color == "blue":
            return self._blue_version.get(capability_id)
        else:
            return self._green_version.get(capability_id)
