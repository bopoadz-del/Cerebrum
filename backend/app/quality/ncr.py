"""
Non-Conformance Report (NCR) System
Workflow for tracking and resolving quality issues
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class NCRStatus(Enum):
    """NCR status workflow"""
    OPEN = 'open'
    UNDER_REVIEW = 'under_review'
    CORRECTIVE_ACTION = 'corrective_action'
    VERIFICATION = 'verification'
    CLOSED = 'closed'
    REJECTED = 'rejected'


class NCRCategory(Enum):
    """NCR categories"""
    MATERIAL = 'material'
    WORKMANSHIP = 'workmanship'
    DESIGN = 'design'
    DOCUMENTATION = 'documentation'
    SAFETY = 'safety'
    OTHER = 'other'


class NCRCause(Enum):
    """Root cause categories"""
    HUMAN_ERROR = 'human_error'
    PROCEDURE_NOT_FOLLOWED = 'procedure_not_followed'
    TRAINING_INSUFFICIENT = 'training_insufficient'
    EQUIPMENT_FAILURE = 'equipment_failure'
    MATERIAL_DEFECT = 'material_defect'
    DESIGN_ERROR = 'design_error'
    COMMUNICATION_FAILURE = 'communication_failure'
    OTHER = 'other'


@dataclass
class CorrectiveAction:
    """Corrective action for NCR"""
    id: str
    description: str
    assigned_to: str
    due_date: datetime
    status: str = 'pending'
    completed_at: Optional[datetime] = None
    evidence: List[str] = field(default_factory=list)


@dataclass
class NCR:
    """Non-Conformance Report"""
    id: str
    title: str
    description: str
    project_id: str
    category: NCRCategory
    status: NCRStatus
    reported_by: str
    reported_at: datetime
    location: Optional[str] = None
    reference_documents: List[str] = field(default_factory=list)
    photos: List[str] = field(default_factory=list)
    severity: str = 'minor'  # minor, major, critical
    root_cause: Optional[NCRCause] = None
    root_cause_analysis: Optional[str] = None
    corrective_actions: List[CorrectiveAction] = field(default_factory=list)
    preventive_actions: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    closed_by: Optional[str] = None
    closed_at: Optional[datetime] = None
    closure_notes: Optional[str] = None


class NCRManager:
    """Manage NCR workflow"""
    
    def __init__(self):
        self.ncrs: Dict[str, NCR] = {}
        self._status_transitions = {
            NCRStatus.OPEN: [NCRStatus.UNDER_REVIEW, NCRStatus.REJECTED],
            NCRStatus.UNDER_REVIEW: [NCRStatus.CORRECTIVE_ACTION, NCRStatus.REJECTED],
            NCRStatus.CORRECTIVE_ACTION: [NCRStatus.VERIFICATION],
            NCRStatus.VERIFICATION: [NCRStatus.CLOSED, NCRStatus.CORRECTIVE_ACTION],
        }
    
    def create_ncr(
        self,
        title: str,
        description: str,
        project_id: str,
        category: NCRCategory,
        reported_by: str,
        location: str = None,
        severity: str = 'minor',
        photos: List[str] = None
    ) -> NCR:
        """Create new NCR"""
        ncr_id = f"NCR-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        ncr = NCR(
            id=ncr_id,
            title=title,
            description=description,
            project_id=project_id,
            category=category,
            status=NCRStatus.OPEN,
            reported_by=reported_by,
            reported_at=datetime.utcnow(),
            location=location,
            severity=severity,
            photos=photos or []
        )
        
        self.ncrs[ncr_id] = ncr
        logger.info(f"Created NCR: {ncr_id}")
        
        return ncr
    
    def transition_status(
        self,
        ncr_id: str,
        new_status: NCRStatus,
        user_id: str,
        notes: str = None
    ) -> bool:
        """Transition NCR to new status"""
        if ncr_id not in self.ncrs:
            return False
        
        ncr = self.ncrs[ncr_id]
        
        # Validate transition
        valid_transitions = self._status_transitions.get(ncr.status, [])
        if new_status not in valid_transitions and new_status != ncr.status:
            logger.warning(f"Invalid status transition: {ncr.status} -> {new_status}")
            return False
        
        ncr.status = new_status
        
        # Update timestamps
        if new_status == NCRStatus.CLOSED:
            ncr.closed_by = user_id
            ncr.closed_at = datetime.utcnow()
            ncr.closure_notes = notes
        elif new_status == NCRStatus.UNDER_REVIEW:
            ncr.reviewed_by = user_id
            ncr.reviewed_at = datetime.utcnow()
        
        logger.info(f"NCR {ncr_id} transitioned to {new_status.value}")
        return True
    
    def add_corrective_action(
        self,
        ncr_id: str,
        description: str,
        assigned_to: str,
        due_date: datetime
    ) -> Optional[str]:
        """Add corrective action to NCR"""
        if ncr_id not in self.ncrs:
            return None
        
        action_id = f"CA-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        action = CorrectiveAction(
            id=action_id,
            description=description,
            assigned_to=assigned_to,
            due_date=due_date
        )
        
        self.ncrs[ncr_id].corrective_actions.append(action)
        
        # Auto-transition to corrective action status
        if self.ncrs[ncr_id].status == NCRStatus.UNDER_REVIEW:
            self.transition_status(ncr_id, NCRStatus.CORRECTIVE_ACTION, assigned_to)
        
        return action_id
    
    def complete_corrective_action(
        self,
        ncr_id: str,
        action_id: str,
        user_id: str,
        evidence: List[str] = None
    ) -> bool:
        """Mark corrective action as complete"""
        if ncr_id not in self.ncrs:
            return False
        
        ncr = self.ncrs[ncr_id]
        
        for action in ncr.corrective_actions:
            if action.id == action_id:
                action.status = 'completed'
                action.completed_at = datetime.utcnow()
                action.evidence = evidence or []
                
                # Check if all actions complete
                if all(a.status == 'completed' for a in ncr.corrective_actions):
                    self.transition_status(ncr_id, NCRStatus.VERIFICATION, user_id)
                
                return True
        
        return False
    
    def get_ncr(self, ncr_id: str) -> Optional[NCR]:
        """Get NCR by ID"""
        return self.ncrs.get(ncr_id)
    
    def get_project_ncrs(
        self,
        project_id: str,
        status: NCRStatus = None
    ) -> List[NCR]:
        """Get NCRs for a project"""
        ncrs = [n for n in self.ncrs.values() if n.project_id == project_id]
        
        if status:
            ncrs = [n for n in ncrs if n.status == status]
        
        return sorted(ncrs, key=lambda x: x.reported_at, reverse=True)
    
    def get_open_ncrs(self, project_id: str = None) -> List[NCR]:
        """Get open NCRs"""
        ncrs = [n for n in self.ncrs.values() if n.status != NCRStatus.CLOSED]
        
        if project_id:
            ncrs = [n for n in ncrs if n.project_id == project_id]
        
        return ncrs
    
    def get_ncr_summary(self, project_id: str = None) -> Dict[str, Any]:
        """Get NCR summary statistics"""
        ncrs = self.ncrs.values()
        
        if project_id:
            ncrs = [n for n in ncrs if n.project_id == project_id]
        
        total = len(ncrs)
        open_ncrs = sum(1 for n in ncrs if n.status == NCRStatus.OPEN)
        closed = sum(1 for n in ncrs if n.status == NCRStatus.CLOSED)
        
        by_category = {}
        for category in NCRCategory:
            count = sum(1 for n in ncrs if n.category == category)
            if count > 0:
                by_category[category.value] = count
        
        by_severity = {'minor': 0, 'major': 0, 'critical': 0}
        for n in ncrs:
            if n.severity in by_severity:
                by_severity[n.severity] += 1
        
        # Average resolution time
        resolved = [n for n in ncrs if n.closed_at]
        avg_resolution_days = 0
        if resolved:
            total_days = sum(
                (n.closed_at - n.reported_at).days
                for n in resolved
            )
            avg_resolution_days = total_days / len(resolved)
        
        return {
            'total_ncrs': total,
            'open': open_ncrs,
            'closed': closed,
            'closure_rate': (closed / total * 100) if total > 0 else 0,
            'by_category': by_category,
            'by_severity': by_severity,
            'avg_resolution_days': avg_resolution_days
        }


# Global NCR manager
ncr_manager = NCRManager()
