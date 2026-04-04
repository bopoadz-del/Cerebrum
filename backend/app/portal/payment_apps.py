"""
Payment Applications Module - Schedule of Values and payment tracking
Item 326: Payment applications
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from fastapi import HTTPException
from enum import Enum

from app.db.base_class import Base


class PaymentAppStatus(str, Enum):
    """Payment application status"""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    REVISION_REQUIRED = "revision_required"
    APPROVED = "approved"
    PAID = "paid"
    REJECTED = "rejected"


class RetentionType(str, Enum):
    """Retention type"""
    STANDARD = "standard"
    FINAL = "final"


# Database Models

class ScheduleOfValues(Base):
    """Schedule of Values (SOV)"""
    __tablename__ = 'schedule_of_values'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey('subcontractor_companies.id', ondelete='CASCADE'), nullable=False)
    
    # SOV info
    sov_number = Column(String(100), nullable=False)
    contract_amount = Column(Numeric(15, 2), nullable=False)
    
    # Line items
    line_items = Column(JSONB, default=list)
    # Each item: {id, description, scheduled_value, previous_completed, this_period_completed, total_completed, balance}
    
    # Retention
    retention_percentage = Column(Numeric(5, 2), default=10.00)
    retention_held = Column(Numeric(15, 2), default=0)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PaymentApplication(Base):
    """Payment Application (G702/G703)"""
    __tablename__ = 'payment_applications'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sov_id = Column(UUID(as_uuid=True), ForeignKey('schedule_of_values.id', ondelete='CASCADE'), nullable=False)
    
    # Application info
    app_number = Column(String(100), nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Original contract sum
    original_contract_sum = Column(Numeric(15, 2), nullable=False)
    
    # Net change by change orders
    net_change_orders = Column(Numeric(15, 2), default=0)
    
    # Revised contract sum
    revised_contract_sum = Column(Numeric(15, 2), nullable=False)
    
    # Completed work
    total_completed = Column(Numeric(15, 2), nullable=False)
    
    # Retention
    retention_percentage = Column(Numeric(5, 2), default=10.00)
    retention_held = Column(Numeric(15, 2), nullable=False)
    
    # Amount due
    earned_less_retention = Column(Numeric(15, 2), nullable=False)
    less_previous_payments = Column(Numeric(15, 2), nullable=False)
    current_payment_due = Column(Numeric(15, 2), nullable=False)
    balance_to_finish = Column(Numeric(15, 2), nullable=False)
    
    # Supporting documents
    documents = Column(JSONB, default=list)
    
    # Status
    status = Column(String(50), default=PaymentAppStatus.DRAFT.value)
    
    # Submission
    submitted_at = Column(DateTime, nullable=True)
    submitted_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    
    # Review
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)
    
    # Payment
    paid_at = Column(DateTime, nullable=True)
    payment_reference = Column(String(255), nullable=True)
    payment_amount = Column(Numeric(15, 2), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PaymentHistory(Base):
    """Payment history"""
    __tablename__ = 'payment_history'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sov_id = Column(UUID(as_uuid=True), ForeignKey('schedule_of_values.id', ondelete='CASCADE'), nullable=False)
    
    # Payment info
    payment_number = Column(String(100), nullable=False)
    payment_date = Column(DateTime, nullable=False)
    payment_amount = Column(Numeric(15, 2), nullable=False)
    
    # Application reference
    payment_app_id = Column(UUID(as_uuid=True), ForeignKey('payment_applications.id'), nullable=True)
    
    # Details
    payment_method = Column(String(50), nullable=True)
    reference_number = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Retention
    retention_released = Column(Numeric(15, 2), default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)


# Pydantic Schemas

class SOVLineItem(BaseModel):
    """SOV line item"""
    id: str
    description: str
    scheduled_value: float
    previous_completed: float = 0
    this_period_completed: float = 0
    total_completed: float = 0
    balance: float = 0


class CreateSOVRequest(BaseModel):
    """Create SOV request"""
    project_id: str
    company_id: str
    contract_amount: float
    line_items: List[SOVLineItem]
    retention_percentage: float = 10.0


class CreatePaymentAppRequest(BaseModel):
    """Create payment application request"""
    sov_id: str
    period_start: datetime
    period_end: datetime
    net_change_orders: float = 0


class ReviewPaymentAppRequest(BaseModel):
    """Review payment application request"""
    status: PaymentAppStatus
    notes: Optional[str] = None
    adjusted_amount: Optional[float] = None


class RecordPaymentRequest(BaseModel):
    """Record payment request"""
    payment_date: datetime
    payment_amount: float
    payment_method: str
    reference_number: Optional[str] = None
    notes: Optional[str] = None
    retention_released: float = 0


# Service Classes

class PaymentApplicationService:
    """Service for payment application management"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def _generate_sov_number(self, project_id: str) -> str:
        """Generate SOV number"""
        count = self.db.query(ScheduleOfValues).filter(
            ScheduleOfValues.project_id == project_id
        ).count()
        return f"SOV-{project_id[:8].upper()}-{count + 1:03d}"
    
    def _generate_app_number(self, sov_id: str) -> str:
        """Generate payment application number"""
        count = self.db.query(PaymentApplication).filter(
            PaymentApplication.sov_id == sov_id
        ).count()
        return f"APP-{sov_id[:8].upper()}-{count + 1:03d}"
    
    def create_sov(self, request: CreateSOVRequest) -> ScheduleOfValues:
        """Create Schedule of Values"""
        
        # Calculate retention held
        retention_held = request.contract_amount * (request.retention_percentage / 100)
        
        sov = ScheduleOfValues(
            project_id=request.project_id,
            company_id=request.company_id,
            sov_number=self._generate_sov_number(request.project_id),
            contract_amount=request.contract_amount,
            line_items=[item.model_dump() for item in request.line_items],
            retention_percentage=request.retention_percentage,
            retention_held=retention_held
        )
        
        self.db.add(sov)
        self.db.commit()
        self.db.refresh(sov)
        
        return sov
    
    def get_sov(self, sov_id: str) -> Optional[ScheduleOfValues]:
        """Get SOV by ID"""
        return self.db.query(ScheduleOfValues).filter(
            ScheduleOfValues.id == sov_id
        ).first()
    
    def list_sovs(
        self,
        project_id: Optional[str] = None,
        company_id: Optional[str] = None
    ) -> List[ScheduleOfValues]:
        """List SOVs"""
        
        query = self.db.query(ScheduleOfValues)
        
        if project_id:
            query = query.filter(ScheduleOfValues.project_id == project_id)
        
        if company_id:
            query = query.filter(ScheduleOfValues.company_id == company_id)
        
        return query.order_by(ScheduleOfValues.created_at.desc()).all()
    
    def create_payment_app(
        self,
        request: CreatePaymentAppRequest,
        submitted_by: Optional[str] = None
    ) -> PaymentApplication:
        """Create payment application"""
        
        sov = self.get_sov(request.sov_id)
        if not sov:
            raise HTTPException(404, "SOV not found")
        
        # Calculate values
        revised_contract_sum = sov.contract_amount + request.net_change_orders
        
        # Get previous payments
        previous_payments = self.db.query(PaymentHistory).filter(
            PaymentHistory.sov_id == request.sov_id
        ).all()
        
        total_previous = sum(float(p.payment_amount) for p in previous_payments)
        
        # Calculate completed work (this would come from actual progress)
        # For now, use a placeholder
        total_completed = revised_contract_sum * 0.5  # 50% complete
        
        # Calculate retention
        retention_held = total_completed * (sov.retention_percentage / 100)
        
        # Calculate amount due
        earned_less_retention = total_completed - retention_held
        current_payment_due = earned_less_retention - total_previous
        balance_to_finish = revised_contract_sum - total_completed
        
        app = PaymentApplication(
            sov_id=request.sov_id,
            app_number=self._generate_app_number(request.sov_id),
            period_start=request.period_start,
            period_end=request.period_end,
            original_contract_sum=sov.contract_amount,
            net_change_orders=request.net_change_orders,
            revised_contract_sum=revised_contract_sum,
            total_completed=total_completed,
            retention_percentage=sov.retention_percentage,
            retention_held=retention_held,
            earned_less_retention=earned_less_retention,
            less_previous_payments=total_previous,
            current_payment_due=current_payment_due,
            balance_to_finish=balance_to_finish,
            status=PaymentAppStatus.SUBMITTED.value,
            submitted_at=datetime.utcnow(),
            submitted_by=submitted_by
        )
        
        self.db.add(app)
        self.db.commit()
        self.db.refresh(app)
        
        return app
    
    def get_payment_app(self, app_id: str) -> Optional[PaymentApplication]:
        """Get payment application by ID"""
        return self.db.query(PaymentApplication).filter(
            PaymentApplication.id == app_id
        ).first()
    
    def list_payment_apps(
        self,
        sov_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[PaymentApplication]:
        """List payment applications"""
        
        query = self.db.query(PaymentApplication)
        
        if sov_id:
            query = query.filter(PaymentApplication.sov_id == sov_id)
        
        if status:
            query = query.filter(PaymentApplication.status == status)
        
        return query.order_by(PaymentApplication.created_at.desc()).all()
    
    def review_payment_app(
        self,
        app_id: str,
        request: ReviewPaymentAppRequest,
        reviewed_by: str
    ) -> PaymentApplication:
        """Review payment application"""
        
        app = self.get_payment_app(app_id)
        if not app:
            raise HTTPException(404, "Payment application not found")
        
        app.status = request.status.value
        app.review_notes = request.notes
        app.reviewed_by = reviewed_by
        app.reviewed_at = datetime.utcnow()
        
        # If approved with adjustment
        if request.adjusted_amount is not None:
            app.current_payment_due = request.adjusted_amount
        
        self.db.commit()
        self.db.refresh(app)
        
        return app
    
    def record_payment(
        self,
        sov_id: str,
        app_id: Optional[str],
        request: RecordPaymentRequest
    ) -> PaymentHistory:
        """Record payment"""
        
        sov = self.get_sov(sov_id)
        if not sov:
            raise HTTPException(404, "SOV not found")
        
        # Generate payment number
        count = self.db.query(PaymentHistory).filter(
            PaymentHistory.sov_id == sov_id
        ).count()
        payment_number = f"PAY-{sov_id[:8].upper()}-{count + 1:03d}"
        
        payment = PaymentHistory(
            sov_id=sov_id,
            payment_app_id=app_id,
            payment_number=payment_number,
            payment_date=request.payment_date,
            payment_amount=request.payment_amount,
            payment_method=request.payment_method,
            reference_number=request.reference_number,
            notes=request.notes,
            retention_released=request.retention_released
        )
        
        self.db.add(payment)
        
        # Update app status if applicable
        if app_id:
            app = self.get_payment_app(app_id)
            if app:
                app.status = PaymentAppStatus.PAID.value
                app.paid_at = request.payment_date
                app.payment_reference = request.reference_number
                app.payment_amount = request.payment_amount
        
        self.db.commit()
        self.db.refresh(payment)
        
        return payment
    
    def get_payment_summary(self, sov_id: str) -> Dict[str, Any]:
        """Get payment summary for SOV"""
        
        sov = self.get_sov(sov_id)
        if not sov:
            raise HTTPException(404, "SOV not found")
        
        # Get payment history
        payments = self.db.query(PaymentHistory).filter(
            PaymentHistory.sov_id == sov_id
        ).all()
        
        total_paid = sum(float(p.payment_amount) for p in payments)
        total_retention_released = sum(float(p.retention_released) for p in payments)
        
        # Get pending applications
        pending_apps = self.db.query(PaymentApplication).filter(
            PaymentApplication.sov_id == sov_id,
            PaymentApplication.status.in_([PaymentAppStatus.SUBMITTED.value, PaymentAppStatus.UNDER_REVIEW.value])
        ).all()
        
        pending_amount = sum(float(a.current_payment_due) for a in pending_apps)
        
        return {
            "sov_id": sov_id,
            "contract_amount": float(sov.contract_amount),
            "total_paid": total_paid,
            "total_retention_held": float(sov.retention_held),
            "total_retention_released": total_retention_released,
            "pending_applications": len(pending_apps),
            "pending_amount": pending_amount,
            "balance_remaining": float(sov.contract_amount) - total_paid - total_retention_released,
            "payment_history": [
                {
                    "id": str(p.id),
                    "payment_number": p.payment_number,
                    "payment_date": p.payment_date.isoformat() if p.payment_date else None,
                    "amount": float(p.payment_amount),
                    "reference": p.reference_number
                }
                for p in payments
            ]
        }


# Export
__all__ = [
    'PaymentAppStatus',
    'RetentionType',
    'ScheduleOfValues',
    'PaymentApplication',
    'PaymentHistory',
    'SOVLineItem',
    'CreateSOVRequest',
    'CreatePaymentAppRequest',
    'ReviewPaymentAppRequest',
    'RecordPaymentRequest',
    'PaymentApplicationService'
]
