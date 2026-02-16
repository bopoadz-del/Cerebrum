"""
CRM Integration Module
Handles Salesforce and HubSpot integration.
"""
import requests
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB

from app.database import Base


class CRMConnection(Base):
    """CRM connection record."""
    __tablename__ = 'crm_connections'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    
    crm_type = Column(String(50), nullable=False)  # salesforce, hubspot
    
    instance_url = Column(String(500))
    access_token = Column(Text)
    refresh_token = Column(Text)
    token_expires_at = Column(DateTime)
    
    is_active = Column(Boolean, default=True)
    connected_by = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    connected_at = Column(DateTime, default=datetime.utcnow)
    
    last_sync_at = Column(DateTime)
    sync_settings = Column(JSONB, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Pydantic Models

class SalesforceLeadCreateRequest(BaseModel):
    first_name: str
    last_name: str
    company: str
    email: Optional[str] = None
    phone: Optional[str] = None
    title: Optional[str] = None
    source: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = None


class SalesforceOpportunityCreateRequest(BaseModel):
    name: str
    account_id: str
    stage_name: str
    close_date: str
    amount: Optional[float] = None
    probability: Optional[int] = None
    custom_fields: Optional[Dict[str, Any]] = None


class HubSpotContactCreateRequest(BaseModel):
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    lifecycle_stage: Optional[str] = None


class HubSpotDealCreateRequest(BaseModel):
    deal_name: str
    pipeline: Optional[str] = None
    deal_stage: Optional[str] = None
    amount: Optional[float] = None
    close_date: Optional[str] = None
    associated_contact_ids: List[str] = []


class SalesforceService:
    """Service for Salesforce integration."""
    
    API_VERSION = "v58.0"
    
    def __init__(self, db_session, client_id: str, client_secret: str):
        self.db = db_session
        self.client_id = client_id
        self.client_secret = client_secret
    
    def _get_headers(self, access_token: str) -> Dict[str, str]:
        """Get authorization headers."""
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    
    def _refresh_token(self, connection: CRMConnection) -> str:
        """Refresh Salesforce access token."""
        url = "https://login.salesforce.com/services/oauth2/token"
        
        data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": connection.refresh_token
        }
        
        response = requests.post(url, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        
        connection.access_token = token_data["access_token"]
        connection.instance_url = token_data.get("instance_url", connection.instance_url)
        
        self.db.commit()
        
        return connection.access_token
    
    def _make_request(
        self,
        connection: CRMConnection,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to Salesforce API."""
        access_token = connection.access_token
        
        url = f"{connection.instance_url}/services/data/{self.API_VERSION}{endpoint}"
        headers = self._get_headers(access_token)
        
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data)
        elif method == "PATCH":
            response = requests.patch(url, headers=headers, json=data)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        if response.status_code == 401:
            # Token expired, refresh and retry
            access_token = self._refresh_token(connection)
            headers = self._get_headers(access_token)
            
            if method == "GET":
                response = requests.get(url, headers=headers)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data)
        
        response.raise_for_status()
        return response.json() if response.content else {}
    
    def create_lead(
        self,
        connection: CRMConnection,
        request: SalesforceLeadCreateRequest
    ) -> Dict[str, Any]:
        """Create a lead in Salesforce."""
        data = {
            "FirstName": request.first_name,
            "LastName": request.last_name,
            "Company": request.company
        }
        
        if request.email:
            data["Email"] = request.email
        if request.phone:
            data["Phone"] = request.phone
        if request.title:
            data["Title"] = request.title
        if request.source:
            data["LeadSource"] = request.source
        if request.custom_fields:
            data.update(request.custom_fields)
        
        return self._make_request(connection, "POST", "/sobjects/Lead", data)
    
    def create_opportunity(
        self,
        connection: CRMConnection,
        request: SalesforceOpportunityCreateRequest
    ) -> Dict[str, Any]:
        """Create an opportunity in Salesforce."""
        data = {
            "Name": request.name,
            "AccountId": request.account_id,
            "StageName": request.stage_name,
            "CloseDate": request.close_date
        }
        
        if request.amount:
            data["Amount"] = request.amount
        if request.probability:
            data["Probability"] = request.probability
        if request.custom_fields:
            data.update(request.custom_fields)
        
        return self._make_request(connection, "POST", "/sobjects/Opportunity", data)
    
    def get_accounts(
        self,
        connection: CRMConnection,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get Salesforce accounts."""
        query = "SELECT Id, Name, Industry, Phone, Website FROM Account"
        
        if search:
            query += f" WHERE Name LIKE '%{search}%'"
        
        query += " LIMIT 100"
        
        result = self._make_request(connection, "GET", f"/query?q={requests.utils.quote(query)}")
        return result.get("records", [])
    
    def sync_project_to_opportunity(
        self,
        connection: CRMConnection,
        project_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Sync project data to Salesforce opportunity."""
        # Check if opportunity exists
        project_id = project_data.get("id")
        query = f"SELECT Id FROM Opportunity WHERE Project_ID__c = '{project_id}'"
        url = f"/query?q={requests.utils.quote(query)}"
        existing = self._make_request(connection, "GET", url)
        
        opp_data = {
            "Name": project_data.get("name"),
            "StageName": project_data.get("status", "Prospecting"),
            "Amount": project_data.get("contract_value"),
            "Project_ID__c": project_id,
            "Description": project_data.get("description")
        }
        
        if existing.get("records"):
            # Update existing
            opp_id = existing["records"][0]["Id"]
            return self._make_request(connection, "PATCH", f"/sobjects/Opportunity/{opp_id}", opp_data)
        else:
            # Create new
            opp_data["CloseDate"] = project_data.get("estimated_completion", datetime.utcnow().strftime("%Y-%m-%d"))
            return self._make_request(connection, "POST", "/sobjects/Opportunity", opp_data)


class HubSpotService:
    """Service for HubSpot integration."""
    
    API_BASE_URL = "https://api.hubapi.com"
    
    def __init__(self, db_session):
        self.db = db_session
    
    def _get_headers(self, access_token: str) -> Dict[str, str]:
        """Get authorization headers."""
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    
    def _make_request(
        self,
        connection: CRMConnection,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to HubSpot API."""
        url = f"{self.API_BASE_URL}{endpoint}"
        headers = self._get_headers(connection.access_token)
        
        if method == "GET":
            response = requests.get(url, headers=headers, params=params)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data)
        elif method == "PATCH":
            response = requests.patch(url, headers=headers, json=data)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        response.raise_for_status()
        return response.json() if response.content else {}
    
    def create_contact(
        self,
        connection: CRMConnection,
        request: HubSpotContactCreateRequest
    ) -> Dict[str, Any]:
        """Create a contact in HubSpot."""
        data = {
            "properties": [
                {"property": "email", "value": request.email}
            ]
        }
        
        if request.first_name:
            data["properties"].append({"property": "firstname", "value": request.first_name})
        if request.last_name:
            data["properties"].append({"property": "lastname", "value": request.last_name})
        if request.phone:
            data["properties"].append({"property": "phone", "value": request.phone})
        if request.company:
            data["properties"].append({"property": "company", "value": request.company})
        if request.lifecycle_stage:
            data["properties"].append({"property": "lifecyclestage", "value": request.lifecycle_stage})
        
        return self._make_request(connection, "POST", "/contacts/v1/contact", data)
    
    def create_deal(
        self,
        connection: CRMConnection,
        request: HubSpotDealCreateRequest
    ) -> Dict[str, Any]:
        """Create a deal in HubSpot."""
        data = {
            "properties": [
                {"name": "dealname", "value": request.deal_name}
            ],
            "associations": {
                "associatedVids": request.associated_contact_ids
            }
        }
        
        if request.pipeline:
            data["properties"].append({"name": "pipeline", "value": request.pipeline})
        if request.deal_stage:
            data["properties"].append({"name": "dealstage", "value": request.deal_stage})
        if request.amount:
            data["properties"].append({"name": "amount", "value": request.amount})
        if request.close_date:
            data["properties"].append({"name": "closedate", "value": request.close_date})
        
        return self._make_request(connection, "POST", "/deals/v1/deal", data)
    
    def get_pipelines(
        self,
        connection: CRMConnection
    ) -> List[Dict[str, Any]]:
        """Get HubSpot deal pipelines."""
        result = self._make_request(connection, "GET", "/crm-pipelines/v1/pipelines/deals")
        return result.get("results", [])
    
    def sync_project_to_deal(
        self,
        connection: CRMConnection,
        project_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Sync project data to HubSpot deal."""
        deal_data = {
            "deal_name": project_data.get("name"),
            "amount": project_data.get("contract_value"),
            "pipeline": "default",
            "deal_stage": project_data.get("status", "appointmentscheduled"),
            "close_date": project_data.get("estimated_completion")
        }
        
        request = HubSpotDealCreateRequest(**deal_data)
        return self.create_deal(connection, request)


class CRMService:
    """Unified CRM service."""
    
    def __init__(self, db_session, salesforce_config: Dict = None, hubspot_config: Dict = None):
        self.db = db_session
        self.salesforce = SalesforceService(db_session, **salesforce_config) if salesforce_config else None
        self.hubspot = HubSpotService(db_session)
    
    def get_service(self, crm_type: str):
        """Get the appropriate CRM service."""
        if crm_type == "salesforce":
            return self.salesforce
        elif crm_type == "hubspot":
            return self.hubspot
        else:
            raise ValueError(f"Unsupported CRM type: {crm_type}")
