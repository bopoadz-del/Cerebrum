"""
Scoped Access Module - Trade-specific access control for subcontractor portal
Item 321: Trade-specific access control
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from fastapi import HTTPException
from enum import Enum


class TradeType(str, Enum):
    """Construction trade types"""
    GENERAL_CONTRACTOR = "general_contractor"
    ELECTRICAL = "electrical"
    PLUMBING = "plumbing"
    HVAC = "hvac"
    CARPENTRY = "carpentry"
    MASONRY = "masonry"
    ROOFING = "roofing"
    PAINTING = "painting"
    FLOORING = "flooring"
    LANDSCAPING = "landscaping"
    CONCRETE = "concrete"
    STEEL = "steel"
    GLAZING = "glazing"
    FIRE_PROTECTION = "fire_protection"
    SECURITY = "security"
    IT_TELECOM = "it_telecom"
    DEMOLITION = "demolition"
    EXCAVATION = "excavation"


class AccessLevel(str, Enum):
    """Access levels"""
    VIEW_ONLY = "view_only"
    SUBMIT = "submit"
    EDIT = "edit"
    ADMIN = "admin"


# Database Models

class SubcontractorCompany(Base):
    """Subcontractor company"""
    __tablename__ = 'subcontractor_companies'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    
    # Company info
    company_name = Column(String(500), nullable=False)
    legal_name = Column(String(500), nullable=True)
    
    # Trades
    trades = Column(JSONB, default=list)
    
    # Contact
    primary_contact_name = Column(String(255), nullable=True)
    primary_contact_email = Column(String(255), nullable=True)
    primary_contact_phone = Column(String(50), nullable=True)
    
    # Address
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    zip_code = Column(String(20), nullable=True)
    country = Column(String(100), default='USA')
    
    # License info
    license_number = Column(String(100), nullable=True)
    license_state = Column(String(100), nullable=True)
    license_expiry = Column(DateTime, nullable=True)
    
    # Insurance
    insurance_certificate_url = Column(String(500), nullable=True)
    insurance_expiry = Column(DateTime, nullable=True)
    
    # Status
    status = Column(String(50), default='pending')  # pending, approved, suspended, blacklisted
    
    # Portal access
    portal_enabled = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SubcontractorUser(Base):
    """Subcontractor portal user"""
    __tablename__ = 'subcontractor_users'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey('subcontractor_companies.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    # Role
    role = Column(String(50), default='user')  # admin, estimator, project_manager, field_worker
    
    # Permissions
    permissions = Column(JSONB, default=list)
    
    # Projects access
    allowed_projects = Column(JSONB, default=list)  # Empty = all projects
    
    # Access level
    access_level = Column(String(50), default=AccessLevel.SUBMIT.value)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class ProjectTradeAssignment(Base):
    """Trade assignment for project"""
    __tablename__ = 'project_trade_assignments'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey('subcontractor_companies.id', ondelete='CASCADE'), nullable=False)
    
    # Trade
    trade = Column(String(100), nullable=False)
    
    # Contract info
    contract_value = Column(Integer, nullable=True)  # in cents
    contract_start_date = Column(DateTime, nullable=True)
    contract_end_date = Column(DateTime, nullable=True)
    
    # Scope
    scope_description = Column(Text, nullable=True)
    
    # Status
    status = Column(String(50), default='active')
    
    created_at = Column(DateTime, default=datetime.utcnow)


# Pydantic Schemas

class CreateSubcontractorCompanyRequest(BaseModel):
    """Create subcontractor company request"""
    company_name: str
    trades: List[str]
    primary_contact_name: str
    primary_contact_email: str
    primary_contact_phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    license_number: Optional[str] = None
    license_state: Optional[str] = None


class CreateSubcontractorUserRequest(BaseModel):
    """Create subcontractor user request"""
    user_id: str
    role: str = 'user'
    permissions: List[str] = Field(default_factory=list)
    allowed_projects: List[str] = Field(default_factory=list)
    access_level: AccessLevel = AccessLevel.SUBMIT


class AssignTradeRequest(BaseModel):
    """Assign trade to project request"""
    company_id: str
    trade: str
    contract_value: Optional[int] = None
    contract_start_date: Optional[datetime] = None
    contract_end_date: Optional[datetime] = None
    scope_description: Optional[str] = None


# Service Classes

class ScopedAccessService:
    """Service for trade-specific scoped access"""
    
    TRADE_PERMISSIONS = {
        TradeType.ELECTRICAL: {
            'view_only': ['drawings_electrical', 'specifications'],
            'submit': ['rfis', 'submittals', 'daily_reports'],
            'edit': ['payment_applications', 'change_orders'],
            'admin': ['user_management', 'company_settings']
        },
        TradeType.PLUMBING: {
            'view_only': ['drawings_plumbing', 'specifications'],
            'submit': ['rfis', 'submittals', 'daily_reports'],
            'edit': ['payment_applications', 'change_orders'],
            'admin': ['user_management', 'company_settings']
        },
        TradeType.HVAC: {
            'view_only': ['drawings_mechanical', 'specifications'],
            'submit': ['rfis', 'submittals', 'daily_reports'],
            'edit': ['payment_applications', 'change_orders'],
            'admin': ['user_management', 'company_settings']
        }
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_company(
        self,
        tenant_id: str,
        request: CreateSubcontractorCompanyRequest
    ) -> SubcontractorCompany:
        """Create subcontractor company"""
        
        company = SubcontractorCompany(
            tenant_id=tenant_id,
            company_name=request.company_name,
            trades=request.trades,
            primary_contact_name=request.primary_contact_name,
            primary_contact_email=request.primary_contact_email,
            primary_contact_phone=request.primary_contact_phone,
            address=request.address,
            city=request.city,
            state=request.state,
            zip_code=request.zip_code,
            license_number=request.license_number,
            license_state=request.license_state
        )
        
        self.db.add(company)
        self.db.commit()
        self.db.refresh(company)
        
        return company
    
    def get_company(self, company_id: str) -> Optional[SubcontractorCompany]:
        """Get subcontractor company"""
        return self.db.query(SubcontractorCompany).filter(
            SubcontractorCompany.id == company_id
        ).first()
    
    def list_companies(
        self,
        tenant_id: str,
        trade: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[SubcontractorCompany]:
        """List subcontractor companies"""
        
        query = self.db.query(SubcontractorCompany).filter(
            SubcontractorCompany.tenant_id == tenant_id
        )
        
        if trade:
            query = query.filter(SubcontractorCompany.trades.contains([trade]))
        
        if status:
            query = query.filter(SubcontractorCompany.status == status)
        
        return query.order_by(SubcontractorCompany.company_name).all()
    
    def add_user(
        self,
        company_id: str,
        request: CreateSubcontractorUserRequest
    ) -> SubcontractorUser:
        """Add user to subcontractor company"""
        
        # Get company
        company = self.get_company(company_id)
        if not company:
            raise HTTPException(404, "Company not found")
        
        # Generate permissions based on role and trades
        permissions = self._generate_permissions(
            company.trades,
            request.role,
            request.access_level.value
        )
        
        sub_user = SubcontractorUser(
            company_id=company_id,
            user_id=request.user_id,
            role=request.role,
            permissions=permissions,
            allowed_projects=request.allowed_projects,
            access_level=request.access_level.value
        )
        
        self.db.add(sub_user)
        self.db.commit()
        self.db.refresh(sub_user)
        
        return sub_user
    
    def _generate_permissions(
        self,
        trades: List[str],
        role: str,
        access_level: str
    ) -> List[str]:
        """Generate permissions based on trades and role"""
        
        permissions = []
        
        for trade in trades:
            trade_perms = self.TRADE_PERMISSIONS.get(TradeType(trade), {})
            
            # Add permissions based on access level
            if access_level == 'view_only':
                permissions.extend(trade_perms.get('view_only', []))
            elif access_level == 'submit':
                permissions.extend(trade_perms.get('view_only', []))
                permissions.extend(trade_perms.get('submit', []))
            elif access_level == 'edit':
                permissions.extend(trade_perms.get('view_only', []))
                permissions.extend(trade_perms.get('submit', []))
                permissions.extend(trade_perms.get('edit', []))
            elif access_level == 'admin':
                permissions.extend(trade_perms.get('view_only', []))
                permissions.extend(trade_perms.get('submit', []))
                permissions.extend(trade_perms.get('edit', []))
                permissions.extend(trade_perms.get('admin', []))
        
        return list(set(permissions))
    
    def check_permission(
        self,
        user_id: str,
        permission: str,
        project_id: Optional[str] = None
    ) -> bool:
        """Check if user has permission"""
        
        sub_user = self.db.query(SubcontractorUser).filter(
            SubcontractorUser.user_id == user_id,
            SubcontractorUser.is_active == True
        ).first()
        
        if not sub_user:
            return False
        
        # Check permission
        if permission not in (sub_user.permissions or []):
            return False
        
        # Check project access
        if project_id and sub_user.allowed_projects:
            if project_id not in sub_user.allowed_projects:
                return False
        
        return True
    
    def assign_trade_to_project(
        self,
        project_id: str,
        request: AssignTradeRequest
    ) -> ProjectTradeAssignment:
        """Assign trade to project"""
        
        assignment = ProjectTradeAssignment(
            project_id=project_id,
            company_id=request.company_id,
            trade=request.trade,
            contract_value=request.contract_value,
            contract_start_date=request.contract_start_date,
            contract_end_date=request.contract_end_date,
            scope_description=request.scope_description
        )
        
        self.db.add(assignment)
        self.db.commit()
        self.db.refresh(assignment)
        
        return assignment
    
    def get_project_trades(self, project_id: str) -> List[ProjectTradeAssignment]:
        """Get trades assigned to project"""
        return self.db.query(ProjectTradeAssignment).filter(
            ProjectTradeAssignment.project_id == project_id,
            ProjectTradeAssignment.status == 'active'
        ).all()
    
    def get_user_projects(self, user_id: str) -> List[str]:
        """Get projects user has access to"""
        
        sub_user = self.db.query(SubcontractorUser).filter(
            SubcontractorUser.user_id == user_id,
            SubcontractorUser.is_active == True
        ).first()
        
        if not sub_user:
            return []
        
        # If specific projects allowed, return those
        if sub_user.allowed_projects:
            return sub_user.allowed_projects
        
        # Otherwise, get all projects for user's company trades
        company = self.get_company(str(sub_user.company_id))
        if not company:
            return []
        
        assignments = self.db.query(ProjectTradeAssignment).filter(
            ProjectTradeAssignment.company_id == company.id,
            ProjectTradeAssignment.status == 'active'
        ).all()
        
        return [str(a.project_id) for a in assignments]


# Export
__all__ = [
    'TradeType',
    'AccessLevel',
    'SubcontractorCompany',
    'SubcontractorUser',
    'ProjectTradeAssignment',
    'CreateSubcontractorCompanyRequest',
    'CreateSubcontractorUserRequest',
    'AssignTradeRequest',
    'ScopedAccessService'
]
