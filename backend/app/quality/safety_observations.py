"""
Safety Observations
Digital STOP cards and safety observation reporting
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ObservationType(Enum):
    """Types of safety observations"""
    SAFE_ACT = 'safe_act'
    UNSAFE_ACT = 'unsafe_act'
    SAFE_CONDITION = 'safe_condition'
    UNSAFE_CONDITION = 'unsafe_condition'
    NEAR_MISS = 'near_miss'


class ObservationStatus(Enum):
    """Observation status"""
    OPEN = 'open'
    UNDER_REVIEW = 'under_review'
    ACTION_ASSIGNED = 'action_assigned'
    RESOLVED = 'resolved'
    CLOSED = 'closed'


@dataclass
class SafetyObservation:
    """Safety observation record"""
    id: str
    observation_type: ObservationType
    description: str
    location: str
    project_id: str
    observed_by: str
    observed_at: datetime
    status: ObservationStatus
    severity: str  # low, medium, high
    immediate_action: Optional[str] = None
    corrective_action: Optional[str] = None
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None
    photos: List[str] = field(default_factory=list)
    category: Optional[str] = None  # PPE, housekeeping, equipment, etc.
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None


class SafetyObservationManager:
    """Manage safety observations"""
    
    def __init__(self):
        self.observations: Dict[str, SafetyObservation] = {}
    
    def create_observation(
        self,
        observation_type: ObservationType,
        description: str,
        location: str,
        project_id: str,
        observed_by: str,
        severity: str = 'medium',
        photos: List[str] = None
    ) -> SafetyObservation:
        """Create new safety observation"""
        obs_id = f"SO-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        observation = SafetyObservation(
            id=obs_id,
            observation_type=observation_type,
            description=description,
            location=location,
            project_id=project_id,
            observed_by=observed_by,
            observed_at=datetime.utcnow(),
            status=ObservationStatus.OPEN,
            severity=severity,
            photos=photos or []
        )
        
        self.observations[obs_id] = observation
        logger.info(f"Created safety observation: {obs_id}")
        
        return observation
    
    def assign_action(
        self,
        observation_id: str,
        corrective_action: str,
        assigned_to: str,
        due_date: datetime
    ) -> bool:
        """Assign corrective action"""
        if observation_id not in self.observations:
            return False
        
        obs = self.observations[observation_id]
        obs.corrective_action = corrective_action
        obs.assigned_to = assigned_to
        obs.due_date = due_date
        obs.status = ObservationStatus.ACTION_ASSIGNED
        
        return True
    
    def resolve_observation(
        self,
        observation_id: str,
        resolved_by: str,
        notes: str = None
    ) -> bool:
        """Resolve observation"""
        if observation_id not in self.observations:
            return False
        
        obs = self.observations[observation_id]
        obs.status = ObservationStatus.RESOLVED
        obs.resolved_at = datetime.utcnow()
        obs.resolved_by = resolved_by
        
        return True
    
    def get_observations(
        self,
        project_id: str = None,
        status: ObservationStatus = None,
        observation_type: ObservationType = None
    ) -> List[SafetyObservation]:
        """Get observations with filters"""
        observations = list(self.observations.values())
        
        if project_id:
            observations = [o for o in observations if o.project_id == project_id]
        
        if status:
            observations = [o for o in observations if o.status == status]
        
        if observation_type:
            observations = [o for o in observations if o.observation_type == observation_type]
        
        return sorted(observations, key=lambda x: x.observed_at, reverse=True)
    
    def get_summary(self, project_id: str = None) -> Dict[str, Any]:
        """Get observation summary"""
        observations = self.observations.values()
        
        if project_id:
            observations = [o for o in observations if o.project_id == project_id]
        
        total = len(observations)
        
        by_type = {}
        for obs_type in ObservationType:
            count = sum(1 for o in observations if o.observation_type == obs_type)
            if count > 0:
                by_type[obs_type.value] = count
        
        by_status = {}
        for status in ObservationStatus:
            count = sum(1 for o in observations if o.status == status)
            if count > 0:
                by_status[status.value] = count
        
        return {
            'total_observations': total,
            'by_type': by_type,
            'by_status': by_status,
            'open_count': sum(1 for o in observations if o.status != ObservationStatus.CLOSED)
        }


# Global safety observation manager
safety_observation_manager = SafetyObservationManager()
