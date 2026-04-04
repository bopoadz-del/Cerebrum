"""
Oracle Aconex Stub

Stub implementation for Oracle Aconex collaboration platform.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from .base import BaseStub, StubResponse


class AconexStub(BaseStub):
    """
    Stub for Oracle Aconex API.
    
    Provides mock data for:
    - Mail
    - Documents
    - Workflows
    - Forms
    """
    
    service_name = "aconex"
    version = "1.0.0-stub"
    
    _mail_items = [
        {
            "id": "M001",
            "subject": "Site Inspection Request",
            "from": "inspector@example.com",
            "status": "unread",
            "sent_date": datetime.utcnow().isoformat(),
        },
        {
            "id": "M002",
            "subject": "Change Order Approval",
            "from": "pm@example.com",
            "status": "read",
            "sent_date": datetime.utcnow().isoformat(),
        },
    ]
    
    _documents = [
        {"id": "D001", "name": "Floor Plan A.pdf", "type": "PDF", "size": 2048},
        {"id": "D002", "name": "Structural Calc.xlsx", "type": "XLSX", "size": 512},
    ]
    
    def get_info(self) -> Dict[str, Any]:
        """Return stub information."""
        return {
            "service": self.service_name,
            "version": self.version,
            "mode": "stub",
            "endpoints": ["mail", "documents", "workflows", "forms"],
        }
    
    def get_mail(self, status: Optional[str] = None) -> StubResponse:
        """Get mock mail items."""
        self._log_call("get_mail", status=status)
        mail = self._mail_items
        if status:
            mail = [m for m in mail if m["status"] == status]
        return self._success_response(
            data=mail,
            message=f"Retrieved {len(mail)} mail items (stub)",
        )
    
    def send_mail(self, to: List[str], subject: str, body: str, **kwargs) -> StubResponse:
        """Mock send mail."""
        self._log_call("send_mail", to=to, subject=subject)
        return self._success_response(
            data={
                "id": "M999",
                "to": to,
                "subject": subject,
                "sent": True,
                "stub": True,
            },
            message="Mail sent (stub - no actual delivery)",
        )
    
    def get_documents(self, folder: Optional[str] = None) -> StubResponse:
        """Get mock documents."""
        self._log_call("get_documents", folder=folder)
        return self._success_response(
            data=self._documents,
            message=f"Retrieved {len(self._documents)} documents (stub)",
        )
    
    def upload_document(self, name: str, content_type: str, **kwargs) -> StubResponse:
        """Mock document upload."""
        self._log_call("upload_document", name=name, content_type=content_type)
        new_doc = {
            "id": "D999",
            "name": name,
            "type": content_type,
            "uploaded": True,
            "stub": True,
        }
        return self._success_response(
            data=new_doc,
            message="Document uploaded (stub - not stored)",
        )
    
    def register_document(self, document_id: str, **kwargs) -> StubResponse:
        """Mock document registration."""
        self._log_call("register_document", document_id=document_id)
        return self._success_response(
            data={"document_id": document_id, "registered": True, "revision": "A"},
            message="Document registered (stub)",
        )
