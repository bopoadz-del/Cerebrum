"""
Tenant Onboarding Module - Self-service signup with Stripe integration
Item 282: Self-service tenant onboarding
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import uuid
import re

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, validator, Field
from fastapi import HTTPException, BackgroundTasks
import stripe
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# Stripe configuration
stripe.api_key = "sk_test_..."  # Set from environment


# Database Models

class TenantOnboarding(Base):
    """Tenant onboarding tracking"""
    __tablename__ = 'tenant_onboardings'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=True)
    
    # Contact info
    email = Column(String(255), nullable=False, index=True)
    company_name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    
    # Onboarding progress
    step = Column(String(50), default='started')  # started, email_verified, company_info, plan_selected, payment_setup, completed
    progress_percentage = Column(Integer, default=0)
    
    # Verification
    verification_token = Column(String(255), nullable=True)
    verification_sent_at = Column(DateTime, nullable=True)
    email_verified_at = Column(DateTime, nullable=True)
    
    # Selected plan
    selected_tier = Column(String(50), nullable=True)
    selected_addons = Column(JSONB, default=list)
    
    # Payment
    stripe_setup_intent_id = Column(String(255), nullable=True)
    payment_method_id = Column(String(255), nullable=True)
    
    # Data residency preference
    preferred_region = Column(String(50), default='us-east')
    
    # Metadata
    source = Column(String(100), nullable=True)  # organic, referral, ad, etc.
    utm_data = Column(JSONB, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=7))


class OnboardingInvite(Base):
    """Invitations to join existing tenant"""
    __tablename__ = 'onboarding_invites'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    invited_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    
    email = Column(String(255), nullable=False)
    role = Column(String(50), default='member')
    
    token = Column(String(255), unique=True, nullable=False)
    
    accepted_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=7))
    
    created_at = Column(DateTime, default=datetime.utcnow)


# Pydantic Schemas

class OnboardingStartRequest(BaseModel):
    """Start onboarding request"""
    email: EmailStr
    company_name: str = Field(..., min_length=2, max_length=255)
    phone: Optional[str] = None
    preferred_region: str = 'us-east'
    source: Optional[str] = None
    
    @validator('company_name')
    def validate_company_name(cls, v):
        if not re.match(r'^[\w\s\-\.&]+$', v):
            raise ValueError('Invalid company name')
        return v.strip()


class OnboardingVerifyEmailRequest(BaseModel):
    """Verify email request"""
    token: str


class OnboardingCompanyInfoRequest(BaseModel):
    """Company info request"""
    industry: str
    company_size: str
    country: str
    state: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    postal_code: Optional[str] = None
    tax_id: Optional[str] = None


class OnboardingPlanSelectionRequest(BaseModel):
    """Plan selection request"""
    tier: str
    billing_cycle: str = 'monthly'  # monthly, annual
    addons: List[str] = []


class OnboardingPaymentRequest(BaseModel):
    """Payment setup request"""
    payment_method_id: str
    billing_address: Dict[str, Any]


class OnboardingResponse(BaseModel):
    """Onboarding response"""
    onboarding_id: str
    step: str
    progress_percentage: int
    next_step: Optional[str]
    stripe_client_secret: Optional[str]


# Service Classes

class TenantOnboardingService:
    """Service for managing tenant onboarding"""
    
    PRICING_TIERS = {
        'starter': {
            'monthly': 49,
            'annual': 499,
            'features': ['5_users', '10_projects', 'basic_support'],
            'limits': {'users': 5, 'projects': 10, 'storage_gb': 50}
        },
        'professional': {
            'monthly': 149,
            'annual': 1499,
            'features': ['unlimited_users', 'unlimited_projects', 'priority_support', 'api_access'],
            'limits': {'users': None, 'projects': None, 'storage_gb': 500}
        },
        'enterprise': {
            'monthly': 499,
            'annual': 4999,
            'features': ['everything', 'dedicated_support', 'sso', 'sla', 'custom_integrations'],
            'limits': {'users': None, 'projects': None, 'storage_gb': 5000}
        }
    }
    
    ADDONS = {
        'additional_storage': {'monthly': 10, 'unit': '100GB'},
        'additional_api_calls': {'monthly': 25, 'unit': '10000_calls'},
        'premium_support': {'monthly': 99, 'unit': 'package'},
        'white_label': {'monthly': 199, 'unit': 'package'},
        'advanced_analytics': {'monthly': 49, 'unit': 'package'}
    }
    
    def __init__(self, db: Session, sendgrid_client: Optional[SendGridAPIClient] = None):
        self.db = db
        self.sendgrid = sendgrid_client
    
    async def start_onboarding(
        self, 
        request: OnboardingStartRequest,
        background_tasks: BackgroundTasks
    ) -> OnboardingResponse:
        """Start new tenant onboarding"""
        
        # Check if email already exists
        existing = self.db.query(Tenant).filter(
            Tenant.slug == self._generate_slug(request.company_name)
        ).first()
        
        if existing:
            raise HTTPException(400, "Company name already registered")
        
        # Create onboarding record
        verification_token = str(uuid.uuid4())
        onboarding = TenantOnboarding(
            email=request.email,
            company_name=request.company_name,
            phone=request.phone,
            preferred_region=request.preferred_region,
            source=request.source,
            verification_token=verification_token,
            verification_sent_at=datetime.utcnow(),
            step='started',
            progress_percentage=10
        )
        
        self.db.add(onboarding)
        self.db.commit()
        
        # Send verification email
        background_tasks.add_task(
            self._send_verification_email,
            request.email,
            request.company_name,
            verification_token
        )
        
        return OnboardingResponse(
            onboarding_id=str(onboarding.id),
            step=onboarding.step,
            progress_percentage=onboarding.progress_percentage,
            next_step='email_verification'
        )
    
    async def verify_email(
        self, 
        onboarding_id: str,
        request: OnboardingVerifyEmailRequest
    ) -> OnboardingResponse:
        """Verify email address"""
        
        onboarding = self.db.query(TenantOnboarding).filter(
            TenantOnboarding.id == onboarding_id,
            TenantOnboarding.verification_token == request.token
        ).first()
        
        if not onboarding:
            raise HTTPException(400, "Invalid verification token")
        
        if onboarding.expires_at < datetime.utcnow():
            raise HTTPException(400, "Verification link expired")
        
        onboarding.email_verified_at = datetime.utcnow()
        onboarding.step = 'email_verified'
        onboarding.progress_percentage = 25
        self.db.commit()
        
        return OnboardingResponse(
            onboarding_id=str(onboarding.id),
            step=onboarding.step,
            progress_percentage=onboarding.progress_percentage,
            next_step='company_info'
        )
    
    async def save_company_info(
        self,
        onboarding_id: str,
        request: OnboardingCompanyInfoRequest
    ) -> OnboardingResponse:
        """Save company information"""
        
        onboarding = self._get_onboarding(onboarding_id)
        
        # Store company info in metadata
        onboarding.utm_data = {
            'industry': request.industry,
            'company_size': request.company_size,
            'address': {
                'country': request.country,
                'state': request.state,
                'city': request.city,
                'address': request.address,
                'postal_code': request.postal_code
            },
            'tax_id': request.tax_id
        }
        
        onboarding.step = 'company_info'
        onboarding.progress_percentage = 40
        self.db.commit()
        
        return OnboardingResponse(
            onboarding_id=str(onboarding.id),
            step=onboarding.step,
            progress_percentage=onboarding.progress_percentage,
            next_step='plan_selection'
        )
    
    async def select_plan(
        self,
        onboarding_id: str,
        request: OnboardingPlanSelectionRequest
    ) -> OnboardingResponse:
        """Select subscription plan"""
        
        onboarding = self._get_onboarding(onboarding_id)
        
        if request.tier not in self.PRICING_TIERS:
            raise HTTPException(400, "Invalid plan tier")
        
        onboarding.selected_tier = request.tier
        onboarding.selected_addons = request.addons
        onboarding.step = 'plan_selected'
        onboarding.progress_percentage = 60
        
        # Calculate price
        tier_price = self.PRICING_TIERS[request.tier][request.billing_cycle]
        addons_price = sum(
            self.ADDONS.get(addon, {}).get(request.billing_cycle, 0)
            for addon in request.addons
        )
        
        # Create Stripe Setup Intent for payment method collection
        setup_intent = stripe.SetupIntent.create(
            customer_data={
                'email': onboarding.email,
                'name': onboarding.company_name
            },
            metadata={
                'onboarding_id': str(onboarding.id),
                'tier': request.tier,
                'billing_cycle': request.billing_cycle
            }
        )
        
        onboarding.stripe_setup_intent_id = setup_intent.id
        self.db.commit()
        
        return OnboardingResponse(
            onboarding_id=str(onboarding.id),
            step=onboarding.step,
            progress_percentage=onboarding.progress_percentage,
            next_step='payment_setup',
            stripe_client_secret=setup_intent.client_secret
        )
    
    async def setup_payment(
        self,
        onboarding_id: str,
        request: OnboardingPaymentRequest
    ) -> OnboardingResponse:
        """Setup payment method"""
        
        onboarding = self._get_onboarding(onboarding_id)
        
        # Attach payment method to setup intent
        setup_intent = stripe.SetupIntent.retrieve(onboarding.stripe_setup_intent_id)
        
        if setup_intent.status != 'succeeded':
            raise HTTPException(400, "Payment setup incomplete")
        
        onboarding.payment_method_id = request.payment_method_id
        onboarding.step = 'payment_setup'
        onboarding.progress_percentage = 80
        self.db.commit()
        
        return OnboardingResponse(
            onboarding_id=str(onboarding.id),
            step=onboarding.step,
            progress_percentage=onboarding.progress_percentage,
            next_step='complete'
        )
    
    async def complete_onboarding(
        self,
        onboarding_id: str,
        background_tasks: BackgroundTasks
    ) -> Dict[str, Any]:
        """Complete onboarding and create tenant"""
        
        onboarding = self._get_onboarding(onboarding_id)
        
        if onboarding.step != 'payment_setup':
            raise HTTPException(400, "Onboarding not ready for completion")
        
        # Create Stripe customer
        customer = stripe.Customer.create(
            email=onboarding.email,
            name=onboarding.company_name,
            payment_method=onboarding.payment_method_id,
            invoice_settings={
                'default_payment_method': onboarding.payment_method_id
            }
        )
        
        # Create subscription
        subscription = stripe.Subscription.create(
            customer=customer.id,
            items=[{'price': self._get_stripe_price_id(onboarding.selected_tier)}],
            metadata={'onboarding_id': str(onboarding.id)}
        )
        
        # Create tenant
        tenant = Tenant(
            name=onboarding.company_name,
            slug=self._generate_slug(onboarding.company_name),
            tier=onboarding.selected_tier,
            status='active',
            stripe_customer_id=customer.id,
            stripe_subscription_id=subscription.id,
            data_region=onboarding.preferred_region,
            usage_limits=self.PRICING_TIERS[onboarding.selected_tier]['limits'],
            trial_ends_at=datetime.utcnow() + timedelta(days=14)
        )
        
        self.db.add(tenant)
        self.db.flush()
        
        # Update onboarding
        onboarding.tenant_id = tenant.id
        onboarding.step = 'completed'
        onboarding.progress_percentage = 100
        onboarding.completed_at = datetime.utcnow()
        
        self.db.commit()
        
        # Send welcome email
        background_tasks.add_task(
            self._send_welcome_email,
            onboarding.email,
            tenant.name,
            tenant.slug
        )
        
        return {
            'tenant_id': str(tenant.id),
            'tenant_slug': tenant.slug,
            'subscription_status': subscription.status,
            'trial_ends_at': tenant.trial_ends_at.isoformat()
        }
    
    def _get_onboarding(self, onboarding_id: str) -> TenantOnboarding:
        """Get onboarding by ID"""
        onboarding = self.db.query(TenantOnboarding).filter(
            TenantOnboarding.id == onboarding_id
        ).first()
        
        if not onboarding:
            raise HTTPException(404, "Onboarding not found")
        
        return onboarding
    
    def _generate_slug(self, company_name: str) -> str:
        """Generate URL-friendly slug from company name"""
        slug = re.sub(r'[^\w\s-]', '', company_name.lower())
        slug = re.sub(r'[-\s]+', '-', slug)
        return slug[:50]
    
    def _get_stripe_price_id(self, tier: str) -> str:
        """Get Stripe price ID for tier"""
        price_map = {
            'starter': 'price_starter_monthly',
            'professional': 'price_professional_monthly',
            'enterprise': 'price_enterprise_monthly'
        }
        return price_map.get(tier, 'price_starter_monthly')
    
    async def _send_verification_email(self, email: str, company: str, token: str):
        """Send email verification"""
        if not self.sendgrid:
            return
        
        verification_url = f"https://app.cerebrum.ai/onboarding/verify?token={token}"
        
        message = Mail(
            from_email='onboarding@cerebrum.ai',
            to_emails=email,
            subject='Verify your email - Cerebrum AI',
            html_content=f"""
            <h1>Welcome to Cerebrum AI, {company}!</h1>
            <p>Please verify your email by clicking the link below:</p>
            <a href="{verification_url}" style="padding: 12px 24px; background: #007bff; color: white; text-decoration: none; border-radius: 4px;">Verify Email</a>
            <p>Or copy and paste: {verification_url}</p>
            """
        )
        
        try:
            self.sendgrid.send(message)
        except Exception as e:
            print(f"Failed to send email: {e}")
    
    async def _send_welcome_email(self, email: str, company: str, slug: str):
        """Send welcome email"""
        if not self.sendgrid:
            return
        
        login_url = f"https://{slug}.cerebrum.ai/login"
        
        message = Mail(
            from_email='welcome@cerebrum.ai',
            to_emails=email,
            subject='Welcome to Cerebrum AI - Your account is ready!',
            html_content=f"""
            <h1>Welcome to Cerebrum AI, {company}!</h1>
            <p>Your account has been successfully created.</p>
            <p>Get started by logging in:</p>
            <a href="{login_url}" style="padding: 12px 24px; background: #28a745; color: white; text-decoration: none; border-radius: 4px;">Log In</a>
            <p>Your custom URL: {login_url}</p>
            """
        )
        
        try:
            self.sendgrid.send(message)
        except Exception as e:
            print(f"Failed to send email: {e}")


# Invite Management

class InviteService:
    """Manage invitations to join tenants"""
    
    def __init__(self, db: Session, sendgrid_client: Optional[SendGridAPIClient] = None):
        self.db = db
        self.sendgrid = sendgrid_client
    
    async def create_invite(
        self,
        tenant_id: str,
        invited_by: str,
        email: str,
        role: str = 'member'
    ) -> Dict[str, Any]:
        """Create invitation to join tenant"""
        
        # Check if user already member
        existing = self.db.query(TenantUser).filter(
            TenantUser.tenant_id == tenant_id,
            TenantUser.user_id == User.id,
            User.email == email
        ).first()
        
        if existing:
            raise HTTPException(400, "User already a member of this tenant")
        
        token = str(uuid.uuid4())
        invite = OnboardingInvite(
            tenant_id=tenant_id,
            invited_by=invited_by,
            email=email,
            role=role,
            token=token
        )
        
        self.db.add(invite)
        self.db.commit()
        
        # Send invite email
        await self._send_invite_email(invite)
        
        return {
            'invite_id': str(invite.id),
            'email': email,
            'expires_at': invite.expires_at.isoformat()
        }
    
    async def accept_invite(self, token: str, user_id: str) -> Dict[str, Any]:
        """Accept invitation"""
        
        invite = self.db.query(OnboardingInvite).filter(
            OnboardingInvite.token == token,
            OnboardingInvite.expires_at > datetime.utcnow(),
            OnboardingInvite.accepted_at.is_(None)
        ).first()
        
        if not invite:
            raise HTTPException(400, "Invalid or expired invitation")
        
        # Add user to tenant
        tenant_user = TenantUser(
            tenant_id=invite.tenant_id,
            user_id=user_id,
            role=invite.role,
            joined_at=datetime.utcnow()
        )
        
        invite.accepted_at = datetime.utcnow()
        
        self.db.add(tenant_user)
        self.db.commit()
        
        return {
            'tenant_id': str(invite.tenant_id),
            'role': invite.role
        }
    
    async def _send_invite_email(self, invite: OnboardingInvite):
        """Send invitation email"""
        if not self.sendgrid:
            return
        
        tenant = self.db.query(Tenant).filter(Tenant.id == invite.tenant_id).first()
        inviter = self.db.query(User).filter(User.id == invite.invited_by).first()
        
        invite_url = f"https://app.cerebrum.ai/invite/accept?token={invite.token}"
        
        message = Mail(
            from_email='invites@cerebrum.ai',
            to_emails=invite.email,
            subject=f'{inviter.full_name} invited you to join {tenant.name} on Cerebrum AI',
            html_content=f"""
            <h1>You've been invited to join {tenant.name}</h1>
            <p>{inviter.full_name} has invited you to collaborate on Cerebrum AI.</p>
            <a href="{invite_url}" style="padding: 12px 24px; background: #007bff; color: white; text-decoration: none; border-radius: 4px;">Accept Invitation</a>
            <p>This invitation expires on {invite.expires_at.strftime('%B %d, %Y')}</p>
            """
        )
        
        try:
            self.sendgrid.send(message)
        except Exception as e:
            print(f"Failed to send invite: {e}")


# Export
__all__ = [
    'TenantOnboarding',
    'OnboardingInvite',
    'OnboardingStartRequest',
    'OnboardingVerifyEmailRequest',
    'OnboardingCompanyInfoRequest',
    'OnboardingPlanSelectionRequest',
    'OnboardingPaymentRequest',
    'OnboardingResponse',
    'TenantOnboardingService',
    'InviteService'
]
