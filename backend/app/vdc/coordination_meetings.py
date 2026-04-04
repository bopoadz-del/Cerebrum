"""
Coordination Meetings - Clash Review Workflow
Meeting management and clash resolution workflow
"""
import json
import logging
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from uuid import uuid4

logger = logging.getLogger(__name__)


class MeetingStatus(Enum):
    """Meeting status"""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"


class ClashResolutionStatus(Enum):
    """Clash resolution status in meeting"""
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    ASSIGNED = "assigned"
    RESOLVED = "resolved"
    APPROVED = "approved"
    DEFERRED = "deferred"
    DISPUTED = "disputed"


@dataclass
class MeetingAttendee:
    """Meeting attendee"""
    user_id: str
    name: str
    discipline: str
    company: str
    email: str
    role: str = "attendee"  # attendee, chair, secretary
    rsvp_status: str = "pending"  # pending, accepted, declined, tentative
    attended: bool = False


@dataclass
class MeetingAgendaItem:
    """Agenda item for coordination meeting"""
    item_id: str
    title: str
    description: str
    clash_id: Optional[str] = None
    discipline_a: str = ""
    discipline_b: str = ""
    estimated_duration_minutes: int = 10
    presenter_id: Optional[str] = None
    status: str = "open"
    resolution: str = ""
    action_items: List[Dict] = field(default_factory=list)
    attachments: List[str] = field(default_factory=list)


@dataclass
class CoordinationMeeting:
    """Coordination meeting"""
    meeting_id: str
    project_id: str
    federation_id: str
    title: str
    description: str
    scheduled_at: datetime
    duration_minutes: int = 60
    location: str = ""
    virtual_meeting_link: str = ""
    status: MeetingStatus = MeetingStatus.SCHEDULED
    chair_id: Optional[str] = None
    secretary_id: Optional[str] = None
    attendees: List[MeetingAttendee] = field(default_factory=list)
    agenda: List[MeetingAgendaItem] = field(default_factory=list)
    clash_ids: List[str] = field(default_factory=list)
    meeting_minutes: str = ""
    recording_url: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = ""


@dataclass
class ActionItem:
    """Action item from meeting"""
    action_id: str
    meeting_id: str
    description: str
    assigned_to: str
    discipline: str
    due_date: datetime
    status: str = "open"  # open, in_progress, completed, overdue
    priority: str = "medium"  # low, medium, high, critical
    related_clash_id: Optional[str] = None
    related_agenda_item: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    notes: str = ""


class MeetingScheduler:
    """Schedules coordination meetings"""
    
    def __init__(self):
        self._meetings: Dict[str, CoordinationMeeting] = {}
        self._recurring_schedules: Dict[str, Dict] = {}
    
    def schedule_meeting(self, project_id: str,
                         federation_id: str,
                         title: str,
                         scheduled_at: datetime,
                         duration_minutes: int = 60,
                         created_by: str = "") -> CoordinationMeeting:
        """Schedule new coordination meeting"""
        meeting = CoordinationMeeting(
            meeting_id=str(uuid4()),
            project_id=project_id,
            federation_id=federation_id,
            title=title,
            description="Weekly coordination meeting",
            scheduled_at=scheduled_at,
            duration_minutes=duration_minutes,
            created_by=created_by
        )
        
        self._meetings[meeting.meeting_id] = meeting
        
        logger.info(f"Scheduled meeting: {meeting.meeting_id}")
        
        return meeting
    
    def set_recurring_schedule(self, project_id: str,
                               federation_id: str,
                               frequency: str,  # weekly, biweekly, monthly
                               day_of_week: int,  # 0=Monday
                               time: str,  # HH:MM
                               duration_minutes: int = 60):
        """Set recurring meeting schedule"""
        schedule_id = f"{project_id}:{federation_id}"
        
        self._recurring_schedules[schedule_id] = {
            'project_id': project_id,
            'federation_id': federation_id,
            'frequency': frequency,
            'day_of_week': day_of_week,
            'time': time,
            'duration_minutes': duration_minutes
        }
    
    def generate_next_meeting(self, schedule_id: str) -> CoordinationMeeting:
        """Generate next meeting from recurring schedule"""
        schedule = self._recurring_schedules.get(schedule_id)
        if not schedule:
            raise ValueError(f"Schedule not found: {schedule_id}")
        
        # Calculate next occurrence
        now = datetime.utcnow()
        days_until = (schedule['day_of_week'] - now.weekday()) % 7
        if days_until == 0:
            days_until = 7  # Next week
        
        next_date = now + timedelta(days=days_until)
        hour, minute = map(int, schedule['time'].split(':'))
        scheduled_at = next_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        return self.schedule_meeting(
            project_id=schedule['project_id'],
            federation_id=schedule['federation_id'],
            title=f"Weekly Coordination Meeting",
            scheduled_at=scheduled_at,
            duration_minutes=schedule['duration_minutes']
        )
    
    def add_attendee(self, meeting_id: str, 
                     attendee: MeetingAttendee) -> bool:
        """Add attendee to meeting"""
        meeting = self._meetings.get(meeting_id)
        if not meeting:
            return False
        
        meeting.attendees.append(attendee)
        return True
    
    def add_agenda_item(self, meeting_id: str,
                        item: MeetingAgendaItem) -> bool:
        """Add agenda item to meeting"""
        meeting = self._meetings.get(meeting_id)
        if not meeting:
            return False
        
        meeting.agenda.append(item)
        
        if item.clash_id:
            meeting.clash_ids.append(item.clash_id)
        
        return True
    
    def get_meeting(self, meeting_id: str) -> Optional[CoordinationMeeting]:
        """Get meeting by ID"""
        return self._meetings.get(meeting_id)
    
    def get_upcoming_meetings(self, project_id: str = None) -> List[CoordinationMeeting]:
        """Get upcoming meetings"""
        now = datetime.utcnow()
        
        meetings = [
            m for m in self._meetings.values()
            if m.scheduled_at >= now
            and m.status in [MeetingStatus.SCHEDULED, MeetingStatus.RESCHEDULED]
        ]
        
        if project_id:
            meetings = [m for m in meetings if m.project_id == project_id]
        
        return sorted(meetings, key=lambda m: m.scheduled_at)


class ClashReviewWorkflow:
    """Manages clash review workflow"""
    
    def __init__(self):
        self._clash_status: Dict[str, Dict] = {}
        self._resolution_history: Dict[str, List[Dict]] = {}
    
    def assign_clash_to_meeting(self, clash_id: str,
                                 meeting_id: str,
                                 presenter_discipline: str) -> bool:
        """Assign clash to meeting for review"""
        self._clash_status[clash_id] = {
            'status': ClashResolutionStatus.PENDING,
            'meeting_id': meeting_id,
            'presenter_discipline': presenter_discipline,
            'assigned_at': datetime.utcnow().isoformat()
        }
        
        return True
    
    def record_resolution(self, clash_id: str,
                          meeting_id: str,
                          resolution: str,
                          action_items: List[Dict],
                          approved_by: List[str]) -> Dict:
        """Record clash resolution from meeting"""
        if clash_id not in self._clash_status:
            self._clash_status[clash_id] = {}
        
        status = self._clash_status[clash_id]
        status['status'] = ClashResolutionStatus.RESOLVED
        status['resolution'] = resolution
        status['meeting_id'] = meeting_id
        status['approved_by'] = approved_by
        status['resolved_at'] = datetime.utcnow().isoformat()
        
        # Log to history
        if clash_id not in self._resolution_history:
            self._resolution_history[clash_id] = []
        
        self._resolution_history[clash_id].append({
            'timestamp': datetime.utcnow().isoformat(),
            'meeting_id': meeting_id,
            'resolution': resolution,
            'action_items': action_items
        })
        
        return {
            'clash_id': clash_id,
            'status': 'resolved',
            'action_items_created': len(action_items)
        }
    
    def defer_clash(self, clash_id: str,
                    meeting_id: str,
                    reason: str,
                    defer_until: datetime) -> Dict:
        """Defer clash to future meeting"""
        self._clash_status[clash_id] = {
            'status': ClashResolutionStatus.DEFERRED,
            'meeting_id': meeting_id,
            'reason': reason,
            'defer_until': defer_until.isoformat(),
            'deferred_at': datetime.utcnow().isoformat()
        }
        
        return {
            'clash_id': clash_id,
            'status': 'deferred',
            'defer_until': defer_until.isoformat()
        }
    
    def dispute_clash(self, clash_id: str,
                      meeting_id: str,
                      disputed_by: str,
                      reason: str) -> Dict:
        """Mark clash as disputed"""
        self._clash_status[clash_id] = {
            'status': ClashResolutionStatus.DISPUTED,
            'meeting_id': meeting_id,
            'disputed_by': disputed_by,
            'dispute_reason': reason,
            'disputed_at': datetime.utcnow().isoformat()
        }
        
        return {
            'clash_id': clash_id,
            'status': 'disputed',
            'requires_escalation': True
        }
    
    def get_clash_status(self, clash_id: str) -> Optional[Dict]:
        """Get clash resolution status"""
        return self._clash_status.get(clash_id)
    
    def get_resolution_history(self, clash_id: str) -> List[Dict]:
        """Get resolution history for clash"""
        return self._resolution_history.get(clash_id, [])


class ActionItemTracker:
    """Tracks action items from meetings"""
    
    def __init__(self):
        self._action_items: Dict[str, ActionItem] = {}
    
    def create_action_item(self, meeting_id: str,
                           description: str,
                           assigned_to: str,
                           discipline: str,
                           due_date: datetime,
                           priority: str = "medium",
                           related_clash_id: str = None) -> ActionItem:
        """Create new action item"""
        action = ActionItem(
            action_id=str(uuid4()),
            meeting_id=meeting_id,
            description=description,
            assigned_to=assigned_to,
            discipline=discipline,
            due_date=due_date,
            priority=priority,
            related_clash_id=related_clash_id
        )
        
        self._action_items[action.action_id] = action
        
        logger.info(f"Created action item: {action.action_id}")
        
        return action
    
    def update_status(self, action_id: str, 
                      new_status: str,
                      notes: str = "") -> bool:
        """Update action item status"""
        action = self._action_items.get(action_id)
        if not action:
            return False
        
        action.status = new_status
        
        if new_status == "completed":
            action.completed_at = datetime.utcnow()
        
        if notes:
            action.notes = notes
        
        return True
    
    def get_overdue_items(self) -> List[ActionItem]:
        """Get overdue action items"""
        now = datetime.utcnow()
        
        overdue = [
            item for item in self._action_items.values()
            if item.due_date < now
            and item.status in ["open", "in_progress"]
        ]
        
        # Update status
        for item in overdue:
            item.status = "overdue"
        
        return overdue
    
    def get_items_by_assignee(self, user_id: str) -> List[ActionItem]:
        """Get action items assigned to user"""
        return [
            item for item in self._action_items.values()
            if item.assigned_to == user_id
        ]
    
    def get_items_by_meeting(self, meeting_id: str) -> List[ActionItem]:
        """Get action items from meeting"""
        return [
            item for item in self._action_items.values()
            if item.meeting_id == meeting_id
        ]


class MeetingMinutesGenerator:
    """Generates meeting minutes"""
    
    def generate(self, meeting: CoordinationMeeting) -> str:
        """Generate meeting minutes document"""
        minutes = f"""
COORDINATION MEETING MINUTES
============================

Meeting: {meeting.title}
Date: {meeting.scheduled_at.strftime('%Y-%m-%d %H:%M')}
Location: {meeting.location or 'Virtual'}
Meeting ID: {meeting.meeting_id}

ATTENDEES
---------
"""
        
        for attendee in meeting.attendees:
            status = "✓" if attendee.attended else "✗"
            minutes += f"{status} {attendee.name} ({attendee.discipline}) - {attendee.company}\n"
        
        minutes += "\nAGENDA\n------\n"
        
        for i, item in enumerate(meeting.agenda, 1):
            minutes += f"\n{i}. {item.title}\n"
            minutes += f"   Description: {item.description}\n"
            if item.clash_id:
                minutes += f"   Related Clash: {item.clash_id}\n"
            minutes += f"   Status: {item.status}\n"
            if item.resolution:
                minutes += f"   Resolution: {item.resolution}\n"
        
        minutes += "\nACTION ITEMS\n------------\n"
        
        # Get action items for this meeting
        action_items = [
            item for item in action_tracker._action_items.values()
            if item.meeting_id == meeting.meeting_id
        ]
        
        for item in action_items:
            minutes += f"\n- {item.description}\n"
            minutes += f"  Assigned to: {item.assigned_to} ({item.discipline})\n"
            minutes += f"  Due: {item.due_date.strftime('%Y-%m-%d')}\n"
            minutes += f"  Priority: {item.priority}\n"
        
        minutes += f"\n\nGenerated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}\n"
        
        return minutes


# Global instances
meeting_scheduler = MeetingScheduler()
clash_workflow = ClashReviewWorkflow()
action_tracker = ActionItemTracker()
minutes_generator = MeetingMinutesGenerator()