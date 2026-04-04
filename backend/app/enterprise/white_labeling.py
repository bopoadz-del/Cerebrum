"""
White Labeling Module - Custom domain, branding, and CSS customization
Item 283: White-labeling support
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
from app.db.base_class import Base
import re

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Session
from pydantic import BaseModel, validator, HttpUrl
from fastapi import HTTPException, Request, Response
from fastapi.responses import HTMLResponse
import boto3
from botocore.exceptions import ClientError


# Database Models

class WhiteLabelConfig(Base):
    """White-label configuration for tenants"""
    __tablename__ = 'white_label_configs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, unique=True)
    
    # Domain Settings
    custom_domain = Column(String(255), nullable=True, unique=True)
    domain_verified = Column(Boolean, default=False)
    domain_verification_token = Column(String(255), nullable=True)
    ssl_certificate_arn = Column(String(500), nullable=True)
    
    # Branding
    company_name = Column(String(255), nullable=True)
    logo_light_url = Column(String(500), nullable=True)
    logo_dark_url = Column(String(500), nullable=True)
    favicon_url = Column(String(500), nullable=True)
    
    # Colors
    primary_color = Column(String(7), default='#007bff')
    secondary_color = Column(String(7), default='#6c757d')
    accent_color = Column(String(7), default='#28a745')
    background_color = Column(String(7), default='#ffffff')
    text_color = Column(String(7), default='#212529')
    
    # Typography
    font_family = Column(String(100), default='Inter, sans-serif')
    heading_font = Column(String(100), nullable=True)
    
    # Custom CSS
    custom_css = Column(Text, nullable=True)
    custom_js = Column(Text, nullable=True)
    
    # Email Branding
    email_header_image = Column(String(500), nullable=True)
    email_footer_html = Column(Text, nullable=True)
    email_sender_name = Column(String(255), nullable=True)
    email_sender_address = Column(String(255), nullable=True)
    
    # Login Page
    login_background_image = Column(String(500), nullable=True)
    login_page_title = Column(String(255), default='Sign In')
    login_page_subtitle = Column(String(500), nullable=True)
    show_powered_by = Column(Boolean, default=True)
    
    # Features visibility
    hidden_features = Column(JSONB, default=list)
    renamed_features = Column(JSONB, default=dict)
    
    # Metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)


class DomainVerification(Base):
    """Domain verification records"""
    __tablename__ = 'domain_verifications'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    
    domain = Column(String(255), nullable=False)
    verification_method = Column(String(50), default='dns_txt')  # dns_txt, file, meta_tag
    verification_token = Column(String(255), nullable=False)
    
    # DNS record details
    dns_record_type = Column(String(10), default='TXT')
    dns_record_name = Column(String(255), nullable=True)
    dns_record_value = Column(String(500), nullable=True)
    
    verified_at = Column(DateTime, nullable=True)
    verification_attempts = Column(Integer, default=0)
    last_verified_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)


# Pydantic Schemas

class BrandingColors(BaseModel):
    primary: str = '#007bff'
    secondary: str = '#6c757d'
    accent: str = '#28a745'
    background: str = '#ffffff'
    text: str = '#212529'


class WhiteLabelConfigRequest(BaseModel):
    """Update white-label config request"""
    company_name: Optional[str] = None
    colors: Optional[BrandingColors] = None
    font_family: Optional[str] = None
    custom_css: Optional[str] = None
    login_page_title: Optional[str] = None
    login_page_subtitle: Optional[str] = None
    show_powered_by: Optional[bool] = None
    hidden_features: Optional[List[str]] = None
    renamed_features: Optional[Dict[str, str]] = None
    
    @validator('custom_css')
    def validate_css(cls, v):
        if v:
            # Basic XSS prevention - check for script tags
            if re.search(r'<script|javascript:|on\w+\s*=', v, re.IGNORECASE):
                raise ValueError('CSS contains forbidden content')
        return v


class CustomDomainRequest(BaseModel):
    """Add custom domain request"""
    domain: str
    
    @validator('domain')
    def validate_domain(cls, v):
        # Validate domain format
        if not re.match(r'^[a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,}$', v):
            raise ValueError('Invalid domain format')
        return v.lower()


class WhiteLabelConfigResponse(BaseModel):
    """White-label config response"""
    tenant_id: str
    custom_domain: Optional[str]
    domain_verified: bool
    company_name: Optional[str]
    colors: Dict[str, str]
    logo_light_url: Optional[str]
    logo_dark_url: Optional[str]
    favicon_url: Optional[str]
    font_family: str
    custom_css: Optional[str]
    login_page_title: str
    show_powered_by: bool


# Service Classes

class WhiteLabelService:
    """Service for managing white-label configurations"""
    
    def __init__(self, db: Session, s3_client=None, cloudfront_client=None):
        self.db = db
        self.s3 = s3_client or boto3.client('s3')
        self.cloudfront = cloudfront_client or boto3.client('cloudfront')
        self.assets_bucket = 'cerebrum-white-label-assets'
    
    def get_config(self, tenant_id: str) -> Optional[WhiteLabelConfig]:
        """Get white-label config for tenant"""
        return self.db.query(WhiteLabelConfig).filter(
            WhiteLabelConfig.tenant_id == tenant_id
        ).first()
    
    async def update_config(
        self,
        tenant_id: str,
        request: WhiteLabelConfigRequest,
        updated_by: Optional[str] = None
    ) -> WhiteLabelConfig:
        """Update white-label configuration"""
        
        config = self.get_config(tenant_id)
        
        if not config:
            config = WhiteLabelConfig(tenant_id=tenant_id)
            self.db.add(config)
        
        # Update fields
        if request.company_name is not None:
            config.company_name = request.company_name
        
        if request.colors:
            config.primary_color = request.colors.primary
            config.secondary_color = request.colors.secondary
            config.accent_color = request.colors.accent
            config.background_color = request.colors.background
            config.text_color = request.colors.text
        
        if request.font_family:
            config.font_family = request.font_family
        
        if request.custom_css is not None:
            config.custom_css = self._sanitize_css(request.custom_css)
        
        if request.login_page_title is not None:
            config.login_page_title = request.login_page_title
        
        if request.login_page_subtitle is not None:
            config.login_page_subtitle = request.login_page_subtitle
        
        if request.show_powered_by is not None:
            config.show_powered_by = request.show_powered_by
        
        if request.hidden_features is not None:
            config.hidden_features = request.hidden_features
        
        if request.renamed_features is not None:
            config.renamed_features = request.renamed_features
        
        config.updated_by = updated_by
        config.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(config)
        
        return config
    
    async def upload_logo(
        self,
        tenant_id: str,
        logo_file: bytes,
        logo_type: str = 'light',
        content_type: str = 'image/png'
    ) -> str:
        """Upload tenant logo"""
        
        # Generate unique key
        key = f"logos/{tenant_id}/{logo_type}_{uuid.uuid4()}.png"
        
        # Upload to S3
        self.s3.put_object(
            Bucket=self.assets_bucket,
            Key=key,
            Body=logo_file,
            ContentType=content_type,
            ACL='public-read'
        )
        
        # Generate URL
        url = f"https://{self.assets_bucket}.s3.amazonaws.com/{key}"
        
        # Update config
        config = self.get_config(tenant_id)
        if not config:
            config = WhiteLabelConfig(tenant_id=tenant_id)
            self.db.add(config)
        
        if logo_type == 'light':
            config.logo_light_url = url
        else:
            config.logo_dark_url = url
        
        self.db.commit()
        
        return url
    
    async def add_custom_domain(
        self,
        tenant_id: str,
        request: CustomDomainRequest
    ) -> Dict[str, Any]:
        """Add custom domain for tenant"""
        
        # Check if domain is already in use
        existing = self.db.query(WhiteLabelConfig).filter(
            WhiteLabelConfig.custom_domain == request.domain
        ).first()
        
        if existing and existing.tenant_id != uuid.UUID(tenant_id):
            raise HTTPException(400, "Domain already in use by another tenant")
        
        # Generate verification token
        verification_token = f"cerebrum-verify-{uuid.uuid4().hex[:16]}"
        
        config = self.get_config(tenant_id)
        if not config:
            config = WhiteLabelConfig(tenant_id=tenant_id)
            self.db.add(config)
        
        config.custom_domain = request.domain
        config.domain_verified = False
        config.domain_verification_token = verification_token
        
        self.db.commit()
        
        # Create verification record
        verification = DomainVerification(
            tenant_id=tenant_id,
            domain=request.domain,
            verification_token=verification_token,
            dns_record_type='TXT',
            dns_record_name='_cerebrum',
            dns_record_value=verification_token
        )
        
        self.db.add(verification)
        self.db.commit()
        
        return {
            'domain': request.domain,
            'verification_token': verification_token,
            'dns_instructions': {
                'type': 'TXT',
                'name': '_cerebrum.' + request.domain,
                'value': verification_token
            }
        }
    
    async def verify_domain(self, tenant_id: str, domain: str) -> Dict[str, Any]:
        """Verify custom domain ownership"""
        
        config = self.get_config(tenant_id)
        
        if not config or config.custom_domain != domain:
            raise HTTPException(400, "Domain not configured for this tenant")
        
        verification = self.db.query(DomainVerification).filter(
            DomainVerification.tenant_id == tenant_id,
            DomainVerification.domain == domain
        ).order_by(DomainVerification.created_at.desc()).first()
        
        if not verification:
            raise HTTPException(400, "No verification record found")
        
        # Attempt DNS verification
        import dns.resolver
        
        try:
            answers = dns.resolver.resolve(f"_cerebrum.{domain}", 'TXT')
            for rdata in answers:
                for txt_string in rdata.strings:
                    if verification.verification_token in txt_string.decode():
                        # Verification successful
                        config.domain_verified = True
                        verification.verified_at = datetime.utcnow()
                        verification.last_verified_at = datetime.utcnow()
                        
                        self.db.commit()
                        
                        # Setup CloudFront distribution
                        await self._setup_cloudfront_distribution(tenant_id, domain)
                        
                        return {
                            'verified': True,
                            'message': 'Domain verified successfully'
                        }
        except Exception as e:
            verification.verification_attempts += 1
            self.db.commit()
            
            return {
                'verified': False,
                'message': f'DNS verification failed: {str(e)}',
                'attempts': verification.verification_attempts
            }
        
        return {
            'verified': False,
            'message': 'Verification token not found in DNS'
        }
    
    async def _setup_cloudfront_distribution(self, tenant_id: str, domain: str):
        """Setup CloudFront distribution for custom domain"""
        
        # This would create a CloudFront distribution
        # For now, just a placeholder
        pass
    
    def generate_css(self, tenant_id: str) -> str:
        """Generate custom CSS for tenant"""
        
        config = self.get_config(tenant_id)
        
        if not config:
            return ""
        
        base_css = f"""
        :root {{
            --primary-color: {config.primary_color};
            --secondary-color: {config.secondary_color};
            --accent-color: {config.accent_color};
            --background-color: {config.background_color};
            --text-color: {config.text_color};
            --font-family: {config.font_family};
        }}
        
        body {{
            font-family: var(--font-family);
            background-color: var(--background-color);
            color: var(--text-color);
        }}
        
        .btn-primary {{
            background-color: var(--primary-color);
            border-color: var(--primary-color);
        }}
        
        .btn-primary:hover {{
            background-color: var(--primary-color);
            opacity: 0.9;
        }}
        
        .text-primary {{
            color: var(--primary-color) !important;
        }}
        
        .bg-primary {{
            background-color: var(--primary-color) !important;
        }}
        
        .sidebar {{
            background-color: var(--background-color);
        }}
        
        .navbar {{
            background-color: var(--background-color);
            border-bottom: 1px solid rgba(0,0,0,0.1);
        }}
        """
        
        if config.custom_css:
            base_css += f"\n\n/* Custom CSS */\n{config.custom_css}"
        
        return base_css
    
    def get_branding_data(self, tenant_id: str) -> Dict[str, Any]:
        """Get branding data for frontend"""
        
        config = self.get_config(tenant_id)
        
        if not config:
            return self._get_default_branding()
        
        return {
            'company_name': config.company_name or 'Cerebrum AI',
            'logo_light': config.logo_light_url,
            'logo_dark': config.logo_dark_url,
            'favicon': config.favicon_url,
            'colors': {
                'primary': config.primary_color,
                'secondary': config.secondary_color,
                'accent': config.accent_color,
                'background': config.background_color,
                'text': config.text_color
            },
            'font_family': config.font_family,
            'login_page_title': config.login_page_title,
            'login_page_subtitle': config.login_page_subtitle,
            'show_powered_by': config.show_powered_by,
            'hidden_features': config.hidden_features,
            'renamed_features': config.renamed_features
        }
    
    def _get_default_branding(self) -> Dict[str, Any]:
        """Get default branding"""
        return {
            'company_name': 'Cerebrum AI',
            'logo_light': '/assets/logo-light.svg',
            'logo_dark': '/assets/logo-dark.svg',
            'favicon': '/assets/favicon.ico',
            'colors': {
                'primary': '#007bff',
                'secondary': '#6c757d',
                'accent': '#28a745',
                'background': '#ffffff',
                'text': '#212529'
            },
            'font_family': 'Inter, sans-serif',
            'login_page_title': 'Sign In',
            'login_page_subtitle': 'Welcome back to Cerebrum AI',
            'show_powered_by': True,
            'hidden_features': [],
            'renamed_features': {}
        }
    
    def _sanitize_css(self, css: str) -> str:
        """Sanitize custom CSS for security"""
        # Remove potentially dangerous CSS
        dangerous_patterns = [
            r'expression\s*\(',
            r'javascript\s*:',
            r'@import\s+url\s*\(',
            r'behavior\s*:',
            r'-moz-binding',
        ]
        
        sanitized = css
        for pattern in dangerous_patterns:
            sanitized = re.sub(pattern, '/* removed */', sanitized, flags=re.IGNORECASE)
        
        return sanitized


# Middleware for serving branded content

class WhiteLabelMiddleware:
    """Middleware to handle white-label requests"""
    
    def __init__(self, app, db_session_factory):
        self.app = app
        self.db_session_factory = db_session_factory
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        host = request.headers.get('host', '')
        
        # Check if custom domain
        db = self.db_session_factory()
        try:
            config = db.query(WhiteLabelConfig).filter(
                WhiteLabelConfig.custom_domain == host,
                WhiteLabelConfig.domain_verified == True
            ).first()
            
            if config:
                # Add tenant info to scope
                scope['tenant_id'] = str(config.tenant_id)
                scope['white_label_config'] = config
        finally:
            db.close()
        
        await self.app(scope, receive, send)


# Export
__all__ = [
    'WhiteLabelConfig',
    'DomainVerification',
    'BrandingColors',
    'WhiteLabelConfigRequest',
    'CustomDomainRequest',
    'WhiteLabelConfigResponse',
    'WhiteLabelService',
    'WhiteLabelMiddleware'
]
