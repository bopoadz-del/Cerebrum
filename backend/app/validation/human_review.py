"""
Human Review Gate for Code Validation

Manages the human approval workflow for AI-generated code before
deployment to production.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ReviewStatus(str, Enum):
    """Status of human review."""
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_CHANGES = "needs_changes"
    ESCALATED = "escalated"


class ReviewPriority(str, Enum):
    """Priority level for review."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ReviewComment:
    """A comment on a review."""
    id: UUID
    reviewer_id: UUID
    line_number: Optional[int]
    file_path: Optional[str]
    comment: str
    created_at: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[UUID] = None


@dataclass
class ReviewChecklistItem:
    """Item in the review checklist."""
    id: str
    category: str
    description: str
    required: bool
    checked: bool = False
    checked_by: Optional[UUID] = None
    checked_at: Optional[datetime] = None
    notes: Optional[str] = None


@dataclass
class HumanReview:
    """Human review record."""
    id: UUID
    capability_id: UUID
    validation_result_id: UUID
    status: ReviewStatus
    priority: ReviewPriority
    
    # Reviewers
    assigned_reviewer_id: Optional[UUID]
    reviewers: List[UUID] = field(default_factory=list)
    
    # Review content
    comments: List[ReviewComment] = field(default_factory=list)
    checklist: List[ReviewChecklistItem] = field(default_factory=list)
    
    # Decision
    decision: Optional[str] = None
    decision_reason: Optional[str] = None
    decided_by: Optional[UUID] = None
    decided_at: Optional[datetime] = None
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Metadata
    code_snapshot: Optional[str] = None
    security_report_summary: Optional[Dict[str, Any]] = None
    test_results_summary: Optional[Dict[str, Any]] = None


class ReviewRequest(BaseModel):
    """Request to create a human review."""
    capability_id: UUID
    validation_result_id: UUID
    priority: ReviewPriority = ReviewPriority.MEDIUM
    assigned_reviewer_id: Optional[UUID] = None
    code_snapshot: Optional[str] = None
    security_report_summary: Optional[Dict[str, Any]] = None
    test_results_summary: Optional[Dict[str, Any]] = None


class ReviewDecisionRequest(BaseModel):
    """Request to submit a review decision."""
    decision: ReviewStatus = Field(..., description="approve, reject, or needs_changes")
    reason: str = Field(..., min_length=10, description="Reason for the decision")
    reviewer_id: UUID


class ReviewCommentRequest(BaseModel):
    """Request to add a review comment."""
    comment: str = Field(..., min_length=1)
    line_number: Optional[int] = None
    file_path: Optional[str] = None
    reviewer_id: UUID


class HumanReviewManager:
    """
    Manages human review workflow for AI-generated code.
    
    Provides:
    - Review assignment and tracking
    - Comment and discussion management
    - Checklist-based review process
    - Decision recording and audit trail
    """
    
    # Standard review checklist
    DEFAULT_CHECKLIST = [
        # Security
        ReviewChecklistItem(
            id="sec_1",
            category="Security",
            description="No hardcoded secrets or credentials",
            required=True,
        ),
        ReviewChecklistItem(
            id="sec_2",
            category="Security",
            description="Input validation is appropriate",
            required=True,
        ),
        ReviewChecklistItem(
            id="sec_3",
            category="Security",
            description="No SQL injection vulnerabilities",
            required=True,
        ),
        ReviewChecklistItem(
            id="sec_4",
            category="Security",
            description="Authentication/authorization is correct",
            required=True,
        ),
        
        # Functionality
        ReviewChecklistItem(
            id="func_1",
            category="Functionality",
            description="Code implements the described feature correctly",
            required=True,
        ),
        ReviewChecklistItem(
            id="func_2",
            category="Functionality",
            description="Edge cases are handled appropriately",
            required=True,
        ),
        ReviewChecklistItem(
            id="func_3",
            category="Functionality",
            description="Error handling is comprehensive",
            required=True,
        ),
        
        # Code Quality
        ReviewChecklistItem(
            id="quality_1",
            category="Code Quality",
            description="Code is readable and well-documented",
            required=False,
        ),
        ReviewChecklistItem(
            id="quality_2",
            category="Code Quality",
            description="Naming conventions are followed",
            required=False,
        ),
        ReviewChecklistItem(
            id="quality_3",
            category="Code Quality",
            description="Code follows project style guidelines",
            required=False,
        ),
        
        # Performance
        ReviewChecklistItem(
            id="perf_1",
            category="Performance",
            description="No obvious performance issues",
            required=False,
        ),
        ReviewChecklistItem(
            id="perf_2",
            category="Performance",
            description="Database queries are efficient",
            required=False,
        ),
        
        # Testing
        ReviewChecklistItem(
            id="test_1",
            category="Testing",
            description="Tests cover the main functionality",
            required=True,
        ),
        ReviewChecklistItem(
            id="test_2",
            category="Testing",
            description="Tests include edge cases",
            required=False,
        ),
    ]
    
    def __init__(self):
        """Initialize the review manager."""
        self._reviews: Dict[UUID, HumanReview] = {}
        self._capability_reviews: Dict[UUID, List[UUID]] = {}
    
    async def create_review(self, request: ReviewRequest) -> HumanReview:
        """
        Create a new human review.
        
        Args:
            request: Review creation request
            
        Returns:
            Created review
        """
        review = HumanReview(
            id=uuid4(),
            capability_id=request.capability_id,
            validation_result_id=request.validation_result_id,
            status=ReviewStatus.PENDING,
            priority=request.priority,
            assigned_reviewer_id=request.assigned_reviewer_id,
            checklist=[
                ReviewChecklistItem(
                    id=item.id,
                    category=item.category,
                    description=item.description,
                    required=item.required,
                )
                for item in self.DEFAULT_CHECKLIST
            ],
            code_snapshot=request.code_snapshot,
            security_report_summary=request.security_report_summary,
            test_results_summary=request.test_results_summary,
        )
        
        self._reviews[review.id] = review
        
        if request.capability_id not in self._capability_reviews:
            self._capability_reviews[request.capability_id] = []
        self._capability_reviews[request.capability_id].append(review.id)
        
        logger.info(f"Created human review {review.id} for capability {request.capability_id}")
        
        # Auto-assign if reviewer specified
        if request.assigned_reviewer_id:
            await self.assign_reviewer(review.id, request.assigned_reviewer_id)
        
        return review
    
    async def get_review(self, review_id: UUID) -> Optional[HumanReview]:
        """Get a review by ID."""
        return self._reviews.get(review_id)
    
    async def get_reviews_for_capability(self, capability_id: UUID) -> List[HumanReview]:
        """Get all reviews for a capability."""
        review_ids = self._capability_reviews.get(capability_id, [])
        return [self._reviews[rid] for rid in review_ids if rid in self._reviews]
    
    async def assign_reviewer(
        self, 
        review_id: UUID, 
        reviewer_id: UUID
    ) -> Optional[HumanReview]:
        """
        Assign a reviewer to a review.
        
        Args:
            review_id: Review to assign
            reviewer_id: Reviewer to assign
            
        Returns:
            Updated review or None
        """
        review = self._reviews.get(review_id)
        if not review:
            return None
        
        review.assigned_reviewer_id = reviewer_id
        review.reviewers.append(reviewer_id)
        
        if review.status == ReviewStatus.PENDING:
            review.status = ReviewStatus.IN_REVIEW
            review.started_at = datetime.utcnow()
        
        logger.info(f"Assigned reviewer {reviewer_id} to review {review_id}")
        return review
    
    async def add_comment(
        self,
        review_id: UUID,
        request: ReviewCommentRequest,
    ) -> Optional[ReviewComment]:
        """
        Add a comment to a review.
        
        Args:
            review_id: Review to comment on
            request: Comment request
            
        Returns:
            Created comment or None
        """
        review = self._reviews.get(review_id)
        if not review:
            return None
        
        comment = ReviewComment(
            id=uuid4(),
            reviewer_id=request.reviewer_id,
            line_number=request.line_number,
            file_path=request.file_path,
            comment=request.comment,
            created_at=datetime.utcnow(),
        )
        
        review.comments.append(comment)
        logger.info(f"Added comment to review {review_id}")
        
        return comment
    
    async def update_checklist_item(
        self,
        review_id: UUID,
        item_id: str,
        checked: bool,
        reviewer_id: UUID,
        notes: Optional[str] = None,
    ) -> Optional[ReviewChecklistItem]:
        """
        Update a checklist item.
        
        Args:
            review_id: Review to update
            item_id: Checklist item ID
            checked: New checked status
            reviewer_id: Reviewer making the update
            notes: Optional notes
            
        Returns:
            Updated item or None
        """
        review = self._reviews.get(review_id)
        if not review:
            return None
        
        for item in review.checklist:
            if item.id == item_id:
                item.checked = checked
                item.checked_by = reviewer_id
                item.checked_at = datetime.utcnow()
                item.notes = notes
                return item
        
        return None
    
    async def submit_decision(
        self,
        review_id: UUID,
        request: ReviewDecisionRequest,
    ) -> Optional[HumanReview]:
        """
        Submit a review decision.
        
        Args:
            review_id: Review to decide on
            request: Decision request
            
        Returns:
            Updated review or None
        """
        review = self._reviews.get(review_id)
        if not review:
            return None
        
        # Validate required checklist items are checked for approval
        if request.decision == ReviewStatus.APPROVED:
            unchecked_required = [
                item for item in review.checklist 
                if item.required and not item.checked
            ]
            if unchecked_required:
                raise ValueError(
                    f"Cannot approve: {len(unchecked_required)} required checklist items unchecked"
                )
        
        # Update review
        review.status = request.decision
        review.decision = request.decision.value
        review.decision_reason = request.reason
        review.decided_by = request.reviewer_id
        review.decided_at = datetime.utcnow()
        review.completed_at = datetime.utcnow()
        
        logger.info(
            f"Review {review_id} decided: {request.decision.value} by {request.reviewer_id}"
        )
        
        return review
    
    async def escalate_review(
        self,
        review_id: UUID,
        reason: str,
        escalated_by: UUID,
    ) -> Optional[HumanReview]:
        """
        Escalate a review to higher authority.
        
        Args:
            review_id: Review to escalate
            reason: Escalation reason
            escalated_by: User escalating
            
        Returns:
            Updated review or None
        """
        review = self._reviews.get(review_id)
        if not review:
            return None
        
        review.status = ReviewStatus.ESCALATED
        
        # Add escalation as comment
        comment = ReviewComment(
            id=uuid4(),
            reviewer_id=escalated_by,
            line_number=None,
            file_path=None,
            comment=f"ESCALATED: {reason}",
            created_at=datetime.utcnow(),
        )
        review.comments.append(comment)
        
        logger.info(f"Review {review_id} escalated by {escalated_by}")
        return review
    
    async def get_pending_reviews(
        self,
        reviewer_id: Optional[UUID] = None,
    ) -> List[HumanReview]:
        """
        Get pending reviews.
        
        Args:
            reviewer_id: Filter by assigned reviewer
            
        Returns:
            List of pending reviews
        """
        pending = []
        for review in self._reviews.values():
            if review.status in [ReviewStatus.PENDING, ReviewStatus.IN_REVIEW]:
                if reviewer_id is None or review.assigned_reviewer_id == reviewer_id:
                    pending.append(review)
        
        # Sort by priority and creation date
        priority_order = {
            ReviewPriority.CRITICAL: 0,
            ReviewPriority.HIGH: 1,
            ReviewPriority.MEDIUM: 2,
            ReviewPriority.LOW: 3,
        }
        
        pending.sort(key=lambda r: (priority_order.get(r.priority, 2), r.created_at))
        
        return pending
    
    async def get_review_statistics(self) -> Dict[str, Any]:
        """Get review statistics."""
        stats = {
            "total_reviews": len(self._reviews),
            "by_status": {},
            "by_priority": {},
            "average_review_time_hours": 0,
            "approval_rate": 0,
        }
        
        total_review_time = 0
        completed_reviews = 0
        approved_count = 0
        
        for review in self._reviews.values():
            # By status
            status = review.status.value
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
            
            # By priority
            priority = review.priority.value
            stats["by_priority"][priority] = stats["by_priority"].get(priority, 0) + 1
            
            # Review time
            if review.completed_at and review.started_at:
                review_time = (review.completed_at - review.started_at).total_seconds() / 3600
                total_review_time += review_time
                completed_reviews += 1
            
            # Approval
            if review.status == ReviewStatus.APPROVED:
                approved_count += 1
        
        if completed_reviews > 0:
            stats["average_review_time_hours"] = total_review_time / completed_reviews
        
        if len(self._reviews) > 0:
            stats["approval_rate"] = approved_count / len(self._reviews)
        
        return stats


# Singleton instance
review_manager_instance: Optional[HumanReviewManager] = None


def get_review_manager() -> HumanReviewManager:
    """Get or create the singleton review manager instance."""
    global review_manager_instance
    if review_manager_instance is None:
        review_manager_instance = HumanReviewManager()
    return review_manager_instance


def set_review_manager(manager: HumanReviewManager) -> None:
    """Set the singleton review manager instance."""
    global review_manager_instance
    review_manager_instance = manager
