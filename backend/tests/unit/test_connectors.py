"""
Tests for Connector Factory and Stubs

Tests run without external dependencies.
"""

import pytest
import os
from unittest.mock import patch

from app.connectors import get_connector, get_connector_status, list_connectors
from app.stubs import (
    ProcoreStub, AconexStub, PrimaveraStub,
    GoogleDriveStub, SlackStub, OpenAIStub
)
from app.stubs.base import StubResponse, StubError


class TestConnectorFactory:
    """Tests for connector factory."""
    
    def test_list_connectors(self):
        """Test listing available connectors."""
        connectors = list_connectors()
        assert "procore" in connectors
        assert "aconex" in connectors
        assert "google_drive" in connectors
        assert "slack" in connectors
    
    def test_get_connector_stub_procore(self):
        """Test getting Procore stub."""
        with patch.dict(os.environ, {"USE_STUB_CONNECTORS": "true"}):
            connector = get_connector("procore")
            assert isinstance(connector, ProcoreStub)
    
    def test_get_connector_stub_aconex(self):
        """Test getting Aconex stub."""
        with patch.dict(os.environ, {"USE_STUB_CONNECTORS": "true"}):
            connector = get_connector("aconex")
            assert isinstance(connector, AconexStub)
    
    def test_get_connector_stub_primavera(self):
        """Test getting Primavera stub."""
        with patch.dict(os.environ, {"USE_STUB_CONNECTORS": "true"}):
            connector = get_connector("primavera")
            assert isinstance(connector, PrimaveraStub)
            
            # Also test p6 alias
            connector_p6 = get_connector("p6")
            assert isinstance(connector_p6, PrimaveraStub)
    
    def test_get_connector_stub_google_drive(self):
        """Test getting Google Drive stub."""
        with patch.dict(os.environ, {"USE_STUB_CONNECTORS": "true"}):
            connector = get_connector("google_drive")
            assert isinstance(connector, GoogleDriveStub)
            
            # Also test drive alias
            connector_drive = get_connector("drive")
            assert isinstance(connector_drive, GoogleDriveStub)
    
    def test_get_connector_stub_slack(self):
        """Test getting Slack stub."""
        with patch.dict(os.environ, {"USE_STUB_CONNECTORS": "true"}):
            connector = get_connector("slack")
            assert isinstance(connector, SlackStub)
    
    def test_get_connector_stub_openai(self):
        """Test getting OpenAI stub."""
        with patch.dict(os.environ, {"USE_STUB_CONNECTORS": "true"}):
            connector = get_connector("openai")
            assert isinstance(connector, OpenAIStub)
    
    def test_get_connector_status(self):
        """Test getting connector status."""
        status = get_connector_status()
        assert "procore" in status
        assert "aconex" in status
        
        # Check status structure
        procore_status = status["procore"]
        assert "stub_available" in procore_status
        assert "production_available" in procore_status


class TestProcoreStub:
    """Tests for Procore stub."""
    
    @pytest.fixture
    def stub(self):
        return ProcoreStub()
    
    def test_health_check(self, stub):
        """Test health check."""
        health = stub.health_check()
        assert health["service"] == "procore"
        assert health["status"] == "stubbed"
        assert health["healthy"] is True
    
    def test_get_projects(self, stub):
        """Test getting projects."""
        response = stub.get_projects()
        assert isinstance(response, StubResponse)
        assert response.success is True
        assert len(response.data) == 3
        assert response.data[0]["name"] == "Downtown Tower"
    
    def test_get_project_found(self, stub):
        """Test getting existing project."""
        response = stub.get_project(1)
        assert response.success is True
        assert response.data["id"] == 1
    
    def test_get_project_not_found(self, stub):
        """Test getting non-existent project."""
        response = stub.get_project(999)
        assert response.success is False
        assert "not found" in response.error.lower()
    
    def test_get_rfis(self, stub):
        """Test getting RFIs."""
        response = stub.get_rfis()
        assert response.success is True
        assert len(response.data) == 2
    
    def test_get_rfis_filtered(self, stub):
        """Test getting RFIs with filter."""
        response = stub.get_rfis(project_id=1)
        assert response.success is True
        assert all(r["project_id"] == 1 for r in response.data)


class TestOpenAIStub:
    """Tests for OpenAI stub."""
    
    @pytest.fixture
    def stub(self):
        return OpenAIStub()
    
    def test_chat_completion(self, stub):
        """Test chat completion."""
        messages = [{"role": "user", "content": "Hello"}]
        response = stub.chat_completion(messages)
        assert response.success is True
        assert "choices" in response.data
        assert response.data["model"] == "gpt-4-stub"
    
    def test_chat_completion_document(self, stub):
        """Test document analysis completion."""
        messages = [{"role": "user", "content": "Analyze this document"}]
        response = stub.chat_completion(messages)
        assert response.success is True
        assert "construction project" in response.data["choices"][0]["message"]["content"]
    
    def test_create_embedding(self, stub):
        """Test embedding creation."""
        response = stub.create_embedding("test text")
        assert response.success is True
        assert len(response.data["data"][0]["embedding"]) == 1536
    
    def test_classify_document(self, stub):
        """Test document classification."""
        response = stub.classify_document(
            "This is a construction document about foundation work",
            ["construction", "finance", "legal"]
        )
        assert response.success is True
        assert response.data["classification"] == "construction"


class TestSlackStub:
    """Tests for Slack stub."""
    
    @pytest.fixture
    def stub(self):
        return SlackStub()
    
    def test_send_message(self, stub):
        """Test sending message."""
        response = stub.send_message("general", "Hello team")
        assert response.success is True
        assert response.data["channel"] == "general"
        assert response.data["stub"] is True
    
    def test_post_webhook(self, stub):
        """Test webhook posting."""
        response = stub.post_webhook("https://hooks.slack.com/test", "Alert!")
        assert response.success is True
        assert response.data["posted"] is True
    
    def test_get_channels(self, stub):
        """Test getting channels."""
        response = stub.get_channels()
        assert response.success is True
        assert len(response.data["channels"]) == 3


class TestGoogleDriveStub:
    """Tests for Google Drive stub."""
    
    @pytest.fixture
    def stub(self):
        return GoogleDriveStub()
    
    def test_list_files(self, stub):
        """Test listing files."""
        response = stub.list_files()
        assert response.success is True
        assert len(response.data["files"]) == 2
    
    def test_upload_file(self, stub):
        """Test file upload."""
        response = stub.upload_file("test.pdf", "application/pdf")
        assert response.success is True
        assert response.data["uploaded"] is True
    
    def test_drive_stubbed(self, stub):
        """Test stub detection."""
        assert stub.drive_stubbed() is True
    
    def test_credentials_available(self, stub):
        """Test credentials check."""
        assert stub.credentials_available() is True


class TestStubBaseClass:
    """Tests for base stub class."""
    
    def test_stub_response_to_dict(self):
        """Test StubResponse serialization."""
        response = StubResponse(
            success=True,
            data={"key": "value"},
            message="Test message"
        )
        data = response.to_dict()
        assert data["success"] is True
        assert data["data"]["key"] == "value"
        assert "timestamp" in data
    
    def test_stub_error_to_dict(self):
        """Test StubError serialization."""
        error = StubError(error="Something failed", code="TEST_ERROR")
        data = error.to_dict()
        assert data["success"] is False
        assert data["error"] == "Something failed"
        assert data["code"] == "TEST_ERROR"
    
    def test_base_stub_is_available(self):
        """Test that stubs are always available."""
        stub = ProcoreStub()
        assert stub.is_available() is True
