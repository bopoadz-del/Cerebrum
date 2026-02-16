"""
SCIM 2.0 Directory Sync Module - System for Cross-domain Identity Management
Item 286: SCIM 2.0 directory synchronization
"""

from typing import Optional, Dict, Any, List, Union
from datetime import datetime
import uuid
from app.db.base_class import Base
import re

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, validator
from fastapi import HTTPException, Request, Response, Depends
from fastapi.responses import JSONResponse
import hashlib
import secrets


# Database Models

class SCIMProvider(Base):
    """SCIM provider configuration"""
    __tablename__ = 'scim_providers'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    
    # Provider info
    name = Column(String(255), nullable=False)
    provider_type = Column(String(50), default='generic')  # azure_ad, okta, onelogin, generic
    
    # Authentication
    auth_type = Column(String(50), default='bearer_token')  # bearer_token, oauth
    bearer_token = Column(String(255), nullable=True)
    oauth_client_id = Column(String(255), nullable=True)
    oauth_client_secret = Column(String(255), nullable=True)
    
    # SCIM endpoint
    scim_base_url = Column(String(500), nullable=False)
    
    # Sync settings
    sync_interval_minutes = Column(Integer, default=60)
    last_sync_at = Column(DateTime, nullable=True)
    last_sync_status = Column(String(50), nullable=True)
    last_sync_error = Column(Text, nullable=True)
    
    # Attribute mapping
    attribute_mapping = Column(JSONB, default=dict)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SCIMUser(Base):
    """SCIM user mapping"""
    __tablename__ = 'scim_users'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    provider_id = Column(UUID(as_uuid=True), ForeignKey('scim_providers.id', ondelete='CASCADE'), nullable=False)
    
    # SCIM identifiers
    external_id = Column(String(255), nullable=False)
    scim_id = Column(String(255), nullable=False)
    
    # User reference
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    
    # SCIM attributes
    user_name = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=False)
    
    # Status
    active = Column(Boolean, default=True)
    
    # Metadata
    raw_data = Column(JSONB, nullable=True)
    last_synced_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_scim_users_provider_external', 'provider_id', 'external_id', unique=True),
        Index('ix_scim_users_tenant_email', 'tenant_id', 'email'),
    )


class SCIMGroup(Base):
    """SCIM group mapping"""
    __tablename__ = 'scim_groups'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    provider_id = Column(UUID(as_uuid=True), ForeignKey('scim_providers.id', ondelete='CASCADE'), nullable=False)
    
    # SCIM identifiers
    external_id = Column(String(255), nullable=False)
    scim_id = Column(String(255), nullable=False)
    
    # Group reference (if mapped to tenant role)
    role_mapping = Column(String(50), nullable=True)
    
    # SCIM attributes
    display_name = Column(String(255), nullable=False)
    
    # Members (SCIM user IDs)
    members = Column(JSONB, default=list)
    
    # Status
    active = Column(Boolean, default=True)
    
    # Metadata
    raw_data = Column(JSONB, nullable=True)
    last_synced_at = Column(DateTime, default=datetime.utcnow)


class SCIMSyncLog(Base):
    """SCIM synchronization logs"""
    __tablename__ = 'scim_sync_logs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id = Column(UUID(as_uuid=True), ForeignKey('scim_providers.id', ondelete='CASCADE'), nullable=False)
    
    sync_type = Column(String(50), nullable=False)  # full, incremental, push
    status = Column(String(50), nullable=False)  # success, partial, failed
    
    # Statistics
    users_created = Column(Integer, default=0)
    users_updated = Column(Integer, default=0)
    users_deactivated = Column(Integer, default=0)
    groups_created = Column(Integer, default=0)
    groups_updated = Column(Integer, default=0)
    
    # Details
    error_message = Column(Text, nullable=True)
    details = Column(JSONB, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


# SCIM Protocol Models (RFC 7643/7644)

class SCIMName(BaseModel):
    """SCIM name complex attribute"""
    formatted: Optional[str] = None
    familyName: Optional[str] = None
    givenName: Optional[str] = None
    middleName: Optional[str] = None
    honorificPrefix: Optional[str] = None
    honorificSuffix: Optional[str] = None


class SCIMAddress(BaseModel):
    """SCIM address complex attribute"""
    formatted: Optional[str] = None
    streetAddress: Optional[str] = None
    locality: Optional[str] = None
    region: Optional[str] = None
    postalCode: Optional[str] = None
    country: Optional[str] = None
    type: Optional[str] = None
    primary: Optional[bool] = None


class SCIMEmail(BaseModel):
    """SCIM email attribute"""
    value: str
    type: Optional[str] = "work"
    primary: Optional[bool] = False


class SCIMPhoneNumber(BaseModel):
    """SCIM phone number attribute"""
    value: str
    type: Optional[str] = "work"
    primary: Optional[bool] = False


class SCIMMember(BaseModel):
    """SCIM group member"""
    value: str
    display: Optional[str] = None
    type: Optional[str] = "User"
    ref: Optional[str] = Field(None, alias='$ref')


class SCIMUserResource(BaseModel):
    """SCIM User resource"""
    schemas: List[str] = ["urn:ietf:params:scim:schemas:core:2.0:User"]
    id: Optional[str] = None
    externalId: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    userName: str
    name: Optional[SCIMName] = None
    displayName: Optional[str] = None
    nickName: Optional[str] = None
    profileUrl: Optional[str] = None
    title: Optional[str] = None
    userType: Optional[str] = None
    preferredLanguage: Optional[str] = None
    locale: Optional[str] = None
    timezone: Optional[str] = None
    active: bool = True
    emails: Optional[List[SCIMEmail]] = None
    phoneNumbers: Optional[List[SCIMPhoneNumber]] = None
    addresses: Optional[List[SCIMAddress]] = None
    groups: Optional[List[Dict[str, Any]]] = None
    
    class Config:
        populate_by_name = True


class SCIMGroupResource(BaseModel):
    """SCIM Group resource"""
    schemas: List[str] = ["urn:ietf:params:scim:schemas:core:2.0:Group"]
    id: Optional[str] = None
    externalId: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    displayName: str
    members: Optional[List[SCIMMember]] = None


class SCIMListResponse(BaseModel):
    """SCIM ListResponse"""
    schemas: List[str] = ["urn:ietf:params:scim:api:messages:2.0:ListResponse"]
    totalResults: int
    startIndex: int = 1
    itemsPerPage: int
    Resources: List[Union[SCIMUserResource, SCIMGroupResource]]


class SCIMError(BaseModel):
    """SCIM Error response"""
    schemas: List[str] = ["urn:ietf:params:scim:api:messages:2.0:Error"]
    status: str
    detail: Optional[str] = None
    scimType: Optional[str] = None


# Service Classes

class SCIMService:
    """Service for SCIM 2.0 directory synchronization"""
    
    DEFAULT_ATTRIBUTE_MAPPING = {
        'userName': 'email',
        'name.givenName': 'first_name',
        'name.familyName': 'last_name',
        'emails[0].value': 'email',
        'displayName': 'full_name'
    }
    
    def __init__(self, db: Session, base_url: str = "https://app.cerebrum.ai"):
        self.db = db
        self.base_url = base_url.rstrip('/')
    
    def get_provider(self, provider_id: str) -> Optional[SCIMProvider]:
        """Get SCIM provider by ID"""
        return self.db.query(SCIMProvider).filter(
            SCIMProvider.id == provider_id,
            SCIMProvider.is_active == True
        ).first()
    
    def create_provider(
        self,
        tenant_id: str,
        name: str,
        provider_type: str,
        scim_base_url: str,
        auth_token: Optional[str] = None,
        sync_interval: int = 60
    ) -> SCIMProvider:
        """Create new SCIM provider"""
        
        # Generate bearer token if not provided
        if not auth_token:
            auth_token = secrets.token_urlsafe(32)
        
        provider = SCIMProvider(
            tenant_id=tenant_id,
            name=name,
            provider_type=provider_type,
            scim_base_url=scim_base_url,
            bearer_token=auth_token,
            sync_interval_minutes=sync_interval,
            attribute_mapping=self.DEFAULT_ATTRIBUTE_MAPPING
        )
        
        self.db.add(provider)
        self.db.commit()
        self.db.refresh(provider)
        
        return provider
    
    # SCIM Server (Inbound) Methods
    
    def authenticate_request(
        self,
        request: Request,
        tenant_id: str
    ) -> bool:
        """Authenticate incoming SCIM request"""
        
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header.startswith('Bearer '):
            return False
        
        token = auth_header[7:]
        
        # Find provider with matching token
        provider = self.db.query(SCIMProvider).filter(
            SCIMProvider.tenant_id == tenant_id,
            SCIMProvider.bearer_token == token,
            SCIMProvider.is_active == True
        ).first()
        
        return provider is not None
    
    def list_users(
        self,
        tenant_id: str,
        filter_query: Optional[str] = None,
        start_index: int = 1,
        count: int = 100
    ) -> SCIMListResponse:
        """List users (SCIM /Users endpoint)"""
        
        query = self.db.query(SCIMUser).filter(
            SCIMUser.tenant_id == tenant_id
        )
        
        # Apply filter if provided
        if filter_query:
            query = self._apply_filter(query, filter_query)
        
        total = query.count()
        
        users = query.offset(start_index - 1).limit(count).all()
        
        resources = [self._scim_user_to_resource(u) for u in users]
        
        return SCIMListResponse(
            totalResults=total,
            startIndex=start_index,
            itemsPerPage=count,
            Resources=resources
        )
    
    def get_user(
        self,
        tenant_id: str,
        user_id: str
    ) -> Optional[SCIMUserResource]:
        """Get single user"""
        
        user = self.db.query(SCIMUser).filter(
            SCIMUser.tenant_id == tenant_id,
            SCIMUser.scim_id == user_id
        ).first()
        
        if not user:
            return None
        
        return self._scim_user_to_resource(user)
    
    def create_user(
        self,
        tenant_id: str,
        user_data: SCIMUserResource
    ) -> SCIMUserResource:
        """Create new user"""
        
        # Check if user already exists
        existing = self.db.query(SCIMUser).filter(
            SCIMUser.tenant_id == tenant_id,
            SCIMUser.user_name == user_data.userName
        ).first()
        
        if existing:
            raise HTTPException(409, "User already exists")
        
        # Generate SCIM ID
        scim_id = str(uuid.uuid4())
        
        # Extract email
        email = user_data.userName
        if user_data.emails:
            primary_email = next(
                (e for e in user_data.emails if e.primary),
                user_data.emails[0]
            )
            email = primary_email.value
        
        # Create SCIM user record
        scim_user = SCIMUser(
            tenant_id=tenant_id,
            external_id=user_data.externalId,
            scim_id=scim_id,
            user_name=user_data.userName,
            display_name=user_data.displayName,
            email=email,
            active=user_data.active,
            raw_data=user_data.model_dump()
        )
        
        self.db.add(scim_user)
        self.db.commit()
        
        # Create actual user in system
        self._create_system_user(tenant_id, scim_user, user_data)
        
        return self._scim_user_to_resource(scim_user)
    
    def update_user(
        self,
        tenant_id: str,
        user_id: str,
        user_data: SCIMUserResource
    ) -> Optional[SCIMUserResource]:
        """Update existing user"""
        
        scim_user = self.db.query(SCIMUser).filter(
            SCIMUser.tenant_id == tenant_id,
            SCIMUser.scim_id == user_id
        ).first()
        
        if not scim_user:
            return None
        
        # Update fields
        if user_data.userName:
            scim_user.user_name = user_data.userName
        if user_data.displayName:
            scim_user.display_name = user_data.displayName
        if user_data.emails:
            primary_email = next(
                (e for e in user_data.emails if e.primary),
                user_data.emails[0]
            )
            scim_user.email = primary_email.value
        
        scim_user.active = user_data.active
        scim_user.raw_data = user_data.model_dump()
        scim_user.last_synced_at = datetime.utcnow()
        
        self.db.commit()
        
        # Update system user
        self._update_system_user(scim_user, user_data)
        
        return self._scim_user_to_resource(scim_user)
    
    def delete_user(
        self,
        tenant_id: str,
        user_id: str
    ) -> bool:
        """Delete (deactivate) user"""
        
        scim_user = self.db.query(SCIMUser).filter(
            SCIMUser.tenant_id == tenant_id,
            SCIMUser.scim_id == user_id
        ).first()
        
        if not scim_user:
            return False
        
        # Deactivate rather than delete
        scim_user.active = False
        scim_user.last_synced_at = datetime.utcnow()
        
        self.db.commit()
        
        # Deactivate system user
        if scim_user.user_id:
            self._deactivate_system_user(scim_user.user_id)
        
        return True
    
    def list_groups(
        self,
        tenant_id: str,
        filter_query: Optional[str] = None,
        start_index: int = 1,
        count: int = 100
    ) -> SCIMListResponse:
        """List groups (SCIM /Groups endpoint)"""
        
        query = self.db.query(SCIMGroup).filter(
            SCIMGroup.tenant_id == tenant_id
        )
        
        if filter_query:
            query = self._apply_filter(query, filter_query)
        
        total = query.count()
        groups = query.offset(start_index - 1).limit(count).all()
        
        resources = [self._scim_group_to_resource(g) for g in groups]
        
        return SCIMListResponse(
            totalResults=total,
            startIndex=start_index,
            itemsPerPage=count,
            Resources=resources
        )
    
    def _scim_user_to_resource(self, user: SCIMUser) -> SCIMUserResource:
        """Convert SCIMUser to SCIMUserResource"""
        
        return SCIMUserResource(
            id=user.scim_id,
            externalId=user.external_id,
            userName=user.user_name,
            displayName=user.display_name,
            active=user.active,
            emails=[SCIMEmail(value=user.email, primary=True)],
            meta={
                "resourceType": "User",
                "created": user.last_synced_at.isoformat() if user.last_synced_at else None,
                "lastModified": user.last_synced_at.isoformat() if user.last_synced_at else None,
                "location": f"/scim/v2/Users/{user.scim_id}"
            }
        )
    
    def _scim_group_to_resource(self, group: SCIMGroup) -> SCIMGroupResource:
        """Convert SCIMGroup to SCIMGroupResource"""
        
        members = []
        for member_id in (group.members or []):
            members.append(SCIMMember(value=member_id))
        
        return SCIMGroupResource(
            id=group.scim_id,
            externalId=group.external_id,
            displayName=group.display_name,
            members=members,
            meta={
                "resourceType": "Group",
                "created": group.last_synced_at.isoformat() if group.last_synced_at else None,
                "lastModified": group.last_synced_at.isoformat() if group.last_synced_at else None
            }
        )
    
    def _apply_filter(self, query, filter_query: str):
        """Apply SCIM filter to query"""
        
        # Simple filter parsing (userName eq "value")
        match = re.match(r'(\w+)\s+(eq|sw|ew|co|pr|gt|ge|lt|le)\s+"([^"]+)"', filter_query)
        
        if match:
            attr, op, value = match.groups()
            
            if attr == 'userName' and op == 'eq':
                return query.filter(SCIMUser.user_name == value)
            elif attr == 'externalId' and op == 'eq':
                return query.filter(SCIMUser.external_id == value)
            elif attr == 'emails' and op == 'eq':
                return query.filter(SCIMUser.email == value)
        
        return query
    
    def _create_system_user(
        self,
        tenant_id: str,
        scim_user: SCIMUser,
        user_data: SCIMUserResource
    ):
        """Create user in the main system"""
        
        # This would create the actual User record
        # and link it to the tenant
        pass
    
    def _update_system_user(
        self,
        scim_user: SCIMUser,
        user_data: SCIMUserResource
    ):
        """Update system user"""
        
        if scim_user.user_id:
            # Update existing user
            pass
    
    def _deactivate_system_user(self, user_id: str):
        """Deactivate system user"""
        
        # Deactivate user in main system
        pass


# SCIM Client (Outbound) Methods

class SCIMClient:
    """Client for outbound SCIM synchronization"""
    
    def __init__(self, provider: SCIMProvider):
        self.provider = provider
        self.base_url = provider.scim_base_url.rstrip('/')
    
    def _get_headers(self) -> Dict[str, str]:
        """Get authentication headers"""
        
        headers = {
            'Content-Type': 'application/scim+json',
            'Accept': 'application/scim+json'
        }
        
        if self.provider.auth_type == 'bearer_token' and self.provider.bearer_token:
            headers['Authorization'] = f'Bearer {self.provider.bearer_token}'
        
        return headers
    
    def get_users(self, filter_query: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch users from SCIM provider"""
        
        import requests
        
        url = f"{self.base_url}/Users"
        params = {}
        
        if filter_query:
            params['filter'] = filter_query
        
        try:
            response = requests.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            return data.get('Resources', [])
        
        except requests.RequestException as e:
            raise HTTPException(500, f"SCIM request failed: {str(e)}")
    
    def get_groups(self) -> List[Dict[str, Any]]:
        """Fetch groups from SCIM provider"""
        
        import requests
        
        url = f"{self.base_url}/Groups"
        
        try:
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            return data.get('Resources', [])
        
        except requests.RequestException as e:
            raise HTTPException(500, f"SCIM request failed: {str(e)}")
    
    def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create user in SCIM provider"""
        
        import requests
        
        url = f"{self.base_url}/Users"
        
        try:
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=user_data,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        
        except requests.RequestException as e:
            raise HTTPException(500, f"SCIM create failed: {str(e)}")
    
    def update_user(self, user_id: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update user in SCIM provider"""
        
        import requests
        
        url = f"{self.base_url}/Users/{user_id}"
        
        try:
            response = requests.put(
                url,
                headers=self._get_headers(),
                json=user_data,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        
        except requests.RequestException as e:
            raise HTTPException(500, f"SCIM update failed: {str(e)}")
    
    def delete_user(self, user_id: str) -> bool:
        """Delete user from SCIM provider"""
        
        import requests
        
        url = f"{self.base_url}/Users/{user_id}"
        
        try:
            response = requests.delete(
                url,
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()
            return True
        
        except requests.RequestException as e:
            raise HTTPException(500, f"SCIM delete failed: {str(e)}")


# Export
__all__ = [
    'SCIMProvider',
    'SCIMUser',
    'SCIMGroup',
    'SCIMSyncLog',
    'SCIMName',
    'SCIMAddress',
    'SCIMEmail',
    'SCIMPhoneNumber',
    'SCIMMember',
    'SCIMUserResource',
    'SCIMGroupResource',
    'SCIMListResponse',
    'SCIMError',
    'SCIMService',
    'SCIMClient'
]
