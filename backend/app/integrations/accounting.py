"""
Accounting Integration Module
Handles QuickBooks, Xero, and Sage integration.
"""
import requests
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB

from app.database import Base


class AccountingConnection(Base):
    """Accounting system connection record."""
    __tablename__ = 'accounting_connections'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    
    provider = Column(String(50), nullable=False)  # quickbooks, xero, sage
    realm_id = Column(String(255))  # Company ID in QuickBooks
    
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

class QuickBooksInvoiceCreateRequest(BaseModel):
    customer_id: str
    line_items: List[Dict[str, Any]]
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    memo: Optional[str] = None
    doc_number: Optional[str] = None


class QuickBooksBillCreateRequest(BaseModel):
    vendor_id: str
    line_items: List[Dict[str, Any]]
    bill_date: Optional[str] = None
    due_date: Optional[str] = None
    memo: Optional[str] = None


class XeroInvoiceCreateRequest(BaseModel):
    contact_id: str
    line_items: List[Dict[str, Any]]
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    reference: Optional[str] = None


class ChartOfAccount(BaseModel):
    id: str
    name: str
    account_type: str
    account_sub_type: Optional[str] = None
    active: bool = True


class QuickBooksService:
    """Service for QuickBooks Online integration."""
    
    SANDBOX_BASE_URL = "https://sandbox-quickbooks.api.intuit.com"
    PRODUCTION_BASE_URL = "https://quickbooks.api.intuit.com"
    
    def __init__(self, db_session, client_id: str, client_secret: str, sandbox: bool = False):
        self.db = db_session
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = self.SANDBOX_BASE_URL if sandbox else self.PRODUCTION_BASE_URL
    
    def _get_headers(self, access_token: str) -> Dict[str, str]:
        """Get authorization headers."""
        return {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    
    def _refresh_token(self, connection: AccountingConnection) -> str:
        """Refresh QuickBooks access token."""
        url = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
        
        auth = (self.client_id, self.client_secret)
        data = {
            "grant_type": "refresh_token",
            "refresh_token": connection.refresh_token
        }
        
        response = requests.post(url, auth=auth, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        
        connection.access_token = token_data["access_token"]
        connection.refresh_token = token_data.get("refresh_token", connection.refresh_token)
        connection.token_expires_at = datetime.utcnow().timestamp() + token_data["expires_in"]
        
        self.db.commit()
        
        return connection.access_token
    
    def _make_request(
        self,
        connection: AccountingConnection,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to QuickBooks API."""
        # Check token expiration
        if datetime.utcnow().timestamp() >= connection.token_expires_at:
            access_token = self._refresh_token(connection)
        else:
            access_token = connection.access_token
        
        url = f"{self.base_url}/v3/company/{connection.realm_id}{endpoint}"
        headers = self._get_headers(access_token)
        
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=data)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        response.raise_for_status()
        return response.json()
    
    def create_invoice(
        self,
        connection: AccountingConnection,
        request: QuickBooksInvoiceCreateRequest
    ) -> Dict[str, Any]:
        """Create an invoice in QuickBooks."""
        data = {
            "CustomerRef": {"value": request.customer_id},
            "Line": request.line_items
        }
        
        if request.invoice_date:
            data["TxnDate"] = request.invoice_date
        if request.due_date:
            data["DueDate"] = request.due_date
        if request.memo:
            data["CustomerMemo"] = {"value": request.memo}
        if request.doc_number:
            data["DocNumber"] = request.doc_number
        
        return self._make_request(connection, "POST", "/invoice", data)
    
    def create_bill(
        self,
        connection: AccountingConnection,
        request: QuickBooksBillCreateRequest
    ) -> Dict[str, Any]:
        """Create a bill in QuickBooks."""
        data = {
            "VendorRef": {"value": request.vendor_id},
            "Line": request.line_items
        }
        
        if request.bill_date:
            data["TxnDate"] = request.bill_date
        if request.due_date:
            data["DueDate"] = request.due_date
        if request.memo:
            data["PrivateNote"] = request.memo
        
        return self._make_request(connection, "POST", "/bill", data)
    
    def get_chart_of_accounts(
        self,
        connection: AccountingConnection
    ) -> List[ChartOfAccount]:
        """Get QuickBooks chart of accounts."""
        result = self._make_request(connection, "GET", "/query?query=select * from Account")
        
        accounts = []
        for acc in result.get("QueryResponse", {}).get("Account", []):
            accounts.append(ChartOfAccount(
                id=acc.get("Id"),
                name=acc.get("Name"),
                account_type=acc.get("AccountType"),
                account_sub_type=acc.get("AccountSubType"),
                active=acc.get("Active", True)
            ))
        
        return accounts
    
    def get_customers(
        self,
        connection: AccountingConnection,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get QuickBooks customers."""
        query = "select * from Customer"
        
        if search:
            query += f" where DisplayName LIKE '%{search}%'"
        
        query += " MAXRESULTS 100"
        
        result = self._make_request(
            connection,
            "GET",
            f"/query?query={requests.utils.quote(query)}"
        )
        
        return result.get("QueryResponse", {}).get("Customer", [])
    
    def get_vendors(
        self,
        connection: AccountingConnection,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get QuickBooks vendors."""
        query = "select * from Vendor"
        
        if search:
            query += f" where DisplayName LIKE '%{search}%'"
        
        query += " MAXRESULTS 100"
        
        result = self._make_request(
            connection,
            "GET",
            f"/query?query={requests.utils.quote(query)}"
        )
        
        return result.get("QueryResponse", {}).get("Vendor", [])
    
    def sync_payment_application(
        self,
        connection: AccountingConnection,
        payment_app_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Sync payment application to QuickBooks invoice."""
        line_items = []
        
        for item in payment_app_data.get("line_items", []):
            line_items.append({
                "DetailType": "SalesItemLineDetail",
                "SalesItemLineDetail": {
                    "ItemRef": {"value": item.get("item_id")},
                    "Qty": item.get("quantity", 1),
                    "UnitPrice": item.get("unit_price", 0)
                },
                "Amount": item.get("amount", 0),
                "Description": item.get("description", "")
            })
        
        invoice_request = QuickBooksInvoiceCreateRequest(
            customer_id=payment_app_data.get("customer_id"),
            line_items=line_items,
            doc_number=payment_app_data.get("application_number"),
            memo=f"Payment Application - {payment_app_data.get('period')}"
        )
        
        return self.create_invoice(connection, invoice_request)


class XeroService:
    """Service for Xero integration."""
    
    API_BASE_URL = "https://api.xero.com/api.xro/2.0"
    
    def __init__(self, db_session, client_id: str, client_secret: str):
        self.db = db_session
        self.client_id = client_id
        self.client_secret = client_secret
    
    def _get_headers(self, access_token: str, tenant_id: str) -> Dict[str, str]:
        """Get authorization headers."""
        return {
            "Authorization": f"Bearer {access_token}",
            "Xero-tenant-id": tenant_id,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    
    def _refresh_token(self, connection: AccountingConnection) -> str:
        """Refresh Xero access token."""
        url = "https://identity.xero.com/connect/token"
        
        auth = (self.client_id, self.client_secret)
        data = {
            "grant_type": "refresh_token",
            "refresh_token": connection.refresh_token
        }
        
        response = requests.post(url, auth=auth, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        
        connection.access_token = token_data["access_token"]
        connection.refresh_token = token_data.get("refresh_token", connection.refresh_token)
        connection.token_expires_at = datetime.utcnow().timestamp() + token_data["expires_in"]
        
        self.db.commit()
        
        return connection.access_token
    
    def _make_request(
        self,
        connection: AccountingConnection,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to Xero API."""
        # Check token expiration
        if datetime.utcnow().timestamp() >= connection.token_expires_at:
            access_token = self._refresh_token(connection)
        else:
            access_token = connection.access_token
        
        url = f"{self.API_BASE_URL}{endpoint}"
        headers = self._get_headers(access_token, connection.realm_id)
        
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=data)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        response.raise_for_status()
        return response.json()
    
    def create_invoice(
        self,
        connection: AccountingConnection,
        request: XeroInvoiceCreateRequest
    ) -> Dict[str, Any]:
        """Create an invoice in Xero."""
        data = {
            "Invoices": [{
                "Type": "ACCREC",
                "Contact": {"ContactID": request.contact_id},
                "LineItems": request.line_items
            }]
        }
        
        if request.invoice_date:
            data["Invoices"][0]["Date"] = request.invoice_date
        if request.due_date:
            data["Invoices"][0]["DueDate"] = request.due_date
        if request.reference:
            data["Invoices"][0]["Reference"] = request.reference
        
        return self._make_request(connection, "POST", "/Invoices", data)
    
    def get_chart_of_accounts(
        self,
        connection: AccountingConnection
    ) -> List[ChartOfAccount]:
        """Get Xero chart of accounts."""
        result = self._make_request(connection, "GET", "/Accounts")
        
        accounts = []
        for acc in result.get("Accounts", []):
            accounts.append(ChartOfAccount(
                id=acc.get("AccountID"),
                name=acc.get("Name"),
                account_type=acc.get("Type"),
                active=acc.get("Status") == "ACTIVE"
            ))
        
        return accounts


class AccountingService:
    """Unified accounting service."""
    
    def __init__(self, db_session, quickbooks_config: Dict = None, xero_config: Dict = None):
        self.db = db_session
        self.quickbooks = QuickBooksService(db_session, **quickbooks_config) if quickbooks_config else None
        self.xero = XeroService(db_session, **xero_config) if xero_config else None
    
    def get_service(self, provider: str):
        """Get the appropriate accounting service."""
        if provider == "quickbooks":
            return self.quickbooks
        elif provider == "xero":
            return self.xero
        else:
            raise ValueError(f"Unsupported accounting provider: {provider}")
