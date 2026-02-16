"""
ERP Integration Module - Sage, Viewpoint, QuickBooks, SAP
Item 307: ERP integrations
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from fastapi import HTTPException
from enum import Enum
import requests


class ERPType(str, Enum):
    """ERP system types"""
    SAGE = "sage"
    VIEWPOINT = "viewpoint"
    QUICKBOOKS = "quickbooks"
    SAP = "sap"
    NETSUITE = "netsuite"
    DYNAMICS = "dynamics"


class SyncDirection(str, Enum):
    """Sync direction"""
    IMPORT = "import"
    EXPORT = "export"
    BIDIRECTIONAL = "bidirectional"


# Database Models

class ERPConnection(Base):
    """ERP system connection"""
    __tablename__ = 'erp_connections'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    
    # ERP type
    erp_type = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    
    # Connection details
    base_url = Column(String(500), nullable=True)
    api_key = Column(Text, nullable=True)
    api_secret = Column(Text, nullable=True)
    auth_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    
    # Company/Realm info
    company_id = Column(String(100), nullable=True)
    realm_id = Column(String(100), nullable=True)  # QuickBooks specific
    
    # Sync settings
    sync_enabled = Column(Boolean, default=True)
    sync_frequency_hours = Column(Integer, default=24)
    last_sync_at = Column(DateTime, nullable=True)
    
    # Data mappings
    account_mappings = Column(JSONB, default=dict)
    cost_code_mappings = Column(JSONB, default=dict)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_connected = Column(Boolean, default=False)
    
    # Error tracking
    last_error = Column(Text, nullable=True)
    last_error_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)


class ERPSyncLog(Base):
    """ERP sync log"""
    __tablename__ = 'erp_sync_logs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connection_id = Column(UUID(as_uuid=True), ForeignKey('erp_connections.id', ondelete='CASCADE'), nullable=False)
    
    # Sync details
    sync_type = Column(String(50), nullable=False)  # accounts, vendors, cost_codes, transactions
    direction = Column(String(20), default='import')
    
    # Results
    records_processed = Column(Integer, default=0)
    records_created = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)
    
    # Financial
    total_amount = Column(Numeric(15, 2), nullable=True)
    
    # Status
    status = Column(String(50), nullable=False)
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class ERPAccountMapping(Base):
    """Chart of accounts mapping"""
    __tablename__ = 'erp_account_mappings'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connection_id = Column(UUID(as_uuid=True), ForeignKey('erp_connections.id', ondelete='CASCADE'), nullable=False)
    
    # ERP account
    erp_account_id = Column(String(100), nullable=False)
    erp_account_number = Column(String(100), nullable=True)
    erp_account_name = Column(String(500), nullable=True)
    
    # Cerebrum mapping
    cerebrum_category = Column(String(100), nullable=True)
    cerebrum_cost_type = Column(String(100), nullable=True)
    
    # Account type
    account_type = Column(String(100), nullable=True)  # asset, liability, equity, revenue, expense
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# Pydantic Schemas

class CreateERPConnectionRequest(BaseModel):
    """Create ERP connection request"""
    erp_type: ERPType
    name: str
    base_url: Optional[str] = None
    company_id: Optional[str] = None
    realm_id: Optional[str] = None
    sync_frequency_hours: int = 24


class ERPAuthCallback(BaseModel):
    """ERP OAuth callback"""
    code: str
    realm_id: Optional[str] = None  # QuickBooks
    state: Optional[str] = None


class SyncRequest(BaseModel):
    """Sync request"""
    sync_type: str
    direction: SyncDirection = SyncDirection.IMPORT
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class ERPConnectionResponse(BaseModel):
    """ERP connection response"""
    id: str
    erp_type: str
    name: str
    is_connected: bool
    sync_enabled: bool
    last_sync_at: Optional[datetime]


# Service Classes

class ERPService:
    """Base ERP service"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_connection(
        self,
        tenant_id: str,
        request: CreateERPConnectionRequest,
        created_by: Optional[str] = None
    ) -> ERPConnection:
        """Create ERP connection"""
        
        connection = ERPConnection(
            tenant_id=tenant_id,
            erp_type=request.erp_type.value,
            name=request.name,
            base_url=request.base_url,
            company_id=request.company_id,
            realm_id=request.realm_id,
            sync_frequency_hours=request.sync_frequency_hours,
            created_by=created_by
        )
        
        self.db.add(connection)
        self.db.commit()
        self.db.refresh(connection)
        
        return connection
    
    def get_connection(self, connection_id: str) -> Optional[ERPConnection]:
        """Get ERP connection"""
        return self.db.query(ERPConnection).filter(
            ERPConnection.id == connection_id
        ).first()


class QuickBooksService(ERPService):
    """QuickBooks Online integration"""
    
    OAUTH_BASE_URL = "https://appcenter.intuit.com/connect/oauth2"
    API_BASE_URL = "https://quickbooks.api.intuit.com"
    
    def __init__(self, db: Session, client_id: str, client_secret: str, redirect_uri: str):
        super().__init__(db)
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
    
    def get_auth_url(self, connection_id: str) -> str:
        """Get QuickBooks OAuth URL"""
        
        from urllib.parse import urlencode
        
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "com.intuit.quickbooks.accounting",
            "state": connection_id
        }
        
        return f"{self.OAUTH_BASE_URL}?{urlencode(params)}"
    
    def handle_auth_callback(
        self,
        callback: ERPAuthCallback
    ) -> ERPConnection:
        """Handle QuickBooks OAuth callback"""
        
        connection = self.get_connection(callback.state)
        if not connection:
            raise HTTPException(404, "Connection not found")
        
        # Exchange code for token
        import base64
        
        auth_string = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()
        
        response = requests.post(
            "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer",
            headers={
                "Authorization": f"Basic {auth_string}",
                "Content-Type": "application/x-www-form-urlencoded"
            },
            data={
                "grant_type": "authorization_code",
                "code": callback.code,
                "redirect_uri": self.redirect_uri
            }
        )
        
        if response.status_code != 200:
            raise HTTPException(400, "Failed to exchange code")
        
        token_data = response.json()
        
        connection.auth_token = token_data['access_token']
        connection.refresh_token = token_data.get('refresh_token')
        connection.token_expires_at = datetime.utcnow() + timedelta(
            seconds=token_data.get('expires_in', 3600)
        )
        connection.realm_id = callback.realm_id
        connection.is_connected = True
        
        self.db.commit()
        self.db.refresh(connection)
        
        return connection
    
    def _get_headers(self, connection: ERPConnection) -> Dict[str, str]:
        """Get API headers"""
        
        # Refresh token if needed
        if connection.token_expires_at and connection.token_expires_at < datetime.utcnow():
            self._refresh_token(connection)
        
        return {
            "Authorization": f"Bearer {connection.auth_token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    
    def _refresh_token(self, connection: ERPConnection):
        """Refresh access token"""
        
        import base64
        
        auth_string = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()
        
        response = requests.post(
            "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer",
            headers={
                "Authorization": f"Basic {auth_string}",
                "Content-Type": "application/x-www-form-urlencoded"
            },
            data={
                "grant_type": "refresh_token",
                "refresh_token": connection.refresh_token
            }
        )
        
        if response.status_code == 200:
            token_data = response.json()
            connection.auth_token = token_data['access_token']
            connection.refresh_token = token_data.get('refresh_token', connection.refresh_token)
            connection.token_expires_at = datetime.utcnow() + timedelta(
                seconds=token_data.get('expires_in', 3600)
            )
            self.db.commit()
    
    def get_accounts(self, connection: ERPConnection) -> List[Dict[str, Any]]:
        """Get chart of accounts"""
        
        response = requests.get(
            f"{self.API_BASE_URL}/v3/company/{connection.realm_id}/query",
            headers=self._get_headers(connection),
            params={"query": "SELECT * FROM Account"}
        )
        
        if response.status_code != 200:
            raise HTTPException(400, "Failed to get accounts")
        
        data = response.json()
        return data.get('QueryResponse', {}).get('Account', [])
    
    def get_vendors(self, connection: ERPConnection) -> List[Dict[str, Any]]:
        """Get vendors"""
        
        response = requests.get(
            f"{self.API_BASE_URL}/v3/company/{connection.realm_id}/query",
            headers=self._get_headers(connection),
            params={"query": "SELECT * FROM Vendor"}
        )
        
        if response.status_code != 200:
            raise HTTPException(400, "Failed to get vendors")
        
        data = response.json()
        return data.get('QueryResponse', {}).get('Vendor', [])
    
    def create_bill(
        self,
        connection: ERPConnection,
        vendor_id: str,
        line_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create a bill in QuickBooks"""
        
        bill_data = {
            "VendorRef": {"value": vendor_id},
            "Line": line_items
        }
        
        response = requests.post(
            f"{self.API_BASE_URL}/v3/company/{connection.realm_id}/bill",
            headers=self._get_headers(connection),
            json=bill_data
        )
        
        if response.status_code != 200:
            raise HTTPException(400, "Failed to create bill")
        
        return response.json()
    
    def sync_accounts(self, connection: ERPConnection) -> Dict[str, Any]:
        """Sync chart of accounts"""
        
        accounts = self.get_accounts(connection)
        
        created = 0
        updated = 0
        
        for account in accounts:
            # Check if mapping exists
            mapping = self.db.query(ERPAccountMapping).filter(
                ERPAccountMapping.connection_id == connection.id,
                ERPAccountMapping.erp_account_id == account['Id']
            ).first()
            
            if not mapping:
                mapping = ERPAccountMapping(
                    connection_id=connection.id,
                    erp_account_id=account['Id'],
                    erp_account_number=account.get('AcctNum'),
                    erp_account_name=account.get('Name'),
                    account_type=account.get('AccountType', '').lower()
                )
                self.db.add(mapping)
                created += 1
            else:
                mapping.erp_account_number = account.get('AcctNum')
                mapping.erp_account_name = account.get('Name')
                updated += 1
        
        connection.last_sync_at = datetime.utcnow()
        self.db.commit()
        
        # Log sync
        sync_log = ERPSyncLog(
            connection_id=connection.id,
            sync_type='accounts',
            records_processed=len(accounts),
            records_created=created,
            records_updated=updated,
            status='success'
        )
        self.db.add(sync_log)
        self.db.commit()
        
        return {
            "processed": len(accounts),
            "created": created,
            "updated": updated
        }


# Export
__all__ = [
    'ERPType',
    'SyncDirection',
    'ERPConnection',
    'ERPSyncLog',
    'ERPAccountMapping',
    'CreateERPConnectionRequest',
    'ERPAuthCallback',
    'SyncRequest',
    'ERPConnectionResponse',
    'ERPService',
    'QuickBooksService'
]
