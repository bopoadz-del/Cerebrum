"""
Inspection Management System
Digital inspection checklists for construction quality
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class InspectionStatus(Enum):
    """Inspection status"""
    SCHEDULED = 'scheduled'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    FAILED = 'failed'
    OVERDUE = 'overdue'


class InspectionType(Enum):
    """Types of inspections"""
    DAILY = 'daily'
    WEEKLY = 'weekly'
    MONTHLY = 'monthly'
    PHASE = 'phase'
    FINAL = 'final'
    SPECIAL = 'special'


@dataclass
class InspectionItem:
    """Individual inspection checklist item"""
    id: str
    description: str
    category: str
    required: bool = True
    response_type: str = 'pass_fail'  # pass_fail, numeric, text, photo
    standard_reference: Optional[str] = None
    photos_required: bool = False
    notes: Optional[str] = None


@dataclass
class InspectionResponse:
    """Response to inspection item"""
    item_id: str
    status: str  # pass, fail, na
    value: Optional[str] = None
    notes: Optional[str] = None
    photos: List[str] = field(default_factory=list)
    inspected_by: Optional[str] = None
    inspected_at: Optional[datetime] = None


@dataclass
class Inspection:
    """Inspection record"""
    id: str
    inspection_type: InspectionType
    title: str
    project_id: str
    location: str
    scheduled_date: datetime
    status: InspectionStatus
    checklist: List[InspectionItem]
    responses: List[InspectionResponse] = field(default_factory=list)
    inspector_id: Optional[str] = None
    reviewed_by: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None
    
    def get_completion_rate(self) -> float:
        """Get checklist completion rate"""
        if not self.checklist:
            return 0
        return len(self.responses) / len(self.checklist) * 100
    
    def get_pass_rate(self) -> float:
        """Get pass rate for completed items"""
        if not self.responses:
            return 0
        passed = sum(1 for r in self.responses if r.status == 'pass')
        return passed / len(self.responses) * 100


class InspectionManager:
    """Manage inspections"""
    
    def __init__(self):
        self.inspections: Dict[str, Inspection] = {}
        self.templates: Dict[str, List[InspectionItem]] = {}
        self._load_default_templates()
    
    def _load_default_templates(self):
        """Load default inspection templates"""
        # Daily site inspection
        self.templates['daily_site'] = [
            InspectionItem('ds_1', 'Site clean and organized', 'housekeeping'),
            InspectionItem('ds_2', 'PPE worn by all workers', 'safety'),
            InspectionItem('ds_3', 'Material storage secure', 'materials'),
            InspectionItem('ds_4', 'Equipment in good condition', 'equipment'),
            InspectionItem('ds_5', 'Access routes clear', 'access'),
        ]
        
        # Concrete placement inspection
        self.templates['concrete'] = [
            InspectionItem('conc_1', 'Formwork properly installed', 'formwork', photos_required=True),
            InspectionItem('conc_2', 'Rebar placed per drawings', 'rebar', photos_required=True),
            InspectionItem('conc_3', 'Concrete mix approved', 'materials'),
            InspectionItem('conc_4', 'Pour sequence approved', 'planning'),
            InspectionItem('conc_5', 'Curing plan in place', 'curing'),
        ]
        
        # Final inspection
        self.templates['final'] = [
            InspectionItem('fin_1', 'All work complete per drawings', 'completion', photos_required=True),
            InspectionItem('fin_2', 'Punch list items resolved', 'punch_list'),
            InspectionItem('fin_3', 'Cleanup complete', 'cleanup'),
            InspectionItem('fin_4', 'Documentation complete', 'docs'),
            InspectionItem('fin_5', 'Warranties provided', 'warranty'),
        ]
    
    def create_inspection(
        self,
        inspection_type: InspectionType,
        title: str,
        project_id: str,
        location: str,
        scheduled_date: datetime,
        template_name: str = None,
        custom_checklist: List[InspectionItem] = None
    ) -> Inspection:
        """Create new inspection"""
        inspection_id = f"INS-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        # Use template or custom checklist
        if template_name and template_name in self.templates:
            checklist = self.templates[template_name]
        elif custom_checklist:
            checklist = custom_checklist
        else:
            checklist = []
        
        inspection = Inspection(
            id=inspection_id,
            inspection_type=inspection_type,
            title=title,
            project_id=project_id,
            location=location,
            scheduled_date=scheduled_date,
            status=InspectionStatus.SCHEDULED,
            checklist=checklist
        )
        
        self.inspections[inspection_id] = inspection
        logger.info(f"Created inspection: {inspection_id}")
        
        return inspection
    
    def submit_response(
        self,
        inspection_id: str,
        item_id: str,
        status: str,
        value: str = None,
        notes: str = None,
        photos: List[str] = None,
        inspector_id: str = None
    ) -> bool:
        """Submit response to inspection item"""
        if inspection_id not in self.inspections:
            return False
        
        inspection = self.inspections[inspection_id]
        
        response = InspectionResponse(
            item_id=item_id,
            status=status,
            value=value,
            notes=notes,
            photos=photos or [],
            inspected_by=inspector_id,
            inspected_at=datetime.utcnow()
        )
        
        # Update existing response or add new
        existing = [i for i, r in enumerate(inspection.responses) if r.item_id == item_id]
        if existing:
            inspection.responses[existing[0]] = response
        else:
            inspection.responses.append(response)
        
        # Update inspection status
        if inspection.get_completion_rate() >= 100:
            inspection.status = InspectionStatus.COMPLETED
            inspection.completed_at = datetime.utcnow()
        elif inspection.responses:
            inspection.status = InspectionStatus.IN_PROGRESS
        
        return True
    
    def get_inspection(self, inspection_id: str) -> Optional[Inspection]:
        """Get inspection by ID"""
        return self.inspections.get(inspection_id)
    
    def get_project_inspections(
        self,
        project_id: str,
        status: InspectionStatus = None
    ) -> List[Inspection]:
        """Get inspections for a project"""
        inspections = [
            i for i in self.inspections.values()
            if i.project_id == project_id
        ]
        
        if status:
            inspections = [i for i in inspections if i.status == status]
        
        return sorted(inspections, key=lambda x: x.scheduled_date, reverse=True)
    
    def get_overdue_inspections(self) -> List[Inspection]:
        """Get overdue inspections"""
        now = datetime.utcnow()
        
        overdue = [
            i for i in self.inspections.values()
            if i.scheduled_date < now
            and i.status in [InspectionStatus.SCHEDULED, InspectionStatus.IN_PROGRESS]
        ]
        
        # Mark as overdue
        for inspection in overdue:
            inspection.status = InspectionStatus.OVERDUE
        
        return overdue
    
    def get_inspection_summary(self, project_id: str = None) -> Dict[str, Any]:
        """Get inspection summary"""
        inspections = self.inspections.values()
        
        if project_id:
            inspections = [i for i in inspections if i.project_id == project_id]
        
        total = len(inspections)
        completed = sum(1 for i in inspections if i.status == InspectionStatus.COMPLETED)
        failed = sum(1 for i in inspections if i.status == InspectionStatus.FAILED)
        overdue = sum(1 for i in inspections if i.status == InspectionStatus.OVERDUE)
        
        return {
            'total_inspections': total,
            'completed': completed,
            'failed': failed,
            'overdue': overdue,
            'completion_rate': (completed / total * 100) if total > 0 else 0,
            'average_pass_rate': sum(i.get_pass_rate() for i in inspections) / total if total > 0 else 0
        }


# Global inspection manager
inspection_manager = InspectionManager()
