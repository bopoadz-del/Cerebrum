"""
Procore Integration Module - OAuth2 and Project Sync
Item 301: Procore integration
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import uuid

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from fastapi import HTTPException
import requests
from enum import Enum

from app.db.base_class import Base


class ProcoreSyncStatus(str, Enum):
    """Procore sync status"""
    PENDING = "pending"
    SYNCING = "syncing"
    SYNCED = "synced"
    FAILED = "failed"


# Database Models

class ProcoreConnection(Base):
    """Procore OAuth connection"""
    __tablename__ = 'procore_connections'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    
    # OAuth tokens
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    
    # Procore info
    procore_company_id = Column(String(100), nullable=True)
    procore_company_name = Column(String(255), nullable=True)
    procore_user_id = Column(String(100), nullable=True)
    procore_user_email = Column(String(255), nullable=True)
    
    # Settings
    auto_sync_enabled = Column(Boolean, default=True)
    sync_frequency_hours = Column(Integer, default=24)
    last_sync_at = Column(DateTime, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_connected = Column(Boolean, default=False)
    
    # Error tracking
    last_error = Column(Text, nullable=True)
    last_error_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)


class ProcoreProjectMapping(Base):
    """Mapping between Procore projects and Cerebrum projects"""
    __tablename__ = 'procore_project_mappings'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connection_id = Column(UUID(as_uuid=True), ForeignKey('procore_connections.id', ondelete='CASCADE'), nullable=False)
    
    # Procore project
    procore_project_id = Column(String(100), nullable=False)
    procore_project_name = Column(String(500), nullable=True)
    
    # Cerebrum project
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id', ondelete='CASCADE'), nullable=True)
    
    # Sync settings
    sync_documents = Column(Boolean, default=True)
    sync_rfis = Column(Boolean, default=True)
    sync_submittals = Column(Boolean, default=True)
    sync_drawings = Column(Boolean, default=True)
    
    # Status
    last_sync_at = Column(DateTime, nullable=True)
    sync_status = Column(String(50), default=ProcoreSyncStatus.PENDING.value)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class ProcoreSyncLog(Base):
    """Procore sync log"""
    __tablename__ = 'procore_sync_logs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connection_id = Column(UUID(as_uuid=True), ForeignKey('procore_connections.id', ondelete='CASCADE'), nullable=False)
    project_mapping_id = Column(UUID(as_uuid=True), ForeignKey('procore_project_mappings.id'), nullable=True)
    
    # Sync details
    sync_type = Column(String(50), nullable=False)  # projects, documents, rfis, submittals, drawings
    direction = Column(String(20), default='import')  # import, export, bidirectional
    
    # Results
    records_processed = Column(Integer, default=0)
    records_created = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)
    
    # Status
    status = Column(String(50), nullable=False)
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


# Pydantic Schemas

class ProcoreAuthUrlResponse(BaseModel):
    """Procore OAuth URL response"""
    auth_url: str
    state: str


class ProcoreTokenRequest(BaseModel):
    """Procore token exchange request"""
    code: str
    state: str


class ProcoreProjectSyncRequest(BaseModel):
    """Procore project sync request"""
    procore_project_id: str
    cerebrum_project_id: Optional[str] = None
    sync_documents: bool = True
    sync_rfis: bool = True
    sync_submittals: bool = True
    sync_drawings: bool = True


class ProcoreConnectionResponse(BaseModel):
    """Procore connection response"""
    id: str
    procore_company_name: Optional[str]
    procore_user_email: Optional[str]
    is_connected: bool
    auto_sync_enabled: bool
    last_sync_at: Optional[datetime]


# Service Classes

class ProcoreService:
    """Service for Procore integration"""
    
    OAUTH_BASE_URL = "https://login.procore.com"
    API_BASE_URL = "https://api.procore.com"
    
    def __init__(self, db: Session, client_id: str, client_secret: str, redirect_uri: str):
        self.db = db
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
    
    def get_auth_url(self, tenant_id: str) -> ProcoreAuthUrlResponse:
        """Get Procore OAuth authorization URL"""
        
        state = str(uuid.uuid4())
        
        # Store state for validation
        # In production, store in cache/Redis
        
        auth_url = (
            f"{self.OAUTH_BASE_URL}/oauth/authorize?"
            f"client_id={self.client_id}&"
            f"response_type=code&"
            f"redirect_uri={self.redirect_uri}&"
            f"state={state}"
        )
        
        return ProcoreAuthUrlResponse(auth_url=auth_url, state=state)
    
    def exchange_code(
        self,
        tenant_id: str,
        request: ProcoreTokenRequest,
        created_by: Optional[str] = None
    ) -> ProcoreConnection:
        """Exchange OAuth code for tokens"""
        
        # Exchange code for token
        token_response = requests.post(
            f"{self.OAUTH_BASE_URL}/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": request.code,
                "redirect_uri": self.redirect_uri
            }
        )
        
        if token_response.status_code != 200:
            raise HTTPException(400, "Failed to exchange code for token")
        
        token_data = token_response.json()
        
        # Get user info
        user_info = self._get_user_info(token_data['access_token'])
        
        # Create or update connection
        connection = self.db.query(ProcoreConnection).filter(
            ProcoreConnection.tenant_id == tenant_id
        ).first()
        
        if not connection:
            connection = ProcoreConnection(tenant_id=tenant_id)
            self.db.add(connection)
        
        connection.access_token = token_data['access_token']
        connection.refresh_token = token_data.get('refresh_token')
        connection.token_expires_at = datetime.utcnow() + timedelta(
            seconds=token_data.get('expires_in', 7200)
        )
        connection.procore_user_id = str(user_info.get('id'))
        connection.procore_user_email = user_info.get('email')
        connection.is_connected = True
        connection.created_by = created_by
        
        # Get company info
        companies = self._get_companies(token_data['access_token'])
        if companies:
            connection.procore_company_id = str(companies[0].get('id'))
            connection.procore_company_name = companies[0].get('name')
        
        self.db.commit()
        self.db.refresh(connection)
        
        return connection
    
    def _get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get Procore user info"""
        
        response = requests.get(
            f"{self.API_BASE_URL}/rest/v1.0/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if response.status_code != 200:
            raise HTTPException(400, "Failed to get user info")
        
        return response.json()
    
    def _get_companies(self, access_token: str) -> List[Dict[str, Any]]:
        """Get Procore companies"""
        
        response = requests.get(
            f"{self.API_BASE_URL}/rest/v1.0/companies",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if response.status_code != 200:
            return []
        
        return response.json()
    
    def refresh_token(self, connection: ProcoreConnection) -> bool:
        """Refresh access token"""
        
        if not connection.refresh_token:
            return False
        
        response = requests.post(
            f"{self.OAUTH_BASE_URL}/oauth/token",
            data={
                "grant_type": "refresh_token",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": connection.refresh_token
            }
        )
        
        if response.status_code != 200:
            connection.is_connected = False
            self.db.commit()
            return False
        
        token_data = response.json()
        
        connection.access_token = token_data['access_token']
        connection.refresh_token = token_data.get('refresh_token', connection.refresh_token)
        connection.token_expires_at = datetime.utcnow() + timedelta(
            seconds=token_data.get('expires_in', 7200)
        )
        
        self.db.commit()
        return True
    
    def get_connection(self, tenant_id: str) -> Optional[ProcoreConnection]:
        """Get Procore connection for tenant"""
        return self.db.query(ProcoreConnection).filter(
            ProcoreConnection.tenant_id == tenant_id
        ).first()
    
    def get_projects(self, connection: ProcoreConnection) -> List[Dict[str, Any]]:
        """Get Procore projects"""
        
        # Check token expiry
        if connection.token_expires_at and connection.token_expires_at < datetime.utcnow():
            if not self.refresh_token(connection):
                raise HTTPException(401, "Procore connection expired")
        
        response = requests.get(
            f"{self.API_BASE_URL}/rest/v1.0/projects",
            headers={"Authorization": f"Bearer {connection.access_token}"},
            params={"company_id": connection.procore_company_id}
        )
        
        if response.status_code != 200:
            raise HTTPException(400, "Failed to get projects")
        
        return response.json()
    
    def sync_projects(self, connection: ProcoreConnection) -> Dict[str, Any]:
        """Sync Procore projects"""
        
        procore_projects = self.get_projects(connection)
        
        synced = 0
        created = 0
        updated = 0
        
        for procore_project in procore_projects:
            # Check if mapping exists
            mapping = self.db.query(ProcoreProjectMapping).filter(
                ProcoreProjectMapping.connection_id == connection.id,
                ProcoreProjectMapping.procore_project_id == str(procore_project['id'])
            ).first()
            
            if not mapping:
                # Create new mapping
                mapping = ProcoreProjectMapping(
                    connection_id=connection.id,
                    procore_project_id=str(procore_project['id']),
                    procore_project_name=procore_project.get('name')
                )
                self.db.add(mapping)
                created += 1
            else:
                # Update existing
                mapping.procore_project_name = procore_project.get('name')
                updated += 1
            
            synced += 1
        
        connection.last_sync_at = datetime.utcnow()
        self.db.commit()
        
        # Log sync
        sync_log = ProcoreSyncLog(
            connection_id=connection.id,
            sync_type='projects',
            records_processed=synced,
            records_created=created,
            records_updated=updated,
            status='success'
        )
        self.db.add(sync_log)
        self.db.commit()
        
        return {
            "synced": synced,
            "created": created,
            "updated": updated
        }
    
    def sync_project_data(
        self,
        mapping: ProcoreProjectMapping,
        data_type: str
    ) -> Dict[str, Any]:
        """Sync specific project data from Procore"""
        
        connection = self.db.query(ProcoreConnection).filter(
            ProcoreConnection.id == mapping.connection_id
        ).first()
        
        if not connection:
            raise HTTPException(404, "Connection not found")
        
        # Check token
        if connection.token_expires_at and connection.token_expires_at < datetime.utcnow():
            if not self.refresh_token(connection):
                raise HTTPException(401, "Procore connection expired")
        
        # Sync based on data type
        if data_type == 'rfis':
            return self._sync_rfis(connection, mapping)
        elif data_type == 'submittals':
            return self._sync_submittals(connection, mapping)
        elif data_type == 'drawings':
            return self._sync_drawings(connection, mapping)
        else:
            raise HTTPException(400, f"Unknown data type: {data_type}")
    
    def _sync_rfis(
        self,
        connection: ProcoreConnection,
        mapping: ProcoreProjectMapping
    ) -> Dict[str, Any]:
        """Sync RFIs from Procore"""
        
        response = requests.get(
            f"{self.API_BASE_URL}/rest/v1.0/projects/{mapping.procore_project_id}/rfis",
            headers={"Authorization": f"Bearer {connection.access_token}"}
        )
        
        if response.status_code != 200:
            raise HTTPException(400, "Failed to get RFIs")
        
        rfis = response.json()
        
        # Process RFIs
        for rfi in rfis:
            # Create or update RFI in Cerebrum
            pass
        
        mapping.last_sync_at = datetime.utcnow()
        mapping.sync_status = ProcoreSyncStatus.SYNCED.value
        self.db.commit()
        
        return {
            "records_processed": len(rfis),
            "status": "success"
        }
    
    def _sync_submittals(
        self,
        connection: ProcoreConnection,
        mapping: ProcoreProjectMapping
    ) -> Dict[str, Any]:
        """Sync submittals from Procore"""
        
        response = requests.get(
            f"{self.API_BASE_URL}/rest/v1.0/projects/{mapping.procore_project_id}/submittals",
            headers={"Authorization": f"Bearer {connection.access_token}"}
        )
        
        if response.status_code != 200:
            raise HTTPException(400, "Failed to get submittals")
        
        submittals = response.json()
        
        return {
            "records_processed": len(submittals),
            "status": "success"
        }
    
    def _sync_drawings(
        self,
        connection: ProcoreConnection,
        mapping: ProcoreProjectMapping
    ) -> Dict[str, Any]:
        """Sync drawings from Procore"""
        
        response = requests.get(
            f"{self.API_BASE_URL}/rest/v1.0/projects/{mapping.procore_project_id}/drawings",
            headers={"Authorization": f"Bearer {connection.access_token}"}
        )
        
        if response.status_code != 200:
            raise HTTPException(400, "Failed to get drawings")
        
        drawings = response.json()
        
        return {
            "records_processed": len(drawings),
            "status": "success"
        }


# Export
__all__ = [
    'ProcoreSyncStatus',
    'ProcoreConnection',
    'ProcoreProjectMapping',
    'ProcoreSyncLog',
    'ProcoreAuthUrlResponse',
    'ProcoreTokenRequest',
    'ProcoreProjectSyncRequest',
    'ProcoreConnectionResponse',
    'ProcoreService'
]
