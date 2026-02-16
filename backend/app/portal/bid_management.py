"""
Bid Management Module - ITB, bid submission, comparison
Item 322: Bid management
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import uuid

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from fastapi import HTTPException
from enum import Enum


class BidStatus(str, Enum):
    """Bid status"""
    DRAFT = "draft"
    INVITED = "invited"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    SHORTLISTED = "shortlisted"
    AWARDED = "awarded"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class ITBStatus(str, Enum):
    """Invitation to Bid status"""
    DRAFT = "draft"
    SENT = "sent"
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"


# Database Models

class InvitationToBid(Base):
    """Invitation to Bid (ITB)"""
    __tablename__ = 'invitations_to_bid'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    
    # ITB info
    itb_number = Column(String(100), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    
    # Trade/scope
    trade = Column(String(100), nullable=False)
    scope_of_work = Column(Text, nullable=True)
    
    # Documents
    documents = Column(JSONB, default=list)
    drawings = Column(JSONB, default=list)
    specifications = Column(JSONB, default=list)
    
    # Schedule
    issue_date = Column(DateTime, default=datetime.utcnow)
    site_visit_date = Column(DateTime, nullable=True)
    pre_bid_meeting_date = Column(DateTime, nullable=True)
    bid_deadline = Column(DateTime, nullable=False)
    
    # Requirements
    bond_required = Column(Boolean, default=False)
    bond_amount = Column(Numeric(15, 2), nullable=True)
    insurance_required = Column(Boolean, default=True)
    
    # Status
    status = Column(String(50), default=ITBStatus.DRAFT.value)
    
    # Invited bidders
    invited_companies = Column(JSONB, default=list)
    
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Bid(Base):
    """Bid submission"""
    __tablename__ = 'bids'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    itb_id = Column(UUID(as_uuid=True), ForeignKey('invitations_to_bid.id', ondelete='CASCADE'), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey('subcontractor_companies.id', ondelete='CASCADE'), nullable=False)
    
    # Bid info
    bid_number = Column(String(100), nullable=False)
    
    # Pricing
    base_bid_amount = Column(Numeric(15, 2), nullable=False)
    alternate_amounts = Column(JSONB, default=list)
    total_bid_amount = Column(Numeric(15, 2), nullable=False)
    
    # Breakdown
    cost_breakdown = Column(JSONB, default=list)  # Line item breakdown
    
    # Documents
    bid_documents = Column(JSONB, default=list)
    
    # Schedule
    proposed_duration_days = Column(Integer, nullable=True)
    proposed_start_date = Column(DateTime, nullable=True)
    
    # Qualifications
    qualifications = Column(Text, nullable=True)
    exclusions = Column(Text, nullable=True)
    
    # Bond
    bid_bond_amount = Column(Numeric(15, 2), nullable=True)
    bid_bond_document = Column(String(500), nullable=True)
    
    # Status
    status = Column(String(50), default=BidStatus.DRAFT.value)
    
    # Submission
    submitted_at = Column(DateTime, nullable=True)
    submitted_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    
    # Review
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)
    score = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BidComparison(Base):
    """Bid comparison analysis"""
    __tablename__ = 'bid_comparisons'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    itb_id = Column(UUID(as_uuid=True), ForeignKey('invitations_to_bid.id', ondelete='CASCADE'), nullable=False)
    
    # Comparison criteria
    criteria = Column(JSONB, default=list)  # price, schedule, experience, safety, quality
    
    # Bid scores
    bid_scores = Column(JSONB, default=list)
    
    # Analysis
    analysis_notes = Column(Text, nullable=True)
    recommendation = Column(String(500), nullable=True)
    recommended_bid_id = Column(UUID(as_uuid=True), ForeignKey('bids.id'), nullable=True)
    
    # Status
    is_final = Column(Boolean, default=False)
    
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# Pydantic Schemas

class CreateITBRequest(BaseModel):
    """Create ITB request"""
    project_id: str
    title: str
    description: Optional[str] = None
    trade: str
    scope_of_work: Optional[str] = None
    bid_deadline: datetime
    site_visit_date: Optional[datetime] = None
    pre_bid_meeting_date: Optional[datetime] = None
    bond_required: bool = False
    bond_amount: Optional[float] = None
    invited_companies: List[str] = Field(default_factory=list)


class SubmitBidRequest(BaseModel):
    """Submit bid request"""
    itb_id: str
    base_bid_amount: float
    alternate_amounts: List[Dict[str, Any]] = Field(default_factory=list)
    cost_breakdown: List[Dict[str, Any]] = Field(default_factory=list)
    proposed_duration_days: Optional[int] = None
    proposed_start_date: Optional[datetime] = None
    qualifications: Optional[str] = None
    exclusions: Optional[str] = None
    bid_bond_amount: Optional[float] = None


class ReviewBidRequest(BaseModel):
    """Review bid request"""
    score: int = Field(..., ge=1, le=100)
    notes: Optional[str] = None
    status: BidStatus


class CreateComparisonRequest(BaseModel):
    """Create bid comparison request"""
    criteria: List[Dict[str, Any]]
    bid_scores: List[Dict[str, Any]]
    analysis_notes: Optional[str] = None
    recommendation: Optional[str] = None
    recommended_bid_id: Optional[str] = None


# Service Classes

class BidManagementService:
    """Service for bid management"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def _generate_itb_number(self, project_id: str) -> str:
        """Generate ITB number"""
        count = self.db.query(InvitationToBid).filter(
            InvitationToBid.project_id == project_id
        ).count()
        return f"ITB-{project_id[:8].upper()}-{count + 1:03d}"
    
    def _generate_bid_number(self, itb_id: str) -> str:
        """Generate bid number"""
        count = self.db.query(Bid).filter(
            Bid.itb_id == itb_id
        ).count()
        return f"BID-{itb_id[:8].upper()}-{count + 1:03d}"
    
    def create_itb(
        self,
        request: CreateITBRequest,
        created_by: Optional[str] = None
    ) -> InvitationToBid:
        """Create Invitation to Bid"""
        
        itb = InvitationToBid(
            project_id=request.project_id,
            itb_number=self._generate_itb_number(request.project_id),
            title=request.title,
            description=request.description,
            trade=request.trade,
            scope_of_work=request.scope_of_work,
            bid_deadline=request.bid_deadline,
            site_visit_date=request.site_visit_date,
            pre_bid_meeting_date=request.pre_bid_meeting_date,
            bond_required=request.bond_required,
            bond_amount=request.bond_amount,
            invited_companies=request.invited_companies,
            created_by=created_by
        )
        
        self.db.add(itb)
        self.db.commit()
        self.db.refresh(itb)
        
        return itb
    
    def get_itb(self, itb_id: str) -> Optional[InvitationToBid]:
        """Get ITB by ID"""
        return self.db.query(InvitationToBid).filter(
            InvitationToBid.id == itb_id
        ).first()
    
    def list_itbs(
        self,
        project_id: Optional[str] = None,
        trade: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[InvitationToBid]:
        """List ITBs"""
        
        query = self.db.query(InvitationToBid)
        
        if project_id:
            query = query.filter(InvitationToBid.project_id == project_id)
        
        if trade:
            query = query.filter(InvitationToBid.trade == trade)
        
        if status:
            query = query.filter(InvitationToBid.status == status)
        
        return query.order_by(InvitationToBid.created_at.desc()).all()
    
    def send_itb(self, itb_id: str) -> InvitationToBid:
        """Send ITB to invited companies"""
        
        itb = self.get_itb(itb_id)
        if not itb:
            raise HTTPException(404, "ITB not found")
        
        itb.status = ITBStatus.SENT.value
        itb.issue_date = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(itb)
        
        # Notify invited companies
        # This would send emails to each company
        
        return itb
    
    def submit_bid(
        self,
        company_id: str,
        request: SubmitBidRequest,
        submitted_by: Optional[str] = None
    ) -> Bid:
        """Submit bid"""
        
        itb = self.get_itb(request.itb_id)
        if not itb:
            raise HTTPException(404, "ITB not found")
        
        # Check deadline
        if itb.bid_deadline < datetime.utcnow():
            raise HTTPException(400, "Bid deadline has passed")
        
        # Check if already submitted
        existing = self.db.query(Bid).filter(
            Bid.itb_id == request.itb_id,
            Bid.company_id == company_id
        ).first()
        
        if existing:
            raise HTTPException(409, "Bid already submitted for this ITB")
        
        # Calculate total
        total = request.base_bid_amount
        for alt in request.alternate_amounts:
            total += alt.get('amount', 0)
        
        bid = Bid(
            itb_id=request.itb_id,
            company_id=company_id,
            bid_number=self._generate_bid_number(request.itb_id),
            base_bid_amount=request.base_bid_amount,
            alternate_amounts=request.alternate_amounts,
            total_bid_amount=total,
            cost_breakdown=request.cost_breakdown,
            proposed_duration_days=request.proposed_duration_days,
            proposed_start_date=request.proposed_start_date,
            qualifications=request.qualifications,
            exclusions=request.exclusions,
            bid_bond_amount=request.bid_bond_amount,
            status=BidStatus.SUBMITTED.value,
            submitted_at=datetime.utcnow(),
            submitted_by=submitted_by
        )
        
        self.db.add(bid)
        self.db.commit()
        self.db.refresh(bid)
        
        return bid
    
    def get_bid(self, bid_id: str) -> Optional[Bid]:
        """Get bid by ID"""
        return self.db.query(Bid).filter(Bid.id == bid_id).first()
    
    def list_bids(
        self,
        itb_id: Optional[str] = None,
        company_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Bid]:
        """List bids"""
        
        query = self.db.query(Bid)
        
        if itb_id:
            query = query.filter(Bid.itb_id == itb_id)
        
        if company_id:
            query = query.filter(Bid.company_id == company_id)
        
        if status:
            query = query.filter(Bid.status == status)
        
        return query.order_by(Bid.total_bid_amount).all()
    
    def review_bid(
        self,
        bid_id: str,
        request: ReviewBidRequest,
        reviewed_by: str
    ) -> Bid:
        """Review bid"""
        
        bid = self.get_bid(bid_id)
        if not bid:
            raise HTTPException(404, "Bid not found")
        
        bid.score = request.score
        bid.review_notes = request.notes
        bid.status = request.status.value
        bid.reviewed_by = reviewed_by
        bid.reviewed_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(bid)
        
        return bid
    
    def create_comparison(
        self,
        itb_id: str,
        request: CreateComparisonRequest,
        created_by: Optional[str] = None
    ) -> BidComparison:
        """Create bid comparison"""
        
        comparison = BidComparison(
            itb_id=itb_id,
            criteria=request.criteria,
            bid_scores=request.bid_scores,
            analysis_notes=request.analysis_notes,
            recommendation=request.recommendation,
            recommended_bid_id=request.recommended_bid_id,
            created_by=created_by
        )
        
        self.db.add(comparison)
        self.db.commit()
        self.db.refresh(comparison)
        
        return comparison
    
    def get_comparison(self, comparison_id: str) -> Optional[BidComparison]:
        """Get comparison by ID"""
        return self.db.query(BidComparison).filter(
            BidComparison.id == comparison_id
        ).first()
    
    def finalize_comparison(
        self,
        comparison_id: str,
        awarded_bid_id: str
    ) -> BidComparison:
        """Finalize comparison and award bid"""
        
        comparison = self.get_comparison(comparison_id)
        if not comparison:
            raise HTTPException(404, "Comparison not found")
        
        comparison.is_final = True
        comparison.recommended_bid_id = awarded_bid_id
        
        # Update bid status
        bid = self.get_bid(awarded_bid_id)
        if bid:
            bid.status = BidStatus.AWARDED.value
        
        # Reject other bids
        other_bids = self.db.query(Bid).filter(
            Bid.itb_id == comparison.itb_id,
            Bid.id != awarded_bid_id
        ).all()
        
        for b in other_bids:
            b.status = BidStatus.REJECTED.value
        
        self.db.commit()
        self.db.refresh(comparison)
        
        return comparison
    
    def get_bid_summary(self, itb_id: str) -> Dict[str, Any]:
        """Get bid summary for ITB"""
        
        itb = self.get_itb(itb_id)
        if not itb:
            raise HTTPException(404, "ITB not found")
        
        bids = self.list_bids(itb_id=itb_id)
        
        if not bids:
            return {
                "itb_id": itb_id,
                "total_bids": 0,
                "lowest_bid": None,
                "highest_bid": None,
                "average_bid": None
            }
        
        amounts = [float(b.total_bid_amount) for b in bids]
        
        return {
            "itb_id": itb_id,
            "total_bids": len(bids),
            "lowest_bid": min(amounts),
            "highest_bid": max(amounts),
            "average_bid": sum(amounts) / len(amounts),
            "bids": [
                {
                    "id": str(b.id),
                    "bid_number": b.bid_number,
                    "company_id": str(b.company_id),
                    "amount": float(b.total_bid_amount),
                    "status": b.status,
                    "score": b.score
                }
                for b in bids
            ]
        }


# Export
__all__ = [
    'BidStatus',
    'ITBStatus',
    'InvitationToBid',
    'Bid',
    'BidComparison',
    'CreateITBRequest',
    'SubmitBidRequest',
    'ReviewBidRequest',
    'CreateComparisonRequest',
    'BidManagementService'
]
