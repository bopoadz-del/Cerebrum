"""
SSO SAML 2.0 Integration Module
Item 284: SAML 2.0 SSO with python3-saml
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
from app.db.base_class import Base
import base64
from urllib.parse import urlparse

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Session
from pydantic import BaseModel, HttpUrl, Field
from fastapi import HTTPException, Request, Response
from fastapi.responses import RedirectResponse, HTMLResponse
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.settings import OneLogin_Saml2_Settings
from onelogin.saml2.utils import OneLogin_Saml2_Utils
import xml.etree.ElementTree as ET


# Database Models

class SAMLProvider(Base):
    """SAML Identity Provider configuration"""
    __tablename__ = 'saml_providers'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    
    # Provider info
    name = Column(String(255), nullable=False)
    provider_type = Column(String(50), default='generic')  # okta, azure_ad, google, generic
    
    # IdP Configuration
    idp_entity_id = Column(String(500), nullable=False)
    idp_sso_url = Column(String(500), nullable=False)
    idp_slo_url = Column(String(500), nullable=True)
    idp_x509_cert = Column(Text, nullable=False)
    
    # SP Configuration
    sp_entity_id = Column(String(500), nullable=False)
    sp_acs_url = Column(String(500), nullable=False)
    sp_sls_url = Column(String(500), nullable=True)
    
    # Security settings
    want_messages_signed = Column(Boolean, default=True)
    want_assertions_signed = Column(Boolean, default=True)
    want_assertions_encrypted = Column(Boolean, default=False)
    sign_metadata = Column(Boolean, default=True)
    
    # Attribute mapping
    attribute_mapping = Column(JSONB, default=dict)  # Maps SAML attrs to user fields
    
    # Role mapping
    role_mapping = Column(JSONB, default=dict)  # Maps IdP groups to tenant roles
    
    # Status
    is_active = Column(Boolean, default=True)
    is_primary = Column(Boolean, default=False)
    
    # Metadata
    metadata_xml = Column(Text, nullable=True)
    metadata_url = Column(String(500), nullable=True)
    last_metadata_update = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)


class SAMLRequest(Base):
    """Track SAML authentication requests"""
    __tablename__ = 'saml_requests'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id = Column(UUID(as_uuid=True), ForeignKey('saml_providers.id', ondelete='CASCADE'), nullable=False)
    
    request_id = Column(String(255), nullable=False, unique=True)
    relay_state = Column(String(500), nullable=True)
    
    # Request status
    status = Column(String(50), default='pending')  # pending, success, failed
    
    # Response data
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    saml_name_id = Column(String(255), nullable=True)
    saml_session_index = Column(String(255), nullable=True)
    
    # Error info
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


# Pydantic Schemas

class SAMLProviderCreateRequest(BaseModel):
    """Create SAML provider request"""
    name: str
    provider_type: str = 'generic'
    idp_entity_id: str
    idp_sso_url: HttpUrl
    idp_slo_url: Optional[HttpUrl] = None
    idp_x509_cert: str
    attribute_mapping: Dict[str, str] = Field(default_factory=dict)
    role_mapping: Dict[str, str] = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Okta SSO",
                "provider_type": "okta",
                "idp_entity_id": "https://dev-123.okta.com",
                "idp_sso_url": "https://dev-123.okta.com/app/cerebrum/sso/saml",
                "idp_x509_cert": "-----BEGIN CERTIFICATE-----\n...",
                "attribute_mapping": {
                    "email": "user.email",
                    "first_name": "user.firstName",
                    "last_name": "user.lastName",
                    "groups": "groups"
                },
                "role_mapping": {
                    "Admins": "admin",
                    "Users": "member"
                }
            }
        }


class SAMLProviderResponse(BaseModel):
    """SAML provider response"""
    id: str
    name: str
    provider_type: str
    idp_entity_id: str
    sp_entity_id: str
    sp_acs_url: str
    is_active: bool
    is_primary: bool


class SAMLLoginRequest(BaseModel):
    """SAML login request"""
    provider_id: str
    relay_state: Optional[str] = None


class SAMLAttributeMapping(BaseModel):
    """Standard SAML attribute mapping"""
    email: str = "user.email"
    first_name: str = "user.firstName"
    last_name: str = "user.lastName"
    groups: str = "groups"


# Service Classes

class SAMLService:
    """Service for SAML 2.0 authentication"""
    
    DEFAULT_ATTRIBUTE_MAPPING = {
        'email': 'user.email',
        'first_name': 'user.firstName',
        'last_name': 'user.lastName',
        'groups': 'groups'
    }
    
    def __init__(self, db: Session, base_url: str = "https://app.cerebrum.ai"):
        self.db = db
        self.base_url = base_url.rstrip('/')
    
    def get_provider(self, provider_id: str) -> Optional[SAMLProvider]:
        """Get SAML provider by ID"""
        return self.db.query(SAMLProvider).filter(
            SAMLProvider.id == provider_id,
            SAMLProvider.is_active == True
        ).first()
    
    def get_provider_for_tenant(self, tenant_id: str) -> Optional[SAMLProvider]:
        """Get primary SAML provider for tenant"""
        return self.db.query(SAMLProvider).filter(
            SAMLProvider.tenant_id == tenant_id,
            SAMLProvider.is_active == True,
            SAMLProvider.is_primary == True
        ).first()
    
    async def create_provider(
        self,
        tenant_id: str,
        request: SAMLProviderCreateRequest,
        created_by: Optional[str] = None
    ) -> SAMLProvider:
        """Create new SAML provider"""
        
        # Generate SP URLs
        sp_entity_id = f"{self.base_url}/saml/{tenant_id}"
        sp_acs_url = f"{self.base_url}/api/v1/saml/acs/{tenant_id}"
        sp_sls_url = f"{self.base_url}/api/v1/saml/sls/{tenant_id}"
        
        provider = SAMLProvider(
            tenant_id=tenant_id,
            name=request.name,
            provider_type=request.provider_type,
            idp_entity_id=request.idp_entity_id,
            idp_sso_url=str(request.idp_sso_url),
            idp_slo_url=str(request.idp_slo_url) if request.idp_slo_url else None,
            idp_x509_cert=request.idp_x509_cert,
            sp_entity_id=sp_entity_id,
            sp_acs_url=sp_acs_url,
            sp_sls_url=sp_sls_url,
            attribute_mapping={**self.DEFAULT_ATTRIBUTE_MAPPING, **request.attribute_mapping},
            role_mapping=request.role_mapping,
            created_by=created_by
        )
        
        self.db.add(provider)
        self.db.commit()
        self.db.refresh(provider)
        
        return provider
    
    def _build_saml_settings(self, provider: SAMLProvider) -> Dict[str, Any]:
        """Build SAML settings for python3-saml"""
        
        settings = {
            'sp': {
                'entityId': provider.sp_entity_id,
                'assertionConsumerService': {
                    'url': provider.sp_acs_url,
                    'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST'
                },
                'singleLogoutService': {
                    'url': provider.sp_sls_url or provider.sp_acs_url,
                    'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect'
                },
                'NameIDFormat': 'urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress',
                'x509cert': '',  # SP certificate if signing
                'privateKey': ''  # SP private key if signing
            },
            'idp': {
                'entityId': provider.idp_entity_id,
                'singleSignOnService': {
                    'url': provider.idp_sso_url,
                    'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect'
                },
                'singleLogoutService': {
                    'url': provider.idp_slo_url or provider.idp_sso_url,
                    'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect'
                },
                'x509cert': provider.idp_x509_cert.replace('-----BEGIN CERTIFICATE-----', '').replace('-----END CERTIFICATE-----', '').replace('\n', '')
            },
            'security': {
                'nameIdEncrypted': False,
                'authnRequestsSigned': provider.want_messages_signed,
                'logoutRequestSigned': provider.want_messages_signed,
                'logoutResponseSigned': provider.want_messages_signed,
                'signMetadata': provider.sign_metadata,
                'wantAssertionsSigned': provider.want_assertions_signed,
                'wantAssertionsEncrypted': provider.want_assertions_encrypted,
                'wantNameIdEncrypted': False,
                'requestedAuthnContext': True,
                'requestedAuthnContextComparison': 'exact',
                'wantXMLValidation': True,
                'relaxDestinationValidation': False,
                'destinationStrictlyMatches': True,
                'rejectUnsolicitedResponsesWithInResponseTo': False,
                'signatureAlgorithm': 'http://www.w3.org/2001/04/xmldsig-more#rsa-sha256',
                'digestAlgorithm': 'http://www.w3.org/2001/04/xmlenc#sha256'
            }
        }
        
        return settings
    
    async def initiate_login(
        self,
        provider_id: str,
        relay_state: Optional[str] = None
    ) -> Dict[str, Any]:
        """Initiate SAML login flow"""
        
        provider = self.get_provider(provider_id)
        if not provider:
            raise HTTPException(404, "SAML provider not found")
        
        # Build SAML settings
        settings = self._build_saml_settings(provider)
        saml_settings = OneLogin_Saml2_Settings(settings)
        
        # Create auth request
        auth = OneLogin_Saml2_Auth({'https': 'on'}, saml_settings)
        
        # Generate request ID
        request_id = auth.get_last_request_id() or str(uuid.uuid4())
        
        # Store request
        saml_request = SAMLRequest(
            provider_id=provider_id,
            request_id=request_id,
            relay_state=relay_state
        )
        self.db.add(saml_request)
        self.db.commit()
        
        # Get SSO URL
        sso_url = auth.login(return_to=relay_state)
        
        return {
            'sso_url': sso_url,
            'request_id': request_id,
            'saml_request': auth.get_last_request_xml()
        }
    
    async def process_acs_response(
        self,
        provider_id: str,
        request: Request
    ) -> Dict[str, Any]:
        """Process SAML ACS response"""
        
        provider = self.get_provider(provider_id)
        if not provider:
            raise HTTPException(404, "SAML provider not found")
        
        # Get form data
        form_data = await request.form()
        saml_response = form_data.get('SAMLResponse')
        relay_state = form_data.get('RelayState')
        
        if not saml_response:
            raise HTTPException(400, "Missing SAMLResponse")
        
        # Build SAML settings
        settings = self._build_saml_settings(provider)
        
        # Prepare request data for python3-saml
        request_data = {
            'https': 'on' if request.url.scheme == 'https' else 'off',
            'http_host': request.headers.get('host'),
            'script_name': request.url.path,
            'server_port': str(request.url.port or (443 if request.url.scheme == 'https' else 80)),
            'get_data': {},
            'post_data': {
                'SAMLResponse': saml_response,
                'RelayState': relay_state or ''
            }
        }
        
        # Process response
        auth = OneLogin_Saml2_Auth(request_data, settings)
        auth.process_response()
        
        errors = auth.get_errors()
        if errors:
            raise HTTPException(400, f"SAML validation failed: {', '.join(errors)}")
        
        if not auth.is_authenticated():
            raise HTTPException(401, "SAML authentication failed")
        
        # Extract attributes
        attributes = auth.get_attributes()
        name_id = auth.get_nameid()
        session_index = auth.get_session_index()
        
        # Map attributes to user data
        user_data = self._map_attributes(provider, attributes, name_id)
        
        # Determine role from group mappings
        role = self._determine_role(provider, attributes)
        
        return {
            'authenticated': True,
            'user_data': user_data,
            'role': role,
            'session_index': session_index,
            'name_id': name_id,
            'relay_state': relay_state
        }
    
    def _map_attributes(
        self,
        provider: SAMLProvider,
        attributes: Dict[str, List[str]],
        name_id: str
    ) -> Dict[str, str]:
        """Map SAML attributes to user fields"""
        
        mapping = provider.attribute_mapping or self.DEFAULT_ATTRIBUTE_MAPPING
        
        user_data = {}
        
        # Email
        email_attr = mapping.get('email', 'user.email')
        if email_attr in attributes:
            user_data['email'] = attributes[email_attr][0]
        elif name_id and '@' in name_id:
            user_data['email'] = name_id
        
        # First name
        first_name_attr = mapping.get('first_name', 'user.firstName')
        if first_name_attr in attributes:
            user_data['first_name'] = attributes[first_name_attr][0]
        
        # Last name
        last_name_attr = mapping.get('last_name', 'user.lastName')
        if last_name_attr in attributes:
            user_data['last_name'] = attributes[last_name_attr][0]
        
        # Groups
        groups_attr = mapping.get('groups', 'groups')
        if groups_attr in attributes:
            user_data['groups'] = attributes[groups_attr]
        
        return user_data
    
    def _determine_role(
        self,
        provider: SAMLProvider,
        attributes: Dict[str, List[str]]
    ) -> str:
        """Determine user role from SAML groups"""
        
        role_mapping = provider.role_mapping or {}
        
        # Get groups from attributes
        groups_attr = provider.attribute_mapping.get('groups', 'groups')
        groups = attributes.get(groups_attr, [])
        
        # Find matching role
        for group in groups:
            if group in role_mapping:
                return role_mapping[group]
        
        return 'member'  # Default role
    
    async def generate_metadata(self, provider_id: str) -> str:
        """Generate SAML Service Provider metadata XML"""
        
        provider = self.get_provider(provider_id)
        if not provider:
            raise HTTPException(404, "SAML provider not found")
        
        settings = self._build_saml_settings(provider)
        saml_settings = OneLogin_Saml2_Settings(settings)
        
        metadata = saml_settings.get_sp_metadata()
        errors = saml_settings.validate_metadata(metadata)
        
        if errors:
            raise HTTPException(500, f"Metadata validation failed: {', '.join(errors)}")
        
        return metadata
    
    async def initiate_logout(
        self,
        provider_id: str,
        name_id: str,
        session_index: str,
        return_to: Optional[str] = None
    ) -> str:
        """Initiate SAML logout"""
        
        provider = self.get_provider(provider_id)
        if not provider:
            raise HTTPException(404, "SAML provider not found")
        
        settings = self._build_saml_settings(provider)
        
        request_data = {
            'https': 'on',
            'http_host': urlparse(provider.sp_entity_id).netloc,
            'script_name': '',
            'get_data': {},
            'post_data': {}
        }
        
        auth = OneLogin_Saml2_Auth(request_data, settings)
        logout_url = auth.logout(
            return_to=return_to,
            name_id=name_id,
            session_index=session_index
        )
        
        return logout_url
    
    async def process_slo_response(self, provider_id: str, request: Request):
        """Process single logout response"""
        
        provider = self.get_provider(provider_id)
        if not provider:
            raise HTTPException(404, "SAML provider not found")
        
        settings = self._build_saml_settings(provider)
        
        query_params = dict(request.query_params)
        
        request_data = {
            'https': 'on' if request.url.scheme == 'https' else 'off',
            'http_host': request.headers.get('host'),
            'script_name': request.url.path,
            'get_data': query_params,
            'post_data': {}
        }
        
        auth = OneLogin_Saml2_Auth(request_data, settings)
        auth.process_slo(delete_session_cb=lambda: None)
        
        errors = auth.get_errors()
        if errors:
            raise HTTPException(400, f"SLO failed: {', '.join(errors)}")
        
        return {'logout_successful': True}


# Pre-configured provider templates

class SAMLProviderTemplates:
    """Templates for common SAML providers"""
    
    @staticmethod
    def okta(tenant_id: str, okta_domain: str) -> Dict[str, Any]:
        """Okta SAML template"""
        return {
            'provider_type': 'okta',
            'idp_entity_id': f'http://www.okta.com/{okta_domain}',
            'idp_sso_url': f'https://{okta_domain}.okta.com/app/cerebrum/sso/saml',
            'idp_slo_url': f'https://{okta_domain}.okta.com/app/cerebrum/slo/saml',
            'attribute_mapping': {
                'email': 'user.email',
                'first_name': 'user.firstName',
                'last_name': 'user.lastName',
                'groups': 'groups'
            }
        }
    
    @staticmethod
    def azure_ad(tenant_id: str, azure_tenant_id: str) -> Dict[str, Any]:
        """Azure AD SAML template"""
        return {
            'provider_type': 'azure_ad',
            'idp_entity_id': f'https://sts.windows.net/{azure_tenant_id}/',
            'idp_sso_url': f'https://login.microsoftonline.com/{azure_tenant_id}/saml2',
            'idp_slo_url': f'https://login.microsoftonline.com/{azure_tenant_id}/saml2',
            'attribute_mapping': {
                'email': 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress',
                'first_name': 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname',
                'last_name': 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname',
                'groups': 'http://schemas.microsoft.com/ws/2008/06/identity/claims/groups'
            }
        }
    
    @staticmethod
    def google_workspace(tenant_id: str, domain: str) -> Dict[str, Any]:
        """Google Workspace SAML template"""
        return {
            'provider_type': 'google',
            'idp_entity_id': f'https://accounts.google.com/o/saml2?idpid={domain}',
            'idp_sso_url': 'https://accounts.google.com/o/saml2/idp',
            'attribute_mapping': {
                'email': 'email',
                'first_name': 'firstName',
                'last_name': 'lastName'
            }
        }


# Export
__all__ = [
    'SAMLProvider',
    'SAMLRequest',
    'SAMLProviderCreateRequest',
    'SAMLProviderResponse',
    'SAMLLoginRequest',
    'SAMLAttributeMapping',
    'SAMLService',
    'SAMLProviderTemplates'
]
