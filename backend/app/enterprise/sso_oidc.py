"""
SSO OIDC Integration Module - OpenID Connect with authlib
Item 285: OIDC SSO with authlib
"""

from typing import Optional, Dict, Any, List, Callable
from datetime import datetime, timedelta
import uuid
import secrets
import hashlib
import base64

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Session
from pydantic import BaseModel, HttpUrl, Field
from fastapi import HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
from authlib.oidc.core import UserInfo
import jwt
from jose import jwk, jwt as jose_jwt
from jose.utils import base64url_decode
import requests


# Database Models

class OIDCProvider(Base):
    """OIDC Identity Provider configuration"""
    __tablename__ = 'oidc_providers'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    
    # Provider info
    name = Column(String(255), nullable=False)
    provider_type = Column(String(50), default='generic')  # google, microsoft, okta, auth0, generic
    
    # OIDC Configuration
    issuer_url = Column(String(500), nullable=False)
    authorization_endpoint = Column(String(500), nullable=True)
    token_endpoint = Column(String(500), nullable=True)
    userinfo_endpoint = Column(String(500), nullable=True)
    jwks_uri = Column(String(500), nullable=True)
    end_session_endpoint = Column(String(500), nullable=True)
    
    # Client credentials
    client_id = Column(String(255), nullable=False)
    client_secret = Column(String(255), nullable=False)
    
    # Scopes and claims
    scopes = Column(JSONB, default=lambda: ['openid', 'email', 'profile'])
    claims_mapping = Column(JSONB, default=dict)
    
    # PKCE settings
    use_pkce = Column(Boolean, default=True)
    pkce_method = Column(String(10), default='S256')
    
    # Role mapping
    role_mapping = Column(JSONB, default=dict)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_primary = Column(Boolean, default=False)
    
    # Metadata
    discovery_document = Column(JSONB, nullable=True)
    last_discovery_update = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class OIDCAuthSession(Base):
    """Track OIDC authentication sessions"""
    __tablename__ = 'oidc_auth_sessions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id = Column(UUID(as_uuid=True), ForeignKey('oidc_providers.id', ondelete='CASCADE'), nullable=False)
    
    # OAuth2/OIDC parameters
    state = Column(String(255), nullable=False, unique=True)
    nonce = Column(String(255), nullable=True)
    code_verifier = Column(String(255), nullable=True)
    
    # Request context
    redirect_uri = Column(String(500), nullable=False)
    requested_scopes = Column(JSONB, default=list)
    relay_state = Column(String(500), nullable=True)
    
    # Session status
    status = Column(String(50), default='pending')  # pending, code_received, tokens_received, completed, failed
    
    # Token data
    authorization_code = Column(String(500), nullable=True)
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    id_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    
    # User info
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    user_info = Column(JSONB, nullable=True)
    
    # Error info
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(minutes=10))
    completed_at = Column(DateTime, nullable=True)


# Pydantic Schemas

class OIDCProviderCreateRequest(BaseModel):
    """Create OIDC provider request"""
    name: str
    provider_type: str = 'generic'
    issuer_url: HttpUrl
    client_id: str
    client_secret: str
    scopes: List[str] = Field(default_factory=lambda: ['openid', 'email', 'profile'])
    claims_mapping: Dict[str, str] = Field(default_factory=dict)
    role_mapping: Dict[str, str] = Field(default_factory=dict)
    use_pkce: bool = True
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Google Workspace",
                "provider_type": "google",
                "issuer_url": "https://accounts.google.com",
                "client_id": "your-client-id.apps.googleusercontent.com",
                "client_secret": "your-client-secret",
                "scopes": ["openid", "email", "profile"],
                "claims_mapping": {
                    "email": "email",
                    "first_name": "given_name",
                    "last_name": "family_name"
                },
                "role_mapping": {
                    "admin@company.com": "admin"
                }
            }
        }


class OIDCProviderResponse(BaseModel):
    """OIDC provider response"""
    id: str
    name: str
    provider_type: str
    issuer_url: str
    scopes: List[str]
    is_active: bool
    is_primary: bool


class OIDCTokenResponse(BaseModel):
    """OIDC token response"""
    access_token: str
    token_type: str = 'Bearer'
    expires_in: int
    refresh_token: Optional[str] = None
    id_token: str
    scope: str


# Service Classes

class OIDCService:
    """Service for OIDC authentication"""
    
    DEFAULT_CLAIMS_MAPPING = {
        'email': 'email',
        'first_name': 'given_name',
        'last_name': 'family_name',
        'picture': 'picture',
        'groups': 'groups'
    }
    
    PROVIDER_DISCOVERY_URLS = {
        'google': 'https://accounts.google.com/.well-known/openid-configuration',
        'microsoft': 'https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration',
        'okta': '{issuer}/.well-known/openid-configuration',
        'auth0': '{issuer}/.well-known/openid-configuration'
    }
    
    def __init__(self, db: Session, base_url: str = "https://app.cerebrum.ai"):
        self.db = db
        self.base_url = base_url.rstrip('/')
        self.oauth = OAuth()
    
    def get_provider(self, provider_id: str) -> Optional[OIDCProvider]:
        """Get OIDC provider by ID"""
        return self.db.query(OIDCProvider).filter(
            OIDCProvider.id == provider_id,
            OIDCProvider.is_active == True
        ).first()
    
    def get_provider_for_tenant(self, tenant_id: str) -> Optional[OIDCProvider]:
        """Get primary OIDC provider for tenant"""
        return self.db.query(OIDCProvider).filter(
            OIDCProvider.tenant_id == tenant_id,
            OIDCProvider.is_active == True,
            OIDCProvider.is_primary == True
        ).first()
    
    async def discover_configuration(self, issuer_url: str) -> Dict[str, Any]:
        """Discover OIDC configuration from issuer"""
        
        discovery_url = f"{issuer_url.rstrip('/')}/.well-known/openid-configuration"
        
        try:
            response = requests.get(discovery_url, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise HTTPException(400, f"Failed to discover OIDC configuration: {str(e)}")
    
    async def create_provider(
        self,
        tenant_id: str,
        request: OIDCProviderCreateRequest
    ) -> OIDCProvider:
        """Create new OIDC provider"""
        
        issuer_url = str(request.issuer_url).rstrip('/')
        
        # Discover configuration
        discovery = await self.discover_configuration(issuer_url)
        
        provider = OIDCProvider(
            tenant_id=tenant_id,
            name=request.name,
            provider_type=request.provider_type,
            issuer_url=issuer_url,
            authorization_endpoint=discovery.get('authorization_endpoint'),
            token_endpoint=discovery.get('token_endpoint'),
            userinfo_endpoint=discovery.get('userinfo_endpoint'),
            jwks_uri=discovery.get('jwks_uri'),
            end_session_endpoint=discovery.get('end_session_endpoint'),
            client_id=request.client_id,
            client_secret=request.client_secret,
            scopes=request.scopes,
            claims_mapping={**self.DEFAULT_CLAIMS_MAPPING, **request.claims_mapping},
            role_mapping=request.role_mapping,
            use_pkce=request.use_pkce,
            discovery_document=discovery,
            last_discovery_update=datetime.utcnow()
        )
        
        self.db.add(provider)
        self.db.commit()
        self.db.refresh(provider)
        
        # Register with OAuth client
        self._register_oauth_client(provider)
        
        return provider
    
    def _register_oauth_client(self, provider: OIDCProvider):
        """Register provider with authlib OAuth client"""
        
        redirect_uri = f"{self.base_url}/api/v1/oidc/callback/{provider.id}"
        
        client_kwargs = {
            'scope': ' '.join(provider.scopes),
            'token_endpoint_auth_method': 'client_secret_basic'
        }
        
        if provider.use_pkce:
            client_kwargs['code_challenge_method'] = provider.pkce_method
        
        self.oauth.register(
            name=f"oidc_{provider.id}",
            client_id=provider.client_id,
            client_secret=provider.client_secret,
            server_metadata_url=f"{provider.issuer_url}/.well-known/openid-configuration",
            client_kwargs=client_kwargs
        )
    
    def _generate_pkce_challenge(self) -> tuple:
        """Generate PKCE code verifier and challenge"""
        
        code_verifier = base64.urlsafe_b64encode(
            secrets.token_bytes(32)
        ).decode('utf-8').rstrip('=')
        
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode('utf-8').rstrip('=')
        
        return code_verifier, code_challenge
    
    async def initiate_login(
        self,
        provider_id: str,
        redirect_uri: str,
        relay_state: Optional[str] = None,
        additional_scopes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Initiate OIDC login flow"""
        
        provider = self.get_provider(provider_id)
        if not provider:
            raise HTTPException(404, "OIDC provider not found")
        
        # Generate state and nonce
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        
        # PKCE
        code_verifier = None
        code_challenge = None
        if provider.use_pkce:
            code_verifier, code_challenge = self._generate_pkce_challenge()
        
        # Create session
        scopes = provider.scopes.copy()
        if additional_scopes:
            scopes.extend(additional_scopes)
        
        session = OIDCAuthSession(
            provider_id=provider_id,
            state=state,
            nonce=nonce,
            code_verifier=code_verifier,
            redirect_uri=redirect_uri,
            requested_scopes=scopes,
            relay_state=relay_state
        )
        
        self.db.add(session)
        self.db.commit()
        
        # Build authorization URL
        auth_url = provider.authorization_endpoint
        params = {
            'client_id': provider.client_id,
            'response_type': 'code',
            'scope': ' '.join(scopes),
            'redirect_uri': redirect_uri,
            'state': state,
            'nonce': nonce
        }
        
        if code_challenge:
            params['code_challenge'] = code_challenge
            params['code_challenge_method'] = provider.pkce_method
        
        # Build query string
        from urllib.parse import urlencode
        auth_url = f"{auth_url}?{urlencode(params)}"
        
        return {
            'authorization_url': auth_url,
            'state': state,
            'session_id': str(session.id)
        }
    
    async def process_callback(
        self,
        provider_id: str,
        request: Request
    ) -> Dict[str, Any]:
        """Process OIDC callback"""
        
        provider = self.get_provider(provider_id)
        if not provider:
            raise HTTPException(404, "OIDC provider not found")
        
        # Get query parameters
        code = request.query_params.get('code')
        state = request.query_params.get('state')
        error = request.query_params.get('error')
        error_description = request.query_params.get('error_description')
        
        if error:
            raise HTTPException(400, f"OIDC error: {error} - {error_description}")
        
        if not code or not state:
            raise HTTPException(400, "Missing authorization code or state")
        
        # Find session
        session = self.db.query(OIDCAuthSession).filter(
            OIDCAuthSession.provider_id == provider_id,
            OIDCAuthSession.state == state,
            OIDCAuthSession.status == 'pending',
            OIDCAuthSession.expires_at > datetime.utcnow()
        ).first()
        
        if not session:
            raise HTTPException(400, "Invalid or expired session")
        
        # Exchange code for tokens
        token_data = await self._exchange_code(
            provider,
            code,
            session.redirect_uri,
            session.code_verifier
        )
        
        # Update session
        session.authorization_code = code
        session.access_token = token_data.get('access_token')
        session.refresh_token = token_data.get('refresh_token')
        session.id_token = token_data.get('id_token')
        
        if 'expires_in' in token_data:
            session.token_expires_at = datetime.utcnow() + timedelta(
                seconds=token_data['expires_in']
            )
        
        session.status = 'tokens_received'
        
        # Validate ID token and get user info
        user_info = await self._validate_id_token(provider, session.id_token)
        
        # Get additional user info from userinfo endpoint
        if provider.userinfo_endpoint:
            additional_info = await self._get_userinfo(
                provider.userinfo_endpoint,
                session.access_token
            )
            user_info.update(additional_info)
        
        session.user_info = user_info
        session.status = 'completed'
        session.completed_at = datetime.utcnow()
        
        self.db.commit()
        
        # Map claims to user data
        user_data = self._map_claims(provider, user_info)
        
        # Determine role
        role = self._determine_role(provider, user_info)
        
        return {
            'authenticated': True,
            'user_data': user_data,
            'role': role,
            'id_token_claims': user_info,
            'relay_state': session.relay_state,
            'access_token': session.access_token,
            'refresh_token': session.refresh_token
        }
    
    async def _exchange_code(
        self,
        provider: OIDCProvider,
        code: str,
        redirect_uri: str,
        code_verifier: Optional[str]
    ) -> Dict[str, Any]:
        """Exchange authorization code for tokens"""
        
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri,
            'client_id': provider.client_id,
            'client_secret': provider.client_secret
        }
        
        if code_verifier:
            data['code_verifier'] = code_verifier
        
        try:
            response = requests.post(
                provider.token_endpoint,
                data=data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise HTTPException(400, f"Token exchange failed: {str(e)}")
    
    async def _validate_id_token(
        self,
        provider: OIDCProvider,
        id_token: str
    ) -> Dict[str, Any]:
        """Validate and decode ID token"""
        
        # Fetch JWKS
        try:
            jwks_response = requests.get(provider.jwks_uri, timeout=30)
            jwks_response.raise_for_status()
            jwks = jwks_response.json()
        except requests.RequestException as e:
            raise HTTPException(400, f"Failed to fetch JWKS: {str(e)}")
        
        # Decode without verification to get header
        header = jose_jwt.get_unverified_header(id_token)
        
        # Find matching key
        rsa_key = None
        for key in jwks['keys']:
            if key['kid'] == header['kid']:
                rsa_key = key
                break
        
        if not rsa_key:
            raise HTTPException(400, "Unable to find appropriate key")
        
        # Verify and decode
        try:
            public_key = jwk.construct(rsa_key)
            claims = jose_jwt.decode(
                id_token,
                public_key,
                algorithms=['RS256'],
                issuer=provider.issuer_url,
                audience=provider.client_id
            )
            return claims
        except Exception as e:
            raise HTTPException(400, f"ID token validation failed: {str(e)}")
    
    async def _get_userinfo(
        self,
        userinfo_endpoint: str,
        access_token: str
    ) -> Dict[str, Any]:
        """Get user info from userinfo endpoint"""
        
        try:
            response = requests.get(
                userinfo_endpoint,
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            # Don't fail if userinfo fails
            return {}
    
    def _map_claims(
        self,
        provider: OIDCProvider,
        claims: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Map OIDC claims to user data"""
        
        mapping = provider.claims_mapping or self.DEFAULT_CLAIMS_MAPPING
        
        user_data = {}
        
        for key, claim_name in mapping.items():
            if claim_name in claims:
                user_data[key] = claims[claim_name]
        
        return user_data
    
    def _determine_role(
        self,
        provider: OIDCProvider,
        claims: Dict[str, Any]
    ) -> str:
        """Determine user role from claims"""
        
        role_mapping = provider.role_mapping or {}
        
        # Check email-based mapping
        email = claims.get('email', '')
        if email in role_mapping:
            return role_mapping[email]
        
        # Check domain-based mapping
        domain = email.split('@')[1] if '@' in email else ''
        if domain in role_mapping:
            return role_mapping[domain]
        
        # Check groups claim
        groups = claims.get('groups', [])
        for group in groups:
            if group in role_mapping:
                return role_mapping[group]
        
        return 'member'
    
    async def refresh_tokens(
        self,
        provider_id: str,
        refresh_token: str
    ) -> Dict[str, Any]:
        """Refresh access token"""
        
        provider = self.get_provider(provider_id)
        if not provider:
            raise HTTPException(404, "OIDC provider not found")
        
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': provider.client_id,
            'client_secret': provider.client_secret
        }
        
        try:
            response = requests.post(
                provider.token_endpoint,
                data=data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise HTTPException(400, f"Token refresh failed: {str(e)}")
    
    async def logout(
        self,
        provider_id: str,
        id_token: str,
        post_logout_redirect_uri: Optional[str] = None
    ) -> Optional[str]:
        """Initiate OIDC logout"""
        
        provider = self.get_provider(provider_id)
        if not provider or not provider.end_session_endpoint:
            return None
        
        params = {'id_token_hint': id_token}
        
        if post_logout_redirect_uri:
            params['post_logout_redirect_uri'] = post_logout_redirect_uri
        
        from urllib.parse import urlencode
        logout_url = f"{provider.end_session_endpoint}?{urlencode(params)}"
        
        return logout_url


# Pre-configured OIDC providers

class OIDCProviderPresets:
    """Presets for common OIDC providers"""
    
    @staticmethod
    def google(client_id: str, client_secret: str) -> Dict[str, Any]:
        """Google OIDC preset"""
        return {
            'name': 'Google',
            'provider_type': 'google',
            'issuer_url': 'https://accounts.google.com',
            'client_id': client_id,
            'client_secret': client_secret,
            'scopes': ['openid', 'email', 'profile'],
            'claims_mapping': {
                'email': 'email',
                'first_name': 'given_name',
                'last_name': 'family_name',
                'picture': 'picture'
            }
        }
    
    @staticmethod
    def microsoft(
        client_id: str,
        client_secret: str,
        tenant_id: str = 'common'
    ) -> Dict[str, Any]:
        """Microsoft/Azure AD OIDC preset"""
        return {
            'name': 'Microsoft',
            'provider_type': 'microsoft',
            'issuer_url': f'https://login.microsoftonline.com/{tenant_id}/v2.0',
            'client_id': client_id,
            'client_secret': client_secret,
            'scopes': ['openid', 'email', 'profile', 'User.Read'],
            'claims_mapping': {
                'email': 'email',
                'first_name': 'given_name',
                'last_name': 'family_name'
            }
        }
    
    @staticmethod
    def okta(
        client_id: str,
        client_secret: str,
        okta_domain: str
    ) -> Dict[str, Any]:
        """Okta OIDC preset"""
        return {
            'name': 'Okta',
            'provider_type': 'okta',
            'issuer_url': f'https://{okta_domain}.okta.com',
            'client_id': client_id,
            'client_secret': client_secret,
            'scopes': ['openid', 'email', 'profile', 'groups'],
            'claims_mapping': {
                'email': 'email',
                'first_name': 'given_name',
                'last_name': 'family_name',
                'groups': 'groups'
            }
        }


# Export
__all__ = [
    'OIDCProvider',
    'OIDCAuthSession',
    'OIDCProviderCreateRequest',
    'OIDCProviderResponse',
    'OIDCTokenResponse',
    'OIDCService',
    'OIDCProviderPresets'
]
