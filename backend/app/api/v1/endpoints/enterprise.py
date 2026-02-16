"""
Enterprise API Endpoints
Item 300: Enterprise API endpoints
"""

from typing import List, Optional
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user, require_permissions
from app.enterprise.tenant_isolation import (
    Tenant, TenantUser, TenantContext, get_current_tenant
)
from app.enterprise.tenant_onboarding import (
    TenantOnboardingService, OnboardingStartRequest, OnboardingResponse
)
from app.enterprise.sso_saml import SAMLService, SAMLProviderCreateRequest
from app.enterprise.sso_oidc import OIDCService, OIDCProviderCreateRequest
from app.enterprise.scim import SCIMService
from app.enterprise.audit_enterprise import AuditService, AuditLogQuery
from app.enterprise.support import SupportService, CreateTicketRequest
from app.enterprise.analytics import AnalyticsService
from app.enterprise.advanced_security import SecurityPolicyService, IPAllowlistService
from app.enterprise.data_residency import DataResidencyService

router = APIRouter(prefix="/enterprise", tags=["enterprise"])


# Tenant Management Endpoints

@router.get("/tenants", response_model=List[dict])
async def list_tenants(
    status: Optional[str] = None,
    tier: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permissions(["admin:tenants:read"]))
):
    """List all tenants (super admin only)"""
    query = db.query(Tenant)
    
    if status:
        query = query.filter(Tenant.status == status)
    if tier:
        query = query.filter(Tenant.tier == tier)
    
    tenants = query.all()
    
    return [
        {
            "id": str(t.id),
            "name": t.name,
            "slug": t.slug,
            "tier": t.tier,
            "status": t.status,
            "created_at": t.created_at.isoformat() if t.created_at else None
        }
        for t in tenants
    ]


@router.get("/tenants/{tenant_id}")
async def get_tenant(
    tenant_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permissions(["admin:tenants:read"]))
):
    """Get tenant details"""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    return {
        "id": str(tenant.id),
        "name": tenant.name,
        "slug": tenant.slug,
        "tier": tenant.tier,
        "status": tenant.status,
        "data_region": tenant.data_region,
        "features": tenant.features,
        "usage_limits": tenant.usage_limits,
        "created_at": tenant.created_at.isoformat() if tenant.created_at else None
    }


@router.put("/tenants/{tenant_id}")
async def update_tenant(
    tenant_id: UUID,
    updates: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permissions(["admin:tenants:write"]))
):
    """Update tenant settings"""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Update allowed fields
    allowed_fields = ["name", "tier", "status", "features", "usage_limits"]
    for field in allowed_fields:
        if field in updates:
            setattr(tenant, field, updates[field])
    
    db.commit()
    db.refresh(tenant)
    
    return {"message": "Tenant updated successfully"}


# Onboarding Endpoints

@router.post("/onboarding/start", response_model=OnboardingResponse)
async def start_onboarding(
    request: OnboardingStartRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Start tenant onboarding process"""
    service = TenantOnboardingService(db)
    return await service.start_onboarding(request, background_tasks)


@router.post("/onboarding/{onboarding_id}/verify-email")
async def verify_email(
    onboarding_id: UUID,
    token: str,
    db: Session = Depends(get_db)
):
    """Verify email during onboarding"""
    from app.enterprise.tenant_onboarding import OnboardingVerifyEmailRequest
    
    service = TenantOnboardingService(db)
    return await service.verify_email(str(onboarding_id), OnboardingVerifyEmailRequest(token=token))


@router.post("/onboarding/{onboarding_id}/complete")
async def complete_onboarding(
    onboarding_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Complete onboarding and create tenant"""
    service = TenantOnboardingService(db)
    return await service.complete_onboarding(str(onboarding_id), background_tasks)


# SSO/SAML Endpoints

@router.post("/saml/providers")
async def create_saml_provider(
    request: SAMLProviderCreateRequest,
    db: Session = Depends(get_db),
    current_tenant: Tenant = Depends(get_current_tenant)
):
    """Create SAML identity provider"""
    service = SAMLService(db)
    provider = await service.create_provider(str(current_tenant.id), request)
    
    return {
        "id": str(provider.id),
        "name": provider.name,
        "sp_entity_id": provider.sp_entity_id,
        "sp_acs_url": provider.sp_acs_url
    }


@router.get("/saml/providers")
async def list_saml_providers(
    db: Session = Depends(get_db),
    current_tenant: Tenant = Depends(get_current_tenant)
):
    """List SAML providers for tenant"""
    providers = db.query(SAMLProvider).filter(
        SAMLProvider.tenant_id == current_tenant.id
    ).all()
    
    return [
        {
            "id": str(p.id),
            "name": p.name,
            "provider_type": p.provider_type,
            "is_active": p.is_active,
            "is_primary": p.is_primary
        }
        for p in providers
    ]


@router.get("/saml/providers/{provider_id}/metadata")
async def get_saml_metadata(
    provider_id: UUID,
    db: Session = Depends(get_db)
):
    """Get SAML Service Provider metadata"""
    service = SAMLService(db)
    metadata = await service.generate_metadata(str(provider_id))
    
    return Response(content=metadata, media_type="application/xml")


# OIDC Endpoints

@router.post("/oidc/providers")
async def create_oidc_provider(
    request: OIDCProviderCreateRequest,
    db: Session = Depends(get_db),
    current_tenant: Tenant = Depends(get_current_tenant)
):
    """Create OIDC identity provider"""
    service = OIDCService(db)
    provider = await service.create_provider(str(current_tenant.id), request)
    
    return {
        "id": str(provider.id),
        "name": provider.name,
        "issuer_url": provider.issuer_url
    }


# SCIM Endpoints

@router.get("/scim/v2/Users")
async def scim_list_users(
    request: Request,
    filter: Optional[str] = None,
    startIndex: int = 1,
    count: int = 100,
    db: Session = Depends(get_db),
    current_tenant: Tenant = Depends(get_current_tenant)
):
    """SCIM 2.0 List Users endpoint"""
    service = SCIMService(db)
    
    # Verify SCIM authentication
    auth_header = request.headers.get('Authorization', '')
    if not service.authenticate_request(request, str(current_tenant.id)):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    response = service.list_users(
        str(current_tenant.id),
        filter_query=filter,
        start_index=startIndex,
        count=count
    )
    
    return response.model_dump()


@router.post("/scim/v2/Users")
async def scim_create_user(
    request: Request,
    user_data: dict,
    db: Session = Depends(get_db),
    current_tenant: Tenant = Depends(get_current_tenant)
):
    """SCIM 2.0 Create User endpoint"""
    from app.enterprise.scim import SCIMUserResource
    
    service = SCIMService(db)
    
    if not service.authenticate_request(request, str(current_tenant.id)):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user_resource = SCIMUserResource(**user_data)
    created = service.create_user(str(current_tenant.id), user_resource)
    
    return created.model_dump()


# Audit Endpoints

@router.get("/audit/logs")
async def query_audit_logs(
    tenant_id: Optional[UUID] = None,
    event_types: Optional[List[str]] = Query(None),
    actor_id: Optional[UUID] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permissions(["admin:audit:read"]))
):
    """Query audit logs"""
    service = AuditService(db)
    
    query = AuditLogQuery(
        tenant_id=str(tenant_id) if tenant_id else None,
        event_types=event_types or [],
        actor_id=str(actor_id) if actor_id else None,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset
    )
    
    logs, total = service.query_logs(query)
    
    return {
        "total": total,
        "logs": [
            {
                "id": str(log.id),
                "event_type": log.event_type,
                "event_category": log.event_category,
                "severity": log.severity,
                "actor_id": str(log.actor_id) if log.actor_id else None,
                "description": log.description,
                "created_at": log.created_at.isoformat() if log.created_at else None
            }
            for log in logs
        ]
    }


# Support Endpoints

@router.post("/support/tickets")
async def create_support_ticket(
    request: CreateTicketRequest,
    db: Session = Depends(get_db),
    current_tenant: Tenant = Depends(get_current_tenant),
    current_user: dict = Depends(get_current_user)
):
    """Create support ticket"""
    service = SupportService(db)
    ticket = service.create_ticket(
        str(current_tenant.id),
        current_user["id"],
        request
    )
    
    return {
        "id": str(ticket.id),
        "ticket_number": ticket.ticket_number,
        "subject": ticket.subject,
        "status": ticket.status,
        "priority": ticket.priority,
        "created_at": ticket.created_at.isoformat()
    }


@router.get("/support/tickets")
async def list_support_tickets(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_tenant: Tenant = Depends(get_current_tenant)
):
    """List support tickets"""
    from app.enterprise.support import TicketStatus, TicketPriority
    
    service = SupportService(db)
    
    tickets, total = service.list_tickets(
        str(current_tenant.id),
        status=TicketStatus(status) if status else None,
        priority=TicketPriority(priority) if priority else None,
        limit=limit,
        offset=offset
    )
    
    return {
        "total": total,
        "tickets": [
            {
                "id": str(t.id),
                "ticket_number": t.ticket_number,
                "subject": t.subject,
                "status": t.status,
                "priority": t.priority,
                "created_at": t.created_at.isoformat()
            }
            for t in tickets
        ]
    }


# Analytics Endpoints

@router.get("/analytics/dashboard")
async def get_analytics_dashboard(
    days: int = 30,
    db: Session = Depends(get_db),
    current_tenant: Tenant = Depends(get_current_tenant)
):
    """Get analytics dashboard data"""
    service = AnalyticsService(db)
    dashboard = service.get_dashboard_data(str(current_tenant.id), days)
    
    return dashboard.model_dump()


@router.get("/analytics/usage-limits")
async def check_usage_limits(
    db: Session = Depends(get_db),
    current_tenant: Tenant = Depends(get_current_tenant)
):
    """Check tenant usage limits"""
    service = AnalyticsService(db)
    return service.check_usage_limits(str(current_tenant.id))


# Security Endpoints

@router.get("/security/policy")
async def get_security_policy(
    db: Session = Depends(get_db),
    current_tenant: Tenant = Depends(get_current_tenant)
):
    """Get tenant security policy"""
    service = SecurityPolicyService(db)
    policy = service.get_or_create_policy(str(current_tenant.id))
    
    return {
        "policy_level": policy.policy_level,
        "password_min_length": policy.password_min_length,
        "password_require_uppercase": policy.password_require_uppercase,
        "password_require_lowercase": policy.password_require_lowercase,
        "password_require_numbers": policy.password_require_numbers,
        "password_require_special": policy.password_require_special,
        "mfa_required": policy.mfa_required,
        "session_timeout_minutes": policy.session_timeout_minutes,
        "max_login_attempts": policy.max_login_attempts
    }


@router.put("/security/policy")
async def update_security_policy(
    updates: dict,
    db: Session = Depends(get_db),
    current_tenant: Tenant = Depends(get_current_tenant),
    current_user: dict = Depends(require_permissions(["admin:security:write"]))
):
    """Update tenant security policy"""
    from app.enterprise.advanced_security import SecurityPolicyConfig, SecurityPolicyLevel
    
    service = SecurityPolicyService(db)
    
    config = SecurityPolicyConfig(
        policy_level=SecurityPolicyLevel(updates.get("policy_level", "medium")),
        password_min_length=updates.get("password_min_length", 8),
        password_require_uppercase=updates.get("password_require_uppercase", True),
        password_require_lowercase=updates.get("password_require_lowercase", True),
        password_require_numbers=updates.get("password_require_numbers", True),
        password_require_special=updates.get("password_require_special", False),
        mfa_required=updates.get("mfa_required", False),
        session_timeout_minutes=updates.get("session_timeout_minutes", 480),
        max_login_attempts=updates.get("max_login_attempts", 5)
    )
    
    policy = service.update_policy(str(current_tenant.id), config, current_user["id"])
    
    return {"message": "Security policy updated successfully"}


# IP Allowlist Endpoints

@router.get("/security/ip-allowlist")
async def list_ip_allowlist(
    db: Session = Depends(get_db),
    current_tenant: Tenant = Depends(get_current_tenant)
):
    """List IP allowlist entries"""
    from app.enterprise.advanced_security import IPAllowlistEntry
    
    entries = db.query(IPAllowlistEntry).filter(
        IPAllowlistEntry.tenant_id == current_tenant.id,
        IPAllowlistEntry.is_active == True
    ).all()
    
    return [
        {
            "id": str(e.id),
            "ip_address": str(e.ip_address) if e.ip_address else None,
            "ip_range": str(e.ip_range) if e.ip_range else None,
            "description": e.description,
            "allowed_actions": e.allowed_actions
        }
        for e in entries
    ]


@router.post("/security/ip-allowlist")
async def add_ip_allowlist(
    request: dict,
    db: Session = Depends(get_db),
    current_tenant: Tenant = Depends(get_current_tenant),
    current_user: dict = Depends(require_permissions(["admin:security:write"]))
):
    """Add IP to allowlist"""
    from app.enterprise.advanced_security import IPAllowlistEntryRequest
    
    service = IPAllowlistService(db)
    
    entry_request = IPAllowlistEntryRequest(
        ip_address=request.get("ip_address"),
        cidr_range=request.get("cidr_range"),
        description=request.get("description"),
        allowed_actions=request.get("allowed_actions", ["login", "api"]),
        expires_days=request.get("expires_days")
    )
    
    entry = service.add_entry(str(current_tenant.id), entry_request, current_user["id"])
    
    return {
        "id": str(entry.id),
        "message": "IP added to allowlist"
    }


# Data Residency Endpoints

@router.get("/data-residency/regions")
async def list_data_regions(
    db: Session = Depends(get_db)
):
    """List available data regions"""
    service = DataResidencyService(db)
    regions = service.list_available_regions()
    
    return [r.model_dump() for r in regions]


@router.get("/data-residency/config")
async def get_data_residency_config(
    db: Session = Depends(get_db),
    current_tenant: Tenant = Depends(get_current_tenant)
):
    """Get tenant data residency configuration"""
    from app.enterprise.data_residency import TenantDataResidency
    
    config = db.query(TenantDataResidency).filter(
        TenantDataResidency.tenant_id == current_tenant.id
    ).first()
    
    if not config:
        return {
            "primary_region": current_tenant.data_region,
            "replicated_regions": [],
            "backup_enabled": True
        }
    
    return {
        "primary_region": config.primary_region,
        "replicated_regions": config.replicated_regions,
        "replication_mode": config.replication_mode,
        "backup_enabled": config.backup_enabled,
        "backup_region": config.backup_region,
        "required_compliance": config.required_compliance
    }


# Export router
__all__ = ["router"]
