"""
E-Signature Integration Module - DocuSign, HelloSign, Adobe Sign
Item 312: E-signature integrations
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import uuid

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from fastapi import HTTPException
from enum import Enum
import requests
import base64

from app.db.base_class import Base


class ESignatureProvider(str, Enum):
    """E-signature providers"""
    DOCUSIGN = "docusign"
    HELLOSIGN = "hellosign"
    ADOBE_SIGN = "adobe_sign"
    PANDADOC = "pandadoc"


class EnvelopeStatus(str, Enum):
    """Envelope/document status"""
    CREATED = "created"
    SENT = "sent"
    DELIVERED = "delivered"
    COMPLETED = "completed"
    DECLINED = "declined"
    VOIDED = "voided"


# Database Models

class ESignatureConnection(Base):
    """E-signature provider connection"""
    __tablename__ = 'esignature_connections'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    
    # Provider
    provider = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    
    # OAuth tokens
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    
    # Account info
    account_id = Column(String(100), nullable=True)
    account_name = Column(String(255), nullable=True)
    base_url = Column(String(500), nullable=True)
    
    # Settings
    default_template_id = Column(String(100), nullable=True)
    default_redirect_url = Column(String(500), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_connected = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)


class SignatureEnvelope(Base):
    """Signature envelope/document"""
    __tablename__ = 'signature_envelopes'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connection_id = Column(UUID(as_uuid=True), ForeignKey('esignature_connections.id', ondelete='CASCADE'), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id', ondelete='CASCADE'), nullable=True)
    
    # Document info
    document_name = Column(String(500), nullable=False)
    document_type = Column(String(100), nullable=True)  # contract, change_order, invoice, etc.
    
    # External IDs
    envelope_id = Column(String(255), nullable=True)
    template_id = Column(String(255), nullable=True)
    
    # Status
    status = Column(String(50), default=EnvelopeStatus.CREATED.value)
    
    # Signers
    signers = Column(JSONB, default=list)
    
    # Document URLs
    document_url = Column(String(500), nullable=True)
    signed_document_url = Column(String(500), nullable=True)
    
    # Timestamps
    sent_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    
    # Metadata
    metadata = Column(JSONB, default=dict)
    
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SignatureEventLog(Base):
    """Signature event log"""
    __tablename__ = 'signature_event_logs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    envelope_id = Column(UUID(as_uuid=True), ForeignKey('signature_envelopes.id', ondelete='CASCADE'), nullable=False)
    
    # Event details
    event_type = Column(String(100), nullable=False)
    event_data = Column(JSONB, default=dict)
    
    # Signer info
    signer_email = Column(String(255), nullable=True)
    signer_name = Column(String(255), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


# Pydantic Schemas

class CreateEnvelopeRequest(BaseModel):
    """Create signature envelope request"""
    document_name: str
    document_type: str
    document_url: str
    signers: List[Dict[str, Any]]
    template_id: Optional[str] = None
    expires_days: int = 30
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SignerInfo(BaseModel):
    """Signer information"""
    name: str
    email: str
    role: str = "signer"
    order: int = 1


class EnvelopeResponse(BaseModel):
    """Envelope response"""
    id: str
    document_name: str
    status: str
    envelope_id: Optional[str]
    sent_at: Optional[datetime]
    completed_at: Optional[datetime]


# Service Classes

class DocuSignService:
    """DocuSign integration service"""
    
    OAUTH_BASE_URL = "https://account-d.docusign.com"  # Demo environment
    API_BASE_URL = "https://demo.docusign.net/restapi"
    
    def __init__(self, db: Session, integration_key: str, client_secret: str, redirect_uri: str):
        self.db = db
        self.integration_key = integration_key
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
    
    def get_auth_url(self, connection_id: str) -> str:
        """Get DocuSign OAuth URL"""
        
        scopes = [
            "signature",
            "impersonation",
            "extended"
        ]
        
        return (
            f"{self.OAUTH_BASE_URL}/oauth/auth?"
            f"response_type=code&"
            f"scope={'%20'.join(scopes)}&"
            f"client_id={self.integration_key}&"
            f"redirect_uri={self.redirect_uri}&"
            f"state={connection_id}"
        )
    
    def handle_auth_callback(
        self,
        code: str,
        state: str
    ) -> ESignatureConnection:
        """Handle DocuSign OAuth callback"""
        
        connection = self.db.query(ESignatureConnection).filter(
            ESignatureConnection.id == state
        ).first()
        
        if not connection:
            raise HTTPException(404, "Connection not found")
        
        # Exchange code for token
        auth_string = base64.b64encode(
            f"{self.integration_key}:{self.client_secret}".encode()
        ).decode()
        
        response = requests.post(
            f"{self.OAUTH_BASE_URL}/oauth/token",
            headers={
                "Authorization": f"Basic {auth_string}",
                "Content-Type": "application/x-www-form-urlencoded"
            },
            data={
                "grant_type": "authorization_code",
                "code": code
            }
        )
        
        if response.status_code != 200:
            raise HTTPException(400, "Failed to exchange code")
        
        token_data = response.json()
        
        connection.access_token = token_data['access_token']
        connection.refresh_token = token_data.get('refresh_token')
        connection.token_expires_at = datetime.utcnow() + timedelta(
            seconds=token_data.get('expires_in', 3600)
        )
        connection.is_connected = True
        
        # Get user info
        user_info = self._get_user_info(connection)
        connection.account_id = user_info.get('accounts', [{}])[0].get('account_id')
        connection.base_url = user_info.get('accounts', [{}])[0].get('base_uri')
        
        self.db.commit()
        self.db.refresh(connection)
        
        return connection
    
    def _get_user_info(self, connection: ESignatureConnection) -> Dict[str, Any]:
        """Get DocuSign user info"""
        
        response = requests.get(
            f"{self.OAUTH_BASE_URL}/oauth/userinfo",
            headers={"Authorization": f"Bearer {connection.access_token}"}
        )
        
        if response.status_code != 200:
            raise HTTPException(400, "Failed to get user info")
        
        return response.json()
    
    def _get_headers(self, connection: ESignatureConnection) -> Dict[str, str]:
        """Get API headers"""
        
        return {
            "Authorization": f"Bearer {connection.access_token}",
            "Content-Type": "application/json"
        }
    
    def create_envelope(
        self,
        connection: ESignatureConnection,
        request: CreateEnvelopeRequest
    ) -> SignatureEnvelope:
        """Create signature envelope"""
        
        # Build signers
        signers = []
        for signer in request.signers:
            signers.append({
                "email": signer['email'],
                "name": signer['name'],
                "recipientId": str(len(signers) + 1),
                "routingOrder": signer.get('order', 1)
            })
        
        # Build envelope definition
        envelope_definition = {
            "emailSubject": f"Please sign: {request.document_name}",
            "documents": [
                {
                    "documentBase64": self._download_and_encode(request.document_url),
                    "name": request.document_name,
                    "fileExtension": "pdf",
                    "documentId": "1"
                }
            ],
            "recipients": {
                "signers": signers
            },
            "status": "sent"
        }
        
        # Create envelope
        response = requests.post(
            f"{connection.base_url}/restapi/v2.1/accounts/{connection.account_id}/envelopes",
            headers=self._get_headers(connection),
            json=envelope_definition
        )
        
        if response.status_code != 201:
            raise HTTPException(400, f"Failed to create envelope: {response.text}")
        
        envelope_data = response.json()
        
        # Create envelope record
        envelope = SignatureEnvelope(
            connection_id=connection.id,
            document_name=request.document_name,
            document_type=request.document_type,
            envelope_id=envelope_data['envelopeId'],
            signers=request.signers,
            document_url=request.document_url,
            status=EnvelopeStatus.SENT.value,
            sent_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=request.expires_days),
            metadata=request.metadata
        )
        
        self.db.add(envelope)
        self.db.commit()
        self.db.refresh(envelope)
        
        return envelope
    
    def _download_and_encode(self, document_url: str) -> str:
        """Download document and return base64 encoded"""
        
        # In production, download from S3 or storage
        # For now, return placeholder
        return ""
    
    def get_envelope_status(
        self,
        connection: ESignatureConnection,
        envelope_id: str
    ) -> Dict[str, Any]:
        """Get envelope status"""
        
        response = requests.get(
            f"{connection.base_url}/restapi/v2.1/accounts/{connection.account_id}/envelopes/{envelope_id}",
            headers=self._get_headers(connection)
        )
        
        if response.status_code != 200:
            raise HTTPException(400, "Failed to get envelope status")
        
        return response.json()
    
    def void_envelope(
        self,
        connection: ESignatureConnection,
        envelope_id: str,
        reason: str
    ):
        """Void an envelope"""
        
        response = requests.put(
            f"{connection.base_url}/restapi/v2.1/accounts/{connection.account_id}/envelopes/{envelope_id}",
            headers=self._get_headers(connection),
            json={
                "status": "voided",
                "voidedReason": reason
            }
        )
        
        if response.status_code != 200:
            raise HTTPException(400, "Failed to void envelope")
        
        # Update local record
        envelope = self.db.query(SignatureEnvelope).filter(
            SignatureEnvelope.envelope_id == envelope_id
        ).first()
        
        if envelope:
            envelope.status = EnvelopeStatus.VOIDED.value
            self.db.commit()
    
    def handle_webhook(self, connection_id: str, event_data: Dict[str, Any]):
        """Handle DocuSign webhook event"""
        
        for event in event_data.get('eventNotifications', []):
            envelope_summary = event.get('envelopeSummary', {})
            envelope_id = envelope_summary.get('envelopeId')
            status = envelope_summary.get('status')
            
            # Find envelope
            envelope = self.db.query(SignatureEnvelope).filter(
                SignatureEnvelope.envelope_id == envelope_id
            ).first()
            
            if envelope:
                # Update status
                envelope.status = status
                
                if status == 'completed':
                    envelope.completed_at = datetime.utcnow()
                
                self.db.commit()
                
                # Log event
                event_log = SignatureEventLog(
                    envelope_id=envelope.id,
                    event_type=status,
                    event_data=event
                )
                self.db.add(event_log)
                self.db.commit()


# Export
__all__ = [
    'ESignatureProvider',
    'EnvelopeStatus',
    'ESignatureConnection',
    'SignatureEnvelope',
    'SignatureEventLog',
    'CreateEnvelopeRequest',
    'SignerInfo',
    'EnvelopeResponse',
    'DocuSignService'
]
