"""
Economics Models - Budget, ChangeOrder, CostCode
SQLAlchemy models for economics and cost management.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from enum import Enum as PyEnum
import uuid

from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Date, 
    Text, ForeignKey, Enum, Numeric, Boolean, JSON
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class BudgetStatus(str, PyEnum):
    """Budget status values."""
    DRAFT = "draft"
    APPROVED = "approved"
    ACTIVE = "active"
    CLOSED = "closed"
    REVISED = "revised"


class ChangeOrderStatus(str, PyEnum):
    """Change order status values."""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    IMPLEMENTED = "implemented"


class ChangeOrderType(str, PyEnum):
    """Change order types."""
    ADDITION = "addition"
    DEDUCTION = "deduction"
    MODIFICATION = "modification"


class CostCodeType(str, PyEnum):
    """Cost code hierarchy types."""
    DIVISION = "division"
    SUBGROUP = "subgroup"
    LINE_ITEM = "line_item"


class Budget(Base):
    """Project budget model."""
    
    __tablename__ = "budgets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Budget amounts
    original_budget = Column(Numeric(15, 2), nullable=False, default=0)
    revised_budget = Column(Numeric(15, 2), nullable=False, default=0)
    committed_cost = Column(Numeric(15, 2), nullable=False, default=0)
    actual_cost = Column(Numeric(15, 2), nullable=False, default=0)
    forecast_cost = Column(Numeric(15, 2), nullable=False, default=0)
    
    # Status and dates
    status = Column(Enum(BudgetStatus), default=BudgetStatus.DRAFT)
    start_date = Column(Date)
    end_date = Column(Date)
    approved_date = Column(DateTime)
    
    # Metadata
    currency = Column(String(3), default="USD")
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    line_items = relationship("BudgetLineItem", back_populates="budget", cascade="all, delete-orphan")
    change_orders = relationship("ChangeOrder", back_populates="budget")
    
    @property
    def remaining_budget(self) -> Decimal:
        """Calculate remaining budget."""
        return Decimal(self.revised_budget) - Decimal(self.committed_cost)
    
    @property
    def variance(self) -> Decimal:
        """Calculate budget variance."""
        return Decimal(self.revised_budget) - Decimal(self.forecast_cost)
    
    @property
    def percent_complete(self) -> float:
        """Calculate percent complete."""
        if self.revised_budget == 0:
            return 0.0
        return float(Decimal(self.actual_cost) / Decimal(self.revised_budget) * 100)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "name": self.name,
            "description": self.description,
            "original_budget": float(self.original_budget),
            "revised_budget": float(self.revised_budget),
            "committed_cost": float(self.committed_cost),
            "actual_cost": float(self.actual_cost),
            "forecast_cost": float(self.forecast_cost),
            "remaining_budget": float(self.remaining_budget),
            "variance": float(self.variance),
            "percent_complete": self.percent_complete,
            "status": self.status.value,
            "currency": self.currency,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class BudgetLineItem(Base):
    """Budget line item model."""
    
    __tablename__ = "budget_line_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    budget_id = Column(UUID(as_uuid=True), ForeignKey("budgets.id"), nullable=False)
    cost_code_id = Column(UUID(as_uuid=True), ForeignKey("cost_codes.id"))
    
    # Line item details
    description = Column(String(500), nullable=False)
    quantity = Column(Numeric(12, 4), default=1)
    unit = Column(String(50))
    unit_price = Column(Numeric(15, 2), default=0)
    
    # Amounts
    original_amount = Column(Numeric(15, 2), default=0)
    revised_amount = Column(Numeric(15, 2), default=0)
    committed_amount = Column(Numeric(15, 2), default=0)
    actual_amount = Column(Numeric(15, 2), default=0)
    
    # Metadata
    notes = Column(Text)
    wbs_code = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    budget = relationship("Budget", back_populates="line_items")
    cost_code = relationship("CostCode")
    
    @property
    def variance(self) -> Decimal:
        """Calculate line item variance."""
        return Decimal(self.revised_amount) - Decimal(self.actual_amount)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "description": self.description,
            "quantity": float(self.quantity),
            "unit": self.unit,
            "unit_price": float(self.unit_price),
            "original_amount": float(self.original_amount),
            "revised_amount": float(self.revised_amount),
            "committed_amount": float(self.committed_amount),
            "actual_amount": float(self.actual_amount),
            "variance": float(self.variance),
            "wbs_code": self.wbs_code,
        }


class ChangeOrder(Base):
    """Change order model."""
    
    __tablename__ = "change_orders"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    budget_id = Column(UUID(as_uuid=True), ForeignKey("budgets.id"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    
    # Change order details
    co_number = Column(String(50), nullable=False, unique=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Classification
    type = Column(Enum(ChangeOrderType), default=ChangeOrderType.MODIFICATION)
    status = Column(Enum(ChangeOrderStatus), default=ChangeOrderStatus.DRAFT)
    reason = Column(Text)
    
    # Financial impact
    estimated_cost = Column(Numeric(15, 2), default=0)
    approved_amount = Column(Numeric(15, 2), default=0)
    time_impact_days = Column(Integer, default=0)
    
    # Dates
    submitted_date = Column(DateTime)
    approved_date = Column(DateTime)
    implemented_date = Column(DateTime)
    
    # Parties
    requested_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Metadata
    attachments = Column(JSONB, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    budget = relationship("Budget", back_populates="change_orders")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "co_number": self.co_number,
            "title": self.title,
            "description": self.description,
            "type": self.type.value,
            "status": self.status.value,
            "estimated_cost": float(self.estimated_cost),
            "approved_amount": float(self.approved_amount),
            "time_impact_days": self.time_impact_days,
            "submitted_date": self.submitted_date.isoformat() if self.submitted_date else None,
            "approved_date": self.approved_date.isoformat() if self.approved_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class CostCode(Base):
    """Cost code model for WBS structure."""
    
    __tablename__ = "cost_codes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("cost_codes.id"))
    
    # Cost code details
    code = Column(String(50), nullable=False)
    description = Column(String(255), nullable=False)
    type = Column(Enum(CostCodeType), default=CostCodeType.LINE_ITEM)
    
    # Hierarchy
    level = Column(Integer, default=0)
    path = Column(String(500))
    
    # RSMeans reference
    rsmeans_code = Column(String(50))
    unit = Column(String(50))
    
    # Custom metadata
    is_active = Column(Boolean, default=True)
    custom_metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    parent = relationship("CostCode", remote_side=[id], backref="children")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "code": self.code,
            "description": self.description,
            "type": self.type.value,
            "level": self.level,
            "path": self.path,
            "rsmeans_code": self.rsmeans_code,
            "unit": self.unit,
            "is_active": self.is_active,
        }


class Invoice(Base):
    """Invoice model for accounts payable."""
    
    __tablename__ = "invoices"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id"))
    
    # Invoice details
    invoice_number = Column(String(100), nullable=False)
    po_number = Column(String(100))
    description = Column(Text)
    
    # Amounts
    subtotal = Column(Numeric(15, 2), default=0)
    tax_amount = Column(Numeric(15, 2), default=0)
    total_amount = Column(Numeric(15, 2), default=0)
    
    # Dates
    invoice_date = Column(Date, nullable=False)
    due_date = Column(Date)
    received_date = Column(Date)
    paid_date = Column(Date)
    
    # Status
    status = Column(String(50), default="pending")
    approval_status = Column(String(50), default="pending")
    
    # OCR data
    ocr_data = Column(JSONB, default=dict)
    ocr_confidence = Column(Float)
    
    # Metadata
    attachments = Column(JSONB, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "invoice_number": self.invoice_number,
            "po_number": self.po_number,
            "description": self.description,
            "subtotal": float(self.subtotal),
            "tax_amount": float(self.tax_amount),
            "total_amount": float(self.total_amount),
            "invoice_date": self.invoice_date.isoformat() if self.invoice_date else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "status": self.status,
        }


class ProgressPayment(Base):
    """Progress payment / Schedule of Values entry."""
    
    __tablename__ = "progress_payments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    contract_id = Column(UUID(as_uuid=True), ForeignKey("contracts.id"))
    
    # SOV line item
    line_item_number = Column(String(50))
    description = Column(String(500), nullable=False)
    scheduled_value = Column(Numeric(15, 2), default=0)
    
    # Work completed
    work_completed_from_previous = Column(Numeric(15, 2), default=0)
    work_completed_this_period = Column(Numeric(15, 2), default=0)
    materials_present = Column(Numeric(15, 2), default=0)
    
    # Totals
    total_completed = Column(Numeric(15, 2), default=0)
    balance_to_finish = Column(Numeric(15, 2), default=0)
    percent_complete = Column(Numeric(5, 2), default=0)
    
    # Retainage
    retainage_percent = Column(Numeric(5, 2), default=0)
    retainage_amount = Column(Numeric(15, 2), default=0)
    
    # Period
    period_start = Column(Date)
    period_end = Column(Date)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def calculate_totals(self) -> None:
        """Calculate derived totals."""
        self.total_completed = (
            self.work_completed_from_previous + 
            self.work_completed_this_period + 
            self.materials_present
        )
        self.balance_to_finish = self.scheduled_value - self.total_completed
        if self.scheduled_value > 0:
            self.percent_complete = (self.total_completed / self.scheduled_value) * 100
        self.retainage_amount = self.total_completed * (self.retainage_percent / 100)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "line_item_number": self.line_item_number,
            "description": self.description,
            "scheduled_value": float(self.scheduled_value),
            "work_completed_this_period": float(self.work_completed_this_period),
            "total_completed": float(self.total_completed),
            "balance_to_finish": float(self.balance_to_finish),
            "percent_complete": float(self.percent_complete),
            "retainage_amount": float(self.retainage_amount),
        }
