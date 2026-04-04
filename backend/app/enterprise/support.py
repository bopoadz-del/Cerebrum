"""
Enterprise Support Module - SLA Management and Support Channels
Item 290: SLA management and support channels
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import uuid
from app.db.base_class import Base

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Integer, Enum as SQLEnum, func, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from fastapi import HTTPException
from enum import Enum


class SupportTier(str, Enum):
    """Support tiers"""
    BASIC = "basic"
    STANDARD = "standard"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class TicketPriority(str, Enum):
    """Ticket priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TicketStatus(str, Enum):
    """Ticket status"""
    OPEN = "open"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    WAITING_CUSTOMER = "waiting_customer"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketCategory(str, Enum):
    """Ticket categories"""
    GENERAL = "general"
    TECHNICAL = "technical"
    BILLING = "billing"
    SECURITY = "security"
    FEATURE_REQUEST = "feature_request"
    BUG_REPORT = "bug_report"
    ACCOUNT = "account"
    INTEGRATION = "integration"


class SLALevel(str, Enum):
    """SLA response time levels"""
    P1 = "p1"  # Critical - 1 hour
    P2 = "p2"  # High - 4 hours
    P3 = "p3"  # Medium - 24 hours
    P4 = "p4"  # Low - 72 hours


# Database Models

class SupportPlan(Base):
    """Support plan configuration"""
    __tablename__ = 'support_plans'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, unique=True)
    
    # Plan details
    tier = Column(String(50), default=SupportTier.STANDARD.value)
    
    # SLA commitments
    response_time_p1 = Column(Integer, default=60)  # minutes
    response_time_p2 = Column(Integer, default=240)
    response_time_p3 = Column(Integer, default=1440)
    response_time_p4 = Column(Integer, default=4320)
    
    resolution_time_p1 = Column(Integer, default=240)
    resolution_time_p2 = Column(Integer, default=1440)
    resolution_time_p3 = Column(Integer, default=4320)
    resolution_time_p4 = Column(Integer, default=10080)
    
    # Support channels
    email_support = Column(Boolean, default=True)
    chat_support = Column(Boolean, default=False)
    phone_support = Column(Boolean, default=False)
    dedicated_rep = Column(Boolean, default=False)
    
    # Hours
    support_hours = Column(String(100), default='business')  # business, extended, 24x7
    
    # Limits
    max_tickets_per_month = Column(Integer, nullable=True)
    
    # Escalation
    auto_escalate = Column(Boolean, default=True)
    escalation_hours = Column(Integer, default=4)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SupportTicket(Base):
    """Support ticket"""
    __tablename__ = 'support_tickets'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    
    # Ticket info
    ticket_number = Column(String(50), unique=True, nullable=False)
    subject = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    
    # Categorization
    category = Column(String(50), default=TicketCategory.GENERAL.value)
    priority = Column(String(50), default=TicketPriority.MEDIUM.value)
    sla_level = Column(String(10), default=SLALevel.P3.value)
    
    # Status
    status = Column(String(50), default=TicketStatus.OPEN.value)
    
    # Assignment
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    assigned_team = Column(String(100), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # SLA tracking
    first_response_at = Column(DateTime, nullable=True)
    first_response_sla_met = Column(Boolean, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolution_sla_met = Column(Boolean, nullable=True)
    sla_due_at = Column(DateTime, nullable=True)
    
    # Resolution
    resolution_notes = Column(Text, nullable=True)
    satisfaction_rating = Column(Integer, nullable=True)
    
    # Metadata
    tags = Column(JSONB, default=list)
    source = Column(String(50), default='web')  # web, email, chat, phone, api
    internal_notes = Column(Text, nullable=True)
    
    __table_args__ = (
        Index('ix_tickets_tenant_status', 'tenant_id', 'status'),
        Index('ix_tickets_assigned', 'assigned_to', 'status'),
        Index('ix_tickets_sla_due', 'sla_due_at'),
    )


class TicketComment(Base):
    """Ticket comments/updates"""
    __tablename__ = 'ticket_comments'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey('support_tickets.id', ondelete='CASCADE'), nullable=False)
    
    author_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    author_type = Column(String(50), default='customer')  # customer, agent, system
    
    content = Column(Text, nullable=False)
    is_internal = Column(Boolean, default=False)
    
    # Attachments
    attachments = Column(JSONB, default=list)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class SupportAgent(Base):
    """Support agent configuration"""
    __tablename__ = 'support_agents'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, unique=True)
    
    # Agent details
    display_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    
    # Specialization
    specializations = Column(JSONB, default=list)  # ['technical', 'billing', 'security']
    languages = Column(JSONB, default=list)
    
    # Workload
    max_open_tickets = Column(Integer, default=10)
    current_open_tickets = Column(Integer, default=0)
    
    # Schedule
    timezone = Column(String(100), default='UTC')
    working_hours = Column(JSONB, default=dict)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_available = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class SLAReport(Base):
    """SLA compliance reporting"""
    __tablename__ = 'sla_reports'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True)
    
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Metrics
    total_tickets = Column(Integer, default=0)
    tickets_by_priority = Column(JSONB, default=dict)
    tickets_by_category = Column(JSONB, default=dict)
    
    # SLA performance
    first_response_sla_met = Column(Integer, default=0)
    first_response_sla_missed = Column(Integer, default=0)
    resolution_sla_met = Column(Integer, default=0)
    resolution_sla_missed = Column(Integer, default=0)
    
    # Average times (in minutes)
    avg_first_response_time = Column(Integer, nullable=True)
    avg_resolution_time = Column(Integer, nullable=True)
    
    # Satisfaction
    satisfaction_scores = Column(JSONB, default=list)
    avg_satisfaction = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


# Pydantic Schemas

class SupportPlanConfigRequest(BaseModel):
    """Configure support plan"""
    tier: SupportTier
    response_time_p1: int = 60
    response_time_p2: int = 240
    response_time_p3: int = 1440
    response_time_p4: int = 4320
    email_support: bool = True
    chat_support: bool = False
    phone_support: bool = False
    dedicated_rep: bool = False
    support_hours: str = 'business'
    max_tickets_per_month: Optional[int] = None


class CreateTicketRequest(BaseModel):
    """Create support ticket"""
    subject: str = Field(..., min_length=5, max_length=500)
    description: str = Field(..., min_length=10)
    category: TicketCategory = TicketCategory.GENERAL
    priority: TicketPriority = TicketPriority.MEDIUM
    attachments: List[Dict[str, str]] = Field(default_factory=list)


class UpdateTicketRequest(BaseModel):
    """Update support ticket"""
    status: Optional[TicketStatus] = None
    priority: Optional[TicketPriority] = None
    assigned_to: Optional[str] = None
    internal_notes: Optional[str] = None


class AddCommentRequest(BaseModel):
    """Add comment to ticket"""
    content: str = Field(..., min_length=1)
    is_internal: bool = False
    attachments: List[Dict[str, str]] = Field(default_factory=list)


class TicketResponse(BaseModel):
    """Ticket response"""
    id: str
    ticket_number: str
    subject: str
    status: str
    priority: str
    category: str
    created_at: datetime
    sla_due_at: Optional[datetime]


# Service Classes

class SupportService:
    """Service for support ticket management"""
    
    PRIORITY_TO_SLA = {
        TicketPriority.CRITICAL: SLALevel.P1,
        TicketPriority.HIGH: SLALevel.P2,
        TicketPriority.MEDIUM: SLALevel.P3,
        TicketPriority.LOW: SLALevel.P4
    }
    
    SLA_RESPONSE_TIMES = {
        SLALevel.P1: 60,      # 1 hour
        SLALevel.P2: 240,     # 4 hours
        SLALevel.P3: 1440,    # 24 hours
        SLALevel.P4: 4320     # 72 hours
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def _generate_ticket_number(self) -> str:
        """Generate unique ticket number"""
        prefix = "SUP"
        timestamp = datetime.utcnow().strftime('%Y%m%d')
        random_suffix = str(uuid.uuid4().hex[:6]).upper()
        return f"{prefix}-{timestamp}-{random_suffix}"
    
    def create_ticket(
        self,
        tenant_id: str,
        user_id: str,
        request: CreateTicketRequest
    ) -> SupportTicket:
        """Create new support ticket"""
        
        # Determine SLA level
        sla_level = self.PRIORITY_TO_SLA.get(request.priority, SLALevel.P3)
        
        # Calculate SLA due time
        response_minutes = self.SLA_RESPONSE_TIMES[sla_level]
        sla_due_at = datetime.utcnow() + timedelta(minutes=response_minutes)
        
        ticket = SupportTicket(
            tenant_id=tenant_id,
            ticket_number=self._generate_ticket_number(),
            subject=request.subject,
            description=request.description,
            category=request.category.value,
            priority=request.priority.value,
            sla_level=sla_level.value,
            created_by=user_id,
            sla_due_at=sla_due_at,
            tags=[request.category.value]
        )
        
        self.db.add(ticket)
        self.db.commit()
        self.db.refresh(ticket)
        
        # Try auto-assignment
        self._auto_assign_ticket(ticket)
        
        return ticket
    
    def _auto_assign_ticket(self, ticket: SupportTicket):
        """Auto-assign ticket to available agent"""
        
        # Find available agent with matching specialization
        agent = self.db.query(SupportAgent).filter(
            SupportAgent.is_active == True,
            SupportAgent.is_available == True,
            SupportAgent.current_open_tickets < SupportAgent.max_open_tickets
        ).order_by(SupportAgent.current_open_tickets).first()
        
        if agent:
            ticket.assigned_to = agent.user_id
            ticket.status = TicketStatus.ASSIGNED.value
            ticket.assigned_team = agent.specializations[0] if agent.specializations else 'general'
            
            # Update agent workload
            agent.current_open_tickets += 1
            
            self.db.commit()
    
    def get_ticket(self, ticket_id: str) -> Optional[SupportTicket]:
        """Get ticket by ID"""
        return self.db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    
    def get_ticket_by_number(self, ticket_number: str) -> Optional[SupportTicket]:
        """Get ticket by number"""
        return self.db.query(SupportTicket).filter(
            SupportTicket.ticket_number == ticket_number
        ).first()
    
    def list_tickets(
        self,
        tenant_id: str,
        status: Optional[TicketStatus] = None,
        priority: Optional[TicketPriority] = None,
        assigned_to: Optional[str] = None,
        created_by: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> tuple:
        """List tickets with filters"""
        
        query = self.db.query(SupportTicket).filter(
            SupportTicket.tenant_id == tenant_id
        )
        
        if status:
            query = query.filter(SupportTicket.status == status.value)
        
        if priority:
            query = query.filter(SupportTicket.priority == priority.value)
        
        if assigned_to:
            query = query.filter(SupportTicket.assigned_to == assigned_to)
        
        if created_by:
            query = query.filter(SupportTicket.created_by == created_by)
        
        total = query.count()
        
        tickets = query.order_by(SupportTicket.created_at.desc()).offset(
            offset
        ).limit(limit).all()
        
        return tickets, total
    
    def update_ticket(
        self,
        ticket_id: str,
        request: UpdateTicketRequest,
        updated_by: str
    ) -> SupportTicket:
        """Update ticket"""
        
        ticket = self.get_ticket(ticket_id)
        if not ticket:
            raise HTTPException(404, "Ticket not found")
        
        old_status = ticket.status
        
        if request.status:
            ticket.status = request.status.value
            
            # Track resolution
            if request.status == TicketStatus.RESOLVED:
                ticket.resolved_at = datetime.utcnow()
                
                # Check SLA
                if ticket.sla_due_at:
                    ticket.resolution_sla_met = datetime.utcnow() <= ticket.sla_due_at
            
            # Update agent workload
            if old_status != TicketStatus.RESOLVED.value and request.status == TicketStatus.RESOLVED:
                if ticket.assigned_to:
                    agent = self.db.query(SupportAgent).filter(
                        SupportAgent.user_id == ticket.assigned_to
                    ).first()
                    if agent:
                        agent.current_open_tickets = max(0, agent.current_open_tickets - 1)
        
        if request.priority:
            ticket.priority = request.priority.value
            ticket.sla_level = self.PRIORITY_TO_SLA.get(request.priority, SLALevel.P3).value
            
            # Recalculate SLA
            response_minutes = self.SLA_RESPONSE_TIMES[SLALevel(ticket.sla_level)]
            ticket.sla_due_at = ticket.created_at + timedelta(minutes=response_minutes)
        
        if request.assigned_to:
            ticket.assigned_to = request.assigned_to
            ticket.status = TicketStatus.ASSIGNED.value
        
        if request.internal_notes:
            ticket.internal_notes = request.internal_notes
        
        self.db.commit()
        self.db.refresh(ticket)
        
        return ticket
    
    def add_comment(
        self,
        ticket_id: str,
        user_id: str,
        request: AddCommentRequest
    ) -> TicketComment:
        """Add comment to ticket"""
        
        ticket = self.get_ticket(ticket_id)
        if not ticket:
            raise HTTPException(404, "Ticket not found")
        
        # Check if this is first response
        is_agent = self.db.query(SupportAgent).filter(
            SupportAgent.user_id == user_id
        ).first() is not None
        
        if is_agent and not ticket.first_response_at:
            ticket.first_response_at = datetime.utcnow()
            ticket.first_response_sla_met = datetime.utcnow() <= ticket.sla_due_at if ticket.sla_due_at else True
        
        comment = TicketComment(
            ticket_id=ticket_id,
            author_id=user_id,
            author_type='agent' if is_agent else 'customer',
            content=request.content,
            is_internal=request.is_internal,
            attachments=request.attachments
        )
        
        self.db.add(comment)
        self.db.commit()
        self.db.refresh(comment)
        
        return comment
    
    def get_sla_metrics(self, tenant_id: str, days: int = 30) -> Dict[str, Any]:
        """Get SLA metrics for tenant"""
        
        since = datetime.utcnow() - timedelta(days=days)
        
        tickets = self.db.query(SupportTicket).filter(
            SupportTicket.tenant_id == tenant_id,
            SupportTicket.created_at >= since
        ).all()
        
        total = len(tickets)
        
        if total == 0:
            return {
                'total_tickets': 0,
                'first_response_sla_met': 0,
                'first_response_sla_missed': 0,
                'resolution_sla_met': 0,
                'resolution_sla_missed': 0,
                'first_response_rate': 0,
                'resolution_rate': 0
            }
        
        first_response_met = sum(1 for t in tickets if t.first_response_sla_met == True)
        first_response_missed = sum(1 for t in tickets if t.first_response_sla_met == False)
        
        resolution_met = sum(1 for t in tickets if t.resolution_sla_met == True)
        resolution_missed = sum(1 for t in tickets if t.resolution_sla_met == False)
        
        return {
            'total_tickets': total,
            'first_response_sla_met': first_response_met,
            'first_response_sla_missed': first_response_missed,
            'resolution_sla_met': resolution_met,
            'resolution_sla_missed': resolution_missed,
            'first_response_rate': (first_response_met / total * 100) if total > 0 else 0,
            'resolution_rate': (resolution_met / total * 100) if total > 0 else 0
        }


class SupportPlanService:
    """Service for support plan management"""
    
    DEFAULT_PLANS = {
        SupportTier.BASIC: {
            'response_time_p1': 240,
            'response_time_p2': 480,
            'response_time_p3': 2880,
            'response_time_p4': 10080,
            'email_support': True,
            'chat_support': False,
            'phone_support': False,
            'dedicated_rep': False,
            'support_hours': 'business'
        },
        SupportTier.STANDARD: {
            'response_time_p1': 120,
            'response_time_p2': 240,
            'response_time_p3': 1440,
            'response_time_p4': 4320,
            'email_support': True,
            'chat_support': True,
            'phone_support': False,
            'dedicated_rep': False,
            'support_hours': 'extended'
        },
        SupportTier.PREMIUM: {
            'response_time_p1': 60,
            'response_time_p2': 120,
            'response_time_p3': 480,
            'response_time_p4': 1440,
            'email_support': True,
            'chat_support': True,
            'phone_support': True,
            'dedicated_rep': True,
            'support_hours': '24x7'
        },
        SupportTier.ENTERPRISE: {
            'response_time_p1': 30,
            'response_time_p2': 60,
            'response_time_p3': 240,
            'response_time_p4': 480,
            'email_support': True,
            'chat_support': True,
            'phone_support': True,
            'dedicated_rep': True,
            'support_hours': '24x7'
        }
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_or_create_plan(self, tenant_id: str) -> SupportPlan:
        """Get or create support plan for tenant"""
        
        plan = self.db.query(SupportPlan).filter(
            SupportPlan.tenant_id == tenant_id
        ).first()
        
        if not plan:
            # Create default plan
            defaults = self.DEFAULT_PLANS[SupportTier.STANDARD]
            plan = SupportPlan(tenant_id=tenant_id, **defaults)
            self.db.add(plan)
            self.db.commit()
            self.db.refresh(plan)
        
        return plan
    
    def update_plan(
        self,
        tenant_id: str,
        request: SupportPlanConfigRequest
    ) -> SupportPlan:
        """Update support plan"""
        
        plan = self.get_or_create_plan(tenant_id)
        
        plan.tier = request.tier.value
        plan.response_time_p1 = request.response_time_p1
        plan.response_time_p2 = request.response_time_p2
        plan.response_time_p3 = request.response_time_p3
        plan.response_time_p4 = request.response_time_p4
        plan.email_support = request.email_support
        plan.chat_support = request.chat_support
        plan.phone_support = request.phone_support
        plan.dedicated_rep = request.dedicated_rep
        plan.support_hours = request.support_hours
        plan.max_tickets_per_month = request.max_tickets_per_month
        
        self.db.commit()
        self.db.refresh(plan)
        
        return plan


# Export
__all__ = [
    'SupportTier',
    'TicketPriority',
    'TicketStatus',
    'TicketCategory',
    'SLALevel',
    'SupportPlan',
    'SupportTicket',
    'TicketComment',
    'SupportAgent',
    'SLAReport',
    'SupportPlanConfigRequest',
    'CreateTicketRequest',
    'UpdateTicketRequest',
    'AddCommentRequest',
    'TicketResponse',
    'SupportService',
    'SupportPlanService'
]
