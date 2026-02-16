"""
Contract Management Module - MSA, Billing, and PO Support
Item 294: Contract management, MSA, billing, PO support
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import uuid
from app.db.base_class import Base

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Integer, Float, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from fastapi import HTTPException
from enum import Enum


class ContractType(str, Enum):
    """Types of contracts"""
    MSA = "msa"  # Master Service Agreement
    SOW = "sow"  # Statement of Work
    ORDER = "order"  # Purchase Order
    AMENDMENT = "amendment"
    NDA = "nda"
    DPA = "dpa"  # Data Processing Agreement
    SLA = "sla"


class ContractStatus(str, Enum):
    """Contract status"""
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    PENDING_SIGNATURE = "pending_signature"
    ACTIVE = "active"
    EXPIRED = "expired"
    TERMINATED = "terminated"


class BillingCycle(str, Enum):
    """Billing cycles"""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    ONE_TIME = "one_time"


# Database Models

class Contract(Base):
    """Contract/Agreement"""
    __tablename__ = 'contracts'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    
    # Contract info
    contract_number = Column(String(100), unique=True, nullable=False)
    contract_type = Column(String(50), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    
    # Parties
    customer_name = Column(String(500), nullable=False)
    customer_address = Column(Text, nullable=True)
    customer_contact_email = Column(String(255), nullable=True)
    
    # Dates
    effective_date = Column(DateTime, nullable=True)
    expiration_date = Column(DateTime, nullable=True)
    renewal_date = Column(DateTime, nullable=True)
    
    # Financial
    contract_value = Column(Numeric(15, 2), nullable=True)
    currency = Column(String(3), default='USD')
    
    # Status
    status = Column(String(50), default=ContractStatus.DRAFT.value)
    
    # Documents
    document_url = Column(String(500), nullable=True)
    signed_document_url = Column(String(500), nullable=True)
    
    # Signatures
    signed_by_customer = Column(Boolean, default=False)
    signed_by_customer_at = Column(DateTime, nullable=True)
    signed_by_customer_name = Column(String(255), nullable=True)
    
    signed_by_vendor = Column(Boolean, default=False)
    signed_by_vendor_at = Column(DateTime, nullable=True)
    signed_by_vendor_name = Column(String(255), nullable=True)
    
    # Metadata
    terms = Column(JSONB, default=dict)
    custom_fields = Column(JSONB, default=dict)
    
    # Parent contract (for amendments, SOWs)
    parent_contract_id = Column(UUID(as_uuid=True), ForeignKey('contracts.id'), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)


class PurchaseOrder(Base):
    """Purchase Order"""
    __tablename__ = 'purchase_orders'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    contract_id = Column(UUID(as_uuid=True), ForeignKey('contracts.id'), nullable=True)
    
    # PO info
    po_number = Column(String(100), nullable=False)
    po_date = Column(DateTime, nullable=False)
    
    # Vendor info
    vendor_name = Column(String(500), nullable=False)
    vendor_address = Column(Text, nullable=True)
    
    # Line items
    line_items = Column(JSONB, default=list)
    
    # Totals
    subtotal = Column(Numeric(15, 2), nullable=False)
    tax_amount = Column(Numeric(15, 2), default=0)
    total_amount = Column(Numeric(15, 2), nullable=False)
    
    # Status
    status = Column(String(50), default='draft')
    
    # Approval
    approved_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    
    # Document
    document_url = Column(String(500), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class BillingRecord(Base):
    """Billing records"""
    __tablename__ = 'billing_records'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    contract_id = Column(UUID(as_uuid=True), ForeignKey('contracts.id'), nullable=True)
    
    # Billing period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Amounts
    subscription_amount = Column(Numeric(15, 2), default=0)
    usage_amount = Column(Numeric(15, 2), default=0)
    discount_amount = Column(Numeric(15, 2), default=0)
    tax_amount = Column(Numeric(15, 2), default=0)
    total_amount = Column(Numeric(15, 2), nullable=False)
    
    # Status
    status = Column(String(50), default='pending')
    
    # Invoice
    invoice_number = Column(String(100), nullable=True)
    invoice_date = Column(DateTime, nullable=True)
    invoice_url = Column(String(500), nullable=True)
    
    # Payment
    paid_at = Column(DateTime, nullable=True)
    payment_method = Column(String(50), nullable=True)
    
    # Stripe
    stripe_invoice_id = Column(String(255), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class ContractTerm(Base):
    """Contract terms and conditions"""
    __tablename__ = 'contract_terms'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id = Column(UUID(as_uuid=True), ForeignKey('contracts.id', ondelete='CASCADE'), nullable=False)
    
    term_name = Column(String(255), nullable=False)
    term_value = Column(Text, nullable=True)
    
    # Term type
    term_type = Column(String(50), nullable=False)  # payment, service_level, liability, termination, etc.
    
    # Important dates
    effective_date = Column(DateTime, nullable=True)
    expiration_date = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


# Pydantic Schemas

class CreateContractRequest(BaseModel):
    """Create contract request"""
    contract_type: ContractType
    title: str
    description: Optional[str] = None
    customer_name: str
    customer_address: Optional[str] = None
    customer_contact_email: Optional[str] = None
    effective_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    contract_value: Optional[float] = None
    currency: str = 'USD'
    terms: Dict[str, Any] = Field(default_factory=dict)


class CreatePORequest(BaseModel):
    """Create purchase order"""
    po_number: str
    po_date: datetime
    vendor_name: str
    vendor_address: Optional[str] = None
    line_items: List[Dict[str, Any]] = Field(default_factory=list)
    subtotal: float
    tax_amount: float = 0
    contract_id: Optional[str] = None


class CreateBillingRecordRequest(BaseModel):
    """Create billing record"""
    period_start: datetime
    period_end: datetime
    subscription_amount: float = 0
    usage_amount: float = 0
    discount_amount: float = 0
    tax_amount: float = 0
    contract_id: Optional[str] = None


class ContractResponse(BaseModel):
    """Contract response"""
    id: str
    contract_number: str
    contract_type: str
    title: str
    status: str
    contract_value: Optional[float]
    effective_date: Optional[datetime]
    expiration_date: Optional[datetime]
    created_at: datetime


class BillingSummary(BaseModel):
    """Billing summary"""
    period: Dict[str, Any]
    total_billed: float
    total_paid: float
    total_outstanding: float
    records: List[Dict[str, Any]]


# Service Classes

class ContractService:
    """Service for contract management"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def _generate_contract_number(self, contract_type: str) -> str:
        """Generate unique contract number"""
        
        prefix = contract_type.upper()[:3]
        year = datetime.utcnow().strftime('%Y')
        random_suffix = str(uuid.uuid4().hex[:6]).upper()
        
        return f"{prefix}-{year}-{random_suffix}"
    
    def create_contract(
        self,
        tenant_id: str,
        request: CreateContractRequest,
        created_by: Optional[str] = None
    ) -> Contract:
        """Create new contract"""
        
        contract = Contract(
            tenant_id=tenant_id,
            contract_number=self._generate_contract_number(request.contract_type.value),
            contract_type=request.contract_type.value,
            title=request.title,
            description=request.description,
            customer_name=request.customer_name,
            customer_address=request.customer_address,
            customer_contact_email=request.customer_contact_email,
            effective_date=request.effective_date,
            expiration_date=request.expiration_date,
            contract_value=request.contract_value,
            currency=request.currency,
            terms=request.terms,
            created_by=created_by
        )
        
        self.db.add(contract)
        self.db.commit()
        self.db.refresh(contract)
        
        return contract
    
    def get_contract(self, contract_id: str) -> Optional[Contract]:
        """Get contract by ID"""
        return self.db.query(Contract).filter(Contract.id == contract_id).first()
    
    def list_contracts(
        self,
        tenant_id: str,
        contract_type: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Contract]:
        """List contracts"""
        
        query = self.db.query(Contract).filter(Contract.tenant_id == tenant_id)
        
        if contract_type:
            query = query.filter(Contract.contract_type == contract_type)
        
        if status:
            query = query.filter(Contract.status == status)
        
        return query.order_by(Contract.created_at.desc()).all()
    
    def update_contract_status(
        self,
        contract_id: str,
        status: ContractStatus
    ) -> Contract:
        """Update contract status"""
        
        contract = self.get_contract(contract_id)
        if not contract:
            raise HTTPException(404, "Contract not found")
        
        contract.status = status.value
        
        if status == ContractStatus.ACTIVE:
            contract.effective_date = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(contract)
        
        return contract
    
    def sign_contract(
        self,
        contract_id: str,
        party: str,  # 'customer' or 'vendor'
        signed_by_name: str,
        document_url: Optional[str] = None
    ) -> Contract:
        """Record contract signature"""
        
        contract = self.get_contract(contract_id)
        if not contract:
            raise HTTPException(404, "Contract not found")
        
        if party == 'customer':
            contract.signed_by_customer = True
            contract.signed_by_customer_at = datetime.utcnow()
            contract.signed_by_customer_name = signed_by_name
        elif party == 'vendor':
            contract.signed_by_vendor = True
            contract.signed_by_vendor_at = datetime.utcnow()
            contract.signed_by_vendor_name = signed_by_name
            if document_url:
                contract.signed_document_url = document_url
        
        # Check if fully signed
        if contract.signed_by_customer and contract.signed_by_vendor:
            contract.status = ContractStatus.ACTIVE.value
            if not contract.effective_date:
                contract.effective_date = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(contract)
        
        return contract
    
    def get_contracts_expiring_soon(
        self,
        tenant_id: str,
        days: int = 30
    ) -> List[Contract]:
        """Get contracts expiring within specified days"""
        
        threshold = datetime.utcnow() + timedelta(days=days)
        
        return self.db.query(Contract).filter(
            Contract.tenant_id == tenant_id,
            Contract.status == ContractStatus.ACTIVE.value,
            Contract.expiration_date <= threshold,
            Contract.expiration_date >= datetime.utcnow()
        ).order_by(Contract.expiration_date).all()


class PurchaseOrderService:
    """Service for purchase order management"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_po(
        self,
        tenant_id: str,
        request: CreatePORequest,
        created_by: Optional[str] = None
    ) -> PurchaseOrder:
        """Create purchase order"""
        
        # Calculate total
        total = request.subtotal + request.tax_amount
        
        po = PurchaseOrder(
            tenant_id=tenant_id,
            contract_id=request.contract_id,
            po_number=request.po_number,
            po_date=request.po_date,
            vendor_name=request.vendor_name,
            vendor_address=request.vendor_address,
            line_items=request.line_items,
            subtotal=request.subtotal,
            tax_amount=request.tax_amount,
            total_amount=total
        )
        
        self.db.add(po)
        self.db.commit()
        self.db.refresh(po)
        
        return po
    
    def approve_po(
        self,
        po_id: str,
        approved_by: str
    ) -> PurchaseOrder:
        """Approve purchase order"""
        
        po = self.db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
        
        if not po:
            raise HTTPException(404, "Purchase order not found")
        
        po.status = 'approved'
        po.approved_by = approved_by
        po.approved_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(po)
        
        return po


class BillingService:
    """Service for billing management"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_billing_record(
        self,
        tenant_id: str,
        request: CreateBillingRecordRequest
    ) -> BillingRecord:
        """Create billing record"""
        
        total = (
            request.subscription_amount +
            request.usage_amount -
            request.discount_amount +
            request.tax_amount
        )
        
        record = BillingRecord(
            tenant_id=tenant_id,
            contract_id=request.contract_id,
            period_start=request.period_start,
            period_end=request.period_end,
            subscription_amount=request.subscription_amount,
            usage_amount=request.usage_amount,
            discount_amount=request.discount_amount,
            tax_amount=request.tax_amount,
            total_amount=total
        )
        
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        
        return record
    
    def generate_invoice(
        self,
        record_id: str,
        invoice_number: str
    ) -> BillingRecord:
        """Generate invoice for billing record"""
        
        record = self.db.query(BillingRecord).filter(
            BillingRecord.id == record_id
        ).first()
        
        if not record:
            raise HTTPException(404, "Billing record not found")
        
        record.invoice_number = invoice_number
        record.invoice_date = datetime.utcnow()
        record.status = 'invoiced'
        
        self.db.commit()
        self.db.refresh(record)
        
        return record
    
    def record_payment(
        self,
        record_id: str,
        payment_method: str
    ) -> BillingRecord:
        """Record payment for invoice"""
        
        record = self.db.query(BillingRecord).filter(
            BillingRecord.id == record_id
        ).first()
        
        if not record:
            raise HTTPException(404, "Billing record not found")
        
        record.status = 'paid'
        record.paid_at = datetime.utcnow()
        record.payment_method = payment_method
        
        self.db.commit()
        self.db.refresh(record)
        
        return record
    
    def get_billing_summary(
        self,
        tenant_id: str,
        year: int,
        month: int
    ) -> BillingSummary:
        """Get billing summary for period"""
        
        from dateutil.relativedelta import relativedelta
        
        period_start = datetime(year, month, 1)
        period_end = period_start + relativedelta(months=1) - timedelta(days=1)
        
        records = self.db.query(BillingRecord).filter(
            BillingRecord.tenant_id == tenant_id,
            BillingRecord.period_start >= period_start,
            BillingRecord.period_end <= period_end
        ).all()
        
        total_billed = sum(float(r.total_amount) for r in records)
        total_paid = sum(
            float(r.total_amount) for r in records if r.status == 'paid'
        )
        
        return BillingSummary(
            period={
                'year': year,
                'month': month,
                'start': period_start.isoformat(),
                'end': period_end.isoformat()
            },
            total_billed=total_billed,
            total_paid=total_paid,
            total_outstanding=total_billed - total_paid,
            records=[
                {
                    'id': str(r.id),
                    'invoice_number': r.invoice_number,
                    'total_amount': float(r.total_amount),
                    'status': r.status,
                    'invoice_date': r.invoice_date.isoformat() if r.invoice_date else None
                }
                for r in records
            ]
        )


# Export
__all__ = [
    'ContractType',
    'ContractStatus',
    'BillingCycle',
    'Contract',
    'PurchaseOrder',
    'BillingRecord',
    'ContractTerm',
    'CreateContractRequest',
    'CreatePORequest',
    'CreateBillingRecordRequest',
    'ContractResponse',
    'BillingSummary',
    'ContractService',
    'PurchaseOrderService',
    'BillingService'
]
