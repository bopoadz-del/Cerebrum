"""
4D BIM - Schedule Integration with Gantt Visualization
Links 3D model elements to construction schedule for 4D simulation.
"""
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from enum import Enum
import uuid
import json
import logging

from .federated_models import ModelElement, FederatedModel

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Construction task statuses."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DELAYED = "delayed"
    ON_HOLD = "on_hold"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    """Types of construction tasks."""
    FOUNDATION = "foundation"
    STRUCTURE = "structure"
    MEP_ROUGH = "mep_rough"
    ENVELOPE = "envelope"
    INTERIOR = "interior"
    MEP_FINISH = "mep_finish"
    FINISHES = "finishes"
    LANDSCAPE = "landscape"
    COMMISSIONING = "commissioning"
    INSPECTION = "inspection"


@dataclass
class TaskDependency:
    """Dependency between tasks."""
    predecessor_id: str
    successor_id: str
    dependency_type: str = "FS"  # FS, SS, FF, SF
    lag_days: int = 0


@dataclass
class ConstructionTask:
    """Represents a construction schedule task."""
    id: str
    name: str
    wbs_code: str  # Work Breakdown Structure code
    task_type: TaskType
    start_date: date
    end_date: date
    duration_days: int
    status: TaskStatus = TaskStatus.NOT_STARTED
    percent_complete: float = 0.0
    assigned_crew: Optional[str] = None
    assigned_resources: List[str] = field(default_factory=list)
    predecessor_ids: List[str] = field(default_factory=list)
    successor_ids: List[str] = field(default_factory=list)
    linked_element_ids: List[str] = field(default_factory=list)
    budget_hours: float = 0.0
    actual_hours: float = 0.0
    cost_budget: float = 0.0
    cost_actual: float = 0.0
    notes: str = ""
    critical_path: bool = False
    float_days: float = 0.0
    
    @property
    def is_on_critical_path(self) -> bool:
        return self.critical_path
    
    @property
    def is_overdue(self) -> bool:
        return self.end_date < date.today() and self.status != TaskStatus.COMPLETED
    
    @property
    def remaining_duration(self) -> int:
        """Calculate remaining duration based on completion."""
        if self.status == TaskStatus.COMPLETED:
            return 0
        return int(self.duration_days * (1 - self.percent_complete / 100))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'wbs_code': self.wbs_code,
            'task_type': self.task_type.value,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'duration_days': self.duration_days,
            'status': self.status.value,
            'percent_complete': self.percent_complete,
            'assigned_crew': self.assigned_crew,
            'linked_elements': len(self.linked_element_ids),
            'critical_path': self.critical_path,
            'float_days': self.float_days,
            'is_overdue': self.is_overdue
        }


@dataclass
class Schedule4D:
    """4D schedule linked to BIM model."""
    id: str
    name: str
    project_id: str
    federated_model_id: str
    tasks: List[ConstructionTask] = field(default_factory=list)
    dependencies: List[TaskDependency] = field(default_factory=list)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    baseline_date: Optional[date] = None
    
    @property
    def total_tasks(self) -> int:
        return len(self.tasks)
    
    @property
    def completed_tasks(self) -> int:
        return sum(1 for t in self.tasks if t.status == TaskStatus.COMPLETED)
    
    @property
    def overall_progress(self) -> float:
        """Calculate overall project progress."""
        if not self.tasks:
            return 0.0
        total_duration = sum(t.duration_days for t in self.tasks)
        completed_duration = sum(
            t.duration_days * t.percent_complete / 100 
            for t in self.tasks
        )
        return (completed_duration / total_duration * 100) if total_duration > 0 else 0.0
    
    @property
    def critical_path_tasks(self) -> List[ConstructionTask]:
        """Get tasks on the critical path."""
        return [t for t in self.tasks if t.critical_path]
    
    def get_task_by_id(self, task_id: str) -> Optional[ConstructionTask]:
        """Get task by ID."""
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None
    
    def get_tasks_by_date(self, target_date: date) -> List[ConstructionTask]:
        """Get tasks active on a specific date."""
        return [
            t for t in self.tasks
            if t.start_date <= target_date <= t.end_date
        ]
    
    def get_tasks_by_element(self, element_id: str) -> List[ConstructionTask]:
        """Get tasks linked to a specific element."""
        return [
            t for t in self.tasks
            if element_id in t.linked_element_ids
        ]
    
    def get_elements_for_date(self, target_date: date,
                              federated_model: FederatedModel) -> List[ModelElement]:
        """Get model elements that should be visible on a specific date."""
        active_tasks = self.get_tasks_by_date(target_date)
        element_ids = set()
        
        for task in active_tasks:
            if task.status in [TaskStatus.COMPLETED, TaskStatus.IN_PROGRESS]:
                element_ids.update(task.linked_element_ids)
        
        elements = []
        for element in federated_model.get_all_elements():
            if element.id in element_ids:
                elements.append(element)
        
        return elements
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'project_id': self.project_id,
            'federated_model_id': self.federated_model_id,
            'total_tasks': self.total_tasks,
            'completed_tasks': self.completed_tasks,
            'overall_progress': self.overall_progress,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'tasks': [t.to_dict() for t in self.tasks]
        }


class GanttChartGenerator:
    """Generates Gantt chart data for schedule visualization."""
    
    def __init__(self, schedule: Schedule4D):
        self.schedule = schedule
    
    def generate_chart_data(self) -> Dict[str, Any]:
        """Generate data for Gantt chart visualization."""
        tasks = []
        links = []
        
        for task in self.schedule.tasks:
            task_data = {
                'id': task.id,
                'text': task.name,
                'start_date': task.start_date.isoformat(),
                'end_date': task.end_date.isoformat(),
                'duration': task.duration_days,
                'progress': task.percent_complete / 100,
                'open': True,
                'type': 'task',
                'status': task.status.value,
                'critical': task.critical_path,
                'wbs': task.wbs_code,
                'task_type': task.task_type.value
            }
            
            # Color based on status
            if task.status == TaskStatus.COMPLETED:
                task_data['color'] = '#22C55E'  # Green
            elif task.status == TaskStatus.IN_PROGRESS:
                task_data['color'] = '#3B82F6'  # Blue
            elif task.is_overdue:
                task_data['color'] = '#EF4444'  # Red
            elif task.critical_path:
                task_data['color'] = '#F59E0B'  # Orange
            else:
                task_data['color'] = '#6B7280'  # Gray
            
            tasks.append(task_data)
        
        # Generate dependency links
        for dep in self.schedule.dependencies:
            links.append({
                'id': f"{dep.predecessor_id}-{dep.successor_id}",
                'source': dep.predecessor_id,
                'target': dep.successor_id,
                'type': dep.dependency_type,
                'lag': dep.lag_days
            })
        
        return {
            'data': tasks,
            'links': links
        }
    
    def generate_timeline_data(self, 
                               start_date: Optional[date] = None,
                               end_date: Optional[date] = None,
                               granularity: str = "weekly") -> List[Dict[str, Any]]:
        """Generate timeline data for animation."""
        if not start_date:
            start_date = min(t.start_date for t in self.schedule.tasks) if self.schedule.tasks else date.today()
        if not end_date:
            end_date = max(t.end_date for t in self.schedule.tasks) if self.schedule.tasks else date.today()
        
        timeline = []
        current_date = start_date
        
        delta = timedelta(days=7 if granularity == "weekly" else 1)
        
        while current_date <= end_date:
            active_tasks = self.schedule.get_tasks_by_date(current_date)
            
            timeline.append({
                'date': current_date.isoformat(),
                'active_tasks': len(active_tasks),
                'tasks': [t.name for t in active_tasks],
                'progress': self._calculate_progress_on_date(current_date),
                'completed_elements': sum(
                    len(t.linked_element_ids) 
                    for t in active_tasks 
                    if t.status == TaskStatus.COMPLETED
                )
            })
            
            current_date += delta
        
        return timeline
    
    def _calculate_progress_on_date(self, target_date: date) -> float:
        """Calculate project progress on a specific date."""
        total_duration = sum(t.duration_days for t in self.schedule.tasks)
        if total_duration == 0:
            return 0.0
        
        completed_duration = 0.0
        for task in self.schedule.tasks:
            if task.end_date < target_date:
                completed_duration += task.duration_days
            elif task.start_date <= target_date <= task.end_date:
                # Partial completion
                days_elapsed = (target_date - task.start_date).days
                completed_duration += days_elapsed
        
        return (completed_duration / total_duration * 100)
    
    def generate_critical_path_data(self) -> Dict[str, Any]:
        """Generate critical path visualization data."""
        cp_tasks = self.schedule.critical_path_tasks
        
        return {
            'critical_path_length': len(cp_tasks),
            'total_duration': sum(t.duration_days for t in cp_tasks),
            'tasks': [
                {
                    'id': t.id,
                    'name': t.name,
                    'start': t.start_date.isoformat(),
                    'end': t.end_date.isoformat(),
                    'duration': t.duration_days,
                    'float': t.float_days
                }
                for t in sorted(cp_tasks, key=lambda x: x.start_date)
            ]
        }


class Schedule4DEngine:
    """Engine for 4D schedule management and simulation."""
    
    def __init__(self):
        self.schedules: Dict[str, Schedule4D] = {}
    
    def create_schedule(self, name: str, project_id: str,
                       federated_model_id: str) -> Schedule4D:
        """Create a new 4D schedule."""
        schedule = Schedule4D(
            id=str(uuid.uuid4()),
            name=name,
            project_id=project_id,
            federated_model_id=federated_model_id
        )
        self.schedules[schedule.id] = schedule
        logger.info(f"Created 4D schedule: {name}")
        return schedule
    
    def add_task(self, schedule_id: str, task: ConstructionTask) -> bool:
        """Add a task to a schedule."""
        schedule = self.schedules.get(schedule_id)
        if not schedule:
            return False
        
        schedule.tasks.append(task)
        schedule.updated_at = datetime.utcnow()
        
        # Update schedule dates
        self._update_schedule_dates(schedule)
        
        return True
    
    def link_element_to_task(self, schedule_id: str, task_id: str,
                            element_id: str) -> bool:
        """Link a BIM element to a construction task."""
        schedule = self.schedules.get(schedule_id)
        if not schedule:
            return False
        
        task = schedule.get_task_by_id(task_id)
        if not task:
            return False
        
        if element_id not in task.linked_element_ids:
            task.linked_element_ids.append(element_id)
        
        schedule.updated_at = datetime.utcnow()
        return True
    
    def update_task_progress(self, schedule_id: str, task_id: str,
                            percent_complete: float) -> bool:
        """Update task completion percentage."""
        schedule = self.schedules.get(schedule_id)
        if not schedule:
            return False
        
        task = schedule.get_task_by_id(task_id)
        if not task:
            return False
        
        task.percent_complete = min(100.0, max(0.0, percent_complete))
        
        # Update status based on progress
        if task.percent_complete >= 100:
            task.status = TaskStatus.COMPLETED
        elif task.percent_complete > 0:
            task.status = TaskStatus.IN_PROGRESS
        
        schedule.updated_at = datetime.utcnow()
        return True
    
    def calculate_critical_path(self, schedule_id: str) -> List[str]:
        """Calculate critical path using forward/backward pass."""
        schedule = self.schedules.get(schedule_id)
        if not schedule:
            return []
        
        # Simplified critical path calculation
        # In production, use proper CPM algorithm
        
        # Reset critical path flags
        for task in schedule.tasks:
            task.critical_path = False
        
        # Find tasks with zero float (simplified)
        for task in schedule.tasks:
            if task.float_days == 0:
                task.critical_path = True
        
        return [t.id for t in schedule.tasks if t.critical_path]
    
    def simulate_construction(self, schedule_id: str,
                             start_date: Optional[date] = None,
                             speed_factor: float = 1.0) -> Dict[str, Any]:
        """Simulate construction progress over time."""
        schedule = self.schedules.get(schedule_id)
        if not schedule:
            return {}
        
        generator = GanttChartGenerator(schedule)
        
        return {
            'schedule_id': schedule_id,
            'timeline': generator.generate_timeline_data(start_date=start_date),
            'gantt_data': generator.generate_chart_data(),
            'critical_path': generator.generate_critical_path_data()
        }
    
    def _update_schedule_dates(self, schedule: Schedule4D):
        """Update overall schedule dates based on tasks."""
        if schedule.tasks:
            schedule.start_date = min(t.start_date for t in schedule.tasks)
            schedule.end_date = max(t.end_date for t in schedule.tasks)
    
    def export_to_microsoft_project(self, schedule_id: str) -> bytes:
        """Export schedule to Microsoft Project format."""
        # Placeholder - would generate XML for MS Project
        schedule = self.schedules.get(schedule_id)
        if not schedule:
            return b""
        
        xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<Project xmlns="http://schemas.microsoft.com/project">
    <Name>{schedule.name}</Name>
    <Tasks>
"""
        for task in schedule.tasks:
            xml_content += f"""        <Task>
            <UID>{task.id}</UID>
            <Name>{task.name}</Name>
            <WBS>{task.wbs_code}</WBS>
            <Start>{task.start_date.isoformat()}</Start>
            <Finish>{task.end_date.isoformat()}</Finish>
            <Duration>PT{task.duration_days * 8}H0M0S</Duration>
            <PercentComplete>{int(task.percent_complete)}</PercentComplete>
        </Task>
"""
        
        xml_content += """    </Tasks>
</Project>"""
        
        return xml_content.encode('utf-8')
    
    def export_to_p6(self, schedule_id: str) -> bytes:
        """Export schedule to Primavera P6 format."""
        # Placeholder - would generate XER file
        return b""


# Convenience functions
def create_sample_schedule(project_id: str, 
                          federated_model_id: str) -> Schedule4D:
    """Create a sample 4D schedule for testing."""
    engine = Schedule4DEngine()
    schedule = engine.create_schedule("Sample Construction Schedule", 
                                     project_id, federated_model_id)
    
    # Add sample tasks
    base_date = date.today()
    
    tasks = [
        ConstructionTask(
            id=str(uuid.uuid4()),
            name="Foundation Excavation",
            wbs_code="1.1",
            task_type=TaskType.FOUNDATION,
            start_date=base_date,
            end_date=base_date + timedelta(days=14),
            duration_days=14
        ),
        ConstructionTask(
            id=str(uuid.uuid4()),
            name="Foundation Concrete",
            wbs_code="1.2",
            task_type=TaskType.FOUNDATION,
            start_date=base_date + timedelta(days=14),
            end_date=base_date + timedelta(days=28),
            duration_days=14,
            predecessor_ids=[]  # Would link to excavation
        ),
        ConstructionTask(
            id=str(uuid.uuid4()),
            name="Structural Steel",
            wbs_code="2.1",
            task_type=TaskType.STRUCTURE,
            start_date=base_date + timedelta(days=28),
            end_date=base_date + timedelta(days=70),
            duration_days=42
        ),
    ]
    
    for task in tasks:
        engine.add_task(schedule.id, task)
    
    return schedule
