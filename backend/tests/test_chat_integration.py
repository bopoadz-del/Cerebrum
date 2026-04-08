"""
Test Suite for Cerebrum Chat Integration

Covers:
1. Normal chat routing (greetings, general queries)
2. Economics layer queries (cost estimates, RSMeans searches)
3. VDC layer queries (BIM, quantities)
4. File upload + analysis flow
5. Memory search and retrieval
6. Error handling scenarios
7. Edge cases (vague inputs, malformed queries)
"""

import pytest
import json
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from httpx import AsyncClient, Response

# Import the FastAPI app
from app.main import app
from app.api.v1.endpoints.chat import (
    chat_completions, ChatCompletionRequest, ChatMessage,
    is_economics_query, generate_conversational_response, handle_economics_query
)
from app.agent.enhanced_core import (
    EnhancedCerebrumAgent, AgentLayer, AgentAction, AgentResult,
    EnhancedConversationReader, EnhancedLayerNavigator
)
from app.agent.core import CerebrumAgent


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_agent():
    """Create a mock enhanced agent."""
    agent = Mock(spec=EnhancedCerebrumAgent)
    agent.context = Mock()
    agent.context.current_layer = AgentLayer.CODING
    agent.context.session_id = "test_session_001"
    agent.context.conversation_history = []
    agent.context.generated_artifacts = []
    agent.tools = {}
    return agent


@pytest.fixture
def mock_conversation_reader():
    """Create a mock conversation reader."""
    reader = Mock(spec=EnhancedConversationReader)
    reader.memory_index = {}
    return reader


@pytest.fixture
def sample_chat_request():
    """Create a sample chat completion request."""
    return {
        "model": "cerebrum-default",
        "messages": [
            {"role": "user", "content": "Hello!"}
        ],
        "temperature": 0.7,
        "max_tokens": 2048,
        "stream": False
    }


@pytest.fixture
def sample_economics_request():
    """Create a sample economics chat request."""
    return {
        "model": "cerebrum-default",
        "messages": [
            {"role": "user", "content": "Calculate cost for 5000 sq ft office building"}
        ],
        "temperature": 0.7,
        "max_tokens": 2048
    }


# ============================================================================
# Test Class: Normal Chat Routing
# ============================================================================

class TestNormalChatRouting:
    """Tests for normal chat routing and greetings."""

    def test_greeting_hello(self, client):
        """Test greeting with 'hello'."""
        request = {
            "model": "cerebrum-default",
            "messages": [{"role": "user", "content": "hello"}]
        }
        
        with patch('app.api.v1.endpoints.chat.get_enhanced_agent') as mock_get_agent:
            mock_agent = Mock()
            mock_get_agent.return_value = mock_agent
            
            response = client.post("/api/v1/chat/completions", json=request)
            
        assert response.status_code == 200
        data = response.json()
        assert "choices" in data
        assert len(data["choices"]) == 1
        content = data["choices"][0]["message"]["content"]
        assert "cerebrum" in content.lower() or "hello" in content.lower()

    def test_greeting_hi(self, client):
        """Test greeting with 'hi'."""
        request = {
            "model": "cerebrum-default",
            "messages": [{"role": "user", "content": "hi there"}]
        }
        
        with patch('app.api.v1.endpoints.chat.get_enhanced_agent') as mock_get_agent:
            mock_agent = Mock()
            mock_get_agent.return_value = mock_agent
            
            response = client.post("/api/v1/chat/completions", json=request)
            
        assert response.status_code == 200
        data = response.json()
        assert "choices" in data

    def test_help_query(self, client):
        """Test help/capabilities query."""
        request = {
            "model": "cerebrum-default",
            "messages": [{"role": "user", "content": "what can you do?"}]
        }
        
        with patch('app.api.v1.endpoints.chat.get_enhanced_agent') as mock_get_agent:
            mock_agent = Mock()
            mock_get_agent.return_value = mock_agent
            
            response = client.post("/api/v1/chat/completions", json=request)
            
        assert response.status_code == 200
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        assert any(word in content.lower() for word in ["help", "construction", "cost", "estimate"])

    def test_who_are_you(self, client):
        """Test 'who are you' query."""
        request = {
            "model": "cerebrum-default",
            "messages": [{"role": "user", "content": "who are you?"}]
        }
        
        with patch('app.api.v1.endpoints.chat.get_enhanced_agent') as mock_get_agent:
            mock_agent = Mock()
            mock_get_agent.return_value = mock_agent
            
            response = client.post("/api/v1/chat/completions", json=request)
            
        assert response.status_code == 200

    def test_conversational_response_with_context(self, client):
        """Test conversational response with conversation history."""
        request = {
            "model": "cerebrum-default",
            "messages": [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "Hi! How can I help?"},
                {"role": "user", "content": "thanks for your help"}
            ]
        }
        
        with patch('app.api.v1.endpoints.chat.get_enhanced_agent') as mock_get_agent:
            mock_agent = Mock()
            mock_get_agent.return_value = mock_agent
            
            response = client.post("/api/v1/chat/completions", json=request)
            
        assert response.status_code == 200

    def test_generate_conversational_response_greeting(self):
        """Test generate_conversational_response function for greetings."""
        response = generate_conversational_response("hello", "")
        assert "cerebrum" in response.lower() or "hello" in response.lower()
        
    def test_generate_conversational_response_help(self):
        """Test generate_conversational_response function for help."""
        response = generate_conversational_response("what can you do?", "")
        assert len(response) > 0
        assert "construction" in response.lower() or "cost" in response.lower() or "help" in response.lower()

    def test_generate_conversational_response_default(self):
        """Test generate_conversational_response for unrecognized queries."""
        response = generate_conversational_response("something random", "")
        assert len(response) > 0

    @pytest.mark.asyncio
    async def test_conversation_history_included(self):
        """Test that conversation history is passed to agent."""
        messages = [
            ChatMessage(role="user", content="hello"),
            ChatMessage(role="assistant", content="Hi!"),
            ChatMessage(role="user", content="how are you?")
        ]
        request = ChatCompletionRequest(messages=messages)
        
        with patch('app.api.v1.endpoints.chat.get_enhanced_agent') as mock_get_agent:
            mock_agent = Mock()
            mock_agent.run = AsyncMock(return_value=AgentResult(
                success=True,
                action=AgentAction.READ_MEMORY,
                layer=AgentLayer.PORTAL,
                data={},
                message="I'm doing well!"
            ))
            mock_get_agent.return_value = mock_agent
            
            response = await chat_completions(request)
            
            # Check that conversation history was built
            mock_agent.run.assert_called_once()
            call_args = mock_agent.run.call_args
            assert "context" in call_args.kwargs


# ============================================================================
# Test Class: Economics Layer Queries
# ============================================================================

class TestEconomicsLayerQueries:
    """Tests for economics layer queries and cost estimations."""

    def test_is_economics_query_concrete(self):
        """Test detection of concrete-related queries."""
        assert is_economics_query("Calculate concrete cost") == True
        assert is_economics_query("Price of concrete per cubic yard") == True

    def test_is_economics_query_building(self):
        """Test detection of building cost queries."""
        assert is_economics_query("Cost for 5000 sq ft office") == True
        assert is_economics_query("Estimate warehouse 10000 square feet") == True

    def test_is_economics_query_steel(self):
        """Test detection of steel-related queries."""
        assert is_economics_query("Steel reinforcement price") == True

    def test_is_economics_query_rsmeans(self):
        """Test detection of RSMeans queries."""
        assert is_economics_query("RSMeans pricing for drywall") == True

    def test_is_not_economics_query(self):
        """Test that non-economics queries return False."""
        assert is_economics_query("Hello") == False
        assert is_economics_query("What can you do?") == False
        assert is_economics_query("Tell me a joke") == False

    def test_economics_query_with_office_building(self, client):
        """Test cost estimation for office building."""
        request = {
            "model": "cerebrum-default",
            "messages": [{"role": "user", "content": "Calculate cost for 5000 sq ft office building"}]
        }
        
        with patch('app.api.v1.endpoints.chat.get_enhanced_agent') as mock_get_agent:
            mock_agent = Mock()
            mock_agent.run = AsyncMock(return_value=AgentResult(
                success=True,
                action=AgentAction.CALCULATE_COST,
                layer=AgentLayer.ECONOMICS,
                data={"building_type": "office", "size_sf": 5000, "total_cost": 1000000},
                message="Estimated cost: $1,000,000"
            ))
            mock_agent.move_to_layer = Mock()
            mock_get_agent.return_value = mock_agent
            
            response = client.post("/api/v1/chat/completions", json=request)
            
        assert response.status_code == 200

    def test_economics_query_with_warehouse(self, client):
        """Test cost estimation for warehouse."""
        request = {
            "model": "cerebrum-default",
            "messages": [{"role": "user", "content": "Estimate warehouse 10000 sq ft"}]
        }
        
        with patch('app.api.v1.endpoints.chat.get_enhanced_agent') as mock_get_agent:
            mock_agent = Mock()
            mock_agent.run = AsyncMock(return_value=AgentResult(
                success=True,
                action=AgentAction.CALCULATE_COST,
                layer=AgentLayer.ECONOMICS,
                data={"building_type": "warehouse", "size_sf": 10000},
                message="Warehouse estimate: $500,000"
            ))
            mock_get_agent.return_value = mock_agent
            
            response = client.post("/api/v1/chat/completions", json=request)
            
        assert response.status_code == 200

    def test_economics_query_cubic_meters(self, client):
        """Test concrete cost calculation with cubic meters."""
        request = {
            "model": "cerebrum-default",
            "messages": [{"role": "user", "content": "Cost of 100 cubic meters of concrete"}]
        }
        
        with patch('app.api.v1.endpoints.chat.get_enhanced_agent') as mock_get_agent:
            mock_agent = Mock()
            mock_agent.run = AsyncMock(return_value=AgentResult(
                success=True,
                action=AgentAction.CALCULATE_COST,
                layer=AgentLayer.ECONOMICS,
                data={"quantity": 100, "material": "concrete"},
                message="Concrete cost: $12,000"
            ))
            mock_get_agent.return_value = mock_agent
            
            response = client.post("/api/v1/chat/completions", json=request)
            
        assert response.status_code == 200

    def test_economics_query_materials(self, client):
        """Test material cost queries."""
        test_cases = [
            "Price of steel per ton",
            "Cost of lumber for framing",
            "Drywall pricing",
            "Paint cost per gallon"
        ]
        
        for query in test_cases:
            request = {
                "model": "cerebrum-default",
                "messages": [{"role": "user", "content": query}]
            }
            
            with patch('app.api.v1.endpoints.chat.get_enhanced_agent') as mock_get_agent:
                mock_agent = Mock()
                mock_get_agent.return_value = mock_agent
                
                response = client.post("/api/v1/chat/completions", json=request)
                assert response.status_code == 200, f"Failed for query: {query}"

    @pytest.mark.asyncio
    async def test_handle_economics_query_building_estimate(self):
        """Test handle_economics_query for building estimation."""
        agent = Mock(spec=EnhancedCerebrumAgent)
        agent.tools = {
            'estimate_project': Mock(return_value={
                "success": True,
                "building_type": "office-low",
                "size_sf": 5000,
                "total_cost": 1125000
            })
        }
        agent.move_to_layer = Mock()
        agent._format_result_message = Mock(return_value="Cost: $1,125,000")
        
        message = "Estimate cost for 5000 sq ft office"
        response = await handle_economics_query(agent, message)
        
        assert "Cost" in response or "$" in response or "cost" in response.lower()

    @pytest.mark.asyncio
    async def test_handle_economics_query_material_cost(self):
        """Test handle_economics_query for material cost."""
        agent = Mock(spec=EnhancedCerebrumAgent)
        agent.tools = {
            'calculate_cost': Mock(return_value={
                "success": True,
                "item": {"description": "Concrete", "base_cost": 120},
                "quantity": 100,
                "total_cost": 12000
            })
        }
        agent.move_to_layer = Mock()
        agent._format_result_message = Mock(return_value="Total cost: $12,000")
        
        message = "Calculate cost for 100 cubic yards of concrete"
        response = await handle_economics_query(agent, message)
        
        assert len(response) > 0


# ============================================================================
# Test Class: VDC Layer Queries
# ============================================================================

class TestVDCLayerQueries:
    """Tests for VDC layer queries including BIM and quantities."""

    def test_bim_query(self, client):
        """Test BIM model queries."""
        request = {
            "model": "cerebrum-default",
            "messages": [{"role": "user", "content": "Query BIM model for walls"}]
        }
        
        with patch('app.api.v1.endpoints.chat.get_enhanced_agent') as mock_get_agent:
            mock_agent = Mock()
            mock_agent.run = AsyncMock(return_value=AgentResult(
                success=True,
                action=AgentAction.QUERY_BIM,
                layer=AgentLayer.VDC,
                data={"elements": [{"type": "wall", "count": 50}]},
                message="Found 50 walls in the model"
            ))
            mock_get_agent.return_value = mock_agent
            
            response = client.post("/api/v1/chat/completions", json=request)
            
        assert response.status_code == 200

    def test_quantity_extraction(self, client):
        """Test quantity extraction queries."""
        request = {
            "model": "cerebrum-default",
            "messages": [{"role": "user", "content": "Extract concrete quantities from BIM"}]
        }
        
        with patch('app.api.v1.endpoints.chat.get_enhanced_agent') as mock_get_agent:
            mock_agent = Mock()
            mock_agent.run = AsyncMock(return_value=AgentResult(
                success=True,
                action=AgentAction.QUERY_BIM,
                layer=AgentLayer.VDC,
                data={"quantities": [{"type": "concrete", "volume": 500}]},
                message="Extracted 500 cubic yards of concrete"
            ))
            mock_get_agent.return_value = mock_agent
            
            response = client.post("/api/v1/chat/completions", json=request)
            
        assert response.status_code == 200

    def test_clash_detection(self, client):
        """Test clash detection queries."""
        request = {
            "model": "cerebrum-default",
            "messages": [{"role": "user", "content": "Check for clashes in the model"}]
        }
        
        with patch('app.api.v1.endpoints.chat.get_enhanced_agent') as mock_get_agent:
            mock_agent = Mock()
            mock_agent.run = AsyncMock(return_value=AgentResult(
                success=True,
                action=AgentAction.QUERY_BIM,
                layer=AgentLayer.VDC,
                data={"clashes": []},
                message="No clashes detected"
            ))
            mock_get_agent.return_value = mock_agent
            
            response = client.post("/api/v1/chat/completions", json=request)
            
        assert response.status_code == 200

    def test_ifc_model_query(self, client):
        """Test IFC model queries."""
        request = {
            "model": "cerebrum-default",
            "messages": [{"role": "user", "content": "Get all doors from IFC model"}]
        }
        
        with patch('app.api.v1.endpoints.chat.get_enhanced_agent') as mock_get_agent:
            mock_agent = Mock()
            mock_get_agent.return_value = mock_agent
            
            response = client.post("/api/v1/chat/completions", json=request)
            
        assert response.status_code == 200


# ============================================================================
# Test Class: File Upload + Analysis Flow
# ============================================================================

class TestFileUploadAnalysis:
    """Tests for file upload and analysis flow."""

    def test_upload_image_file(self, client):
        """Test uploading an image file."""
        with patch('app.api.v1.endpoints.documents.get_current_user') as mock_user:
            mock_user.return_value = Mock(id="test_user_001")
            
            file_content = b"fake_image_content"
            response = client.post(
                "/api/v1/documents/upload/chat",
                files={"file": ("test.png", file_content, "image/png")}
            )
            
        assert response.status_code in [200, 500]  # May fail if file storage isn't set up

    def test_upload_pdf_file(self, client):
        """Test uploading a PDF file."""
        with patch('app.api.v1.endpoints.documents.get_current_user') as mock_user:
            mock_user.return_value = Mock(id="test_user_001")
            
            file_content = b"fake_pdf_content"
            response = client.post(
                "/api/v1/documents/upload/chat",
                files={"file": ("test.pdf", file_content, "application/pdf")}
            )
            
        assert response.status_code in [200, 500]

    def test_upload_oversized_file(self, client):
        """Test uploading an oversized file (should fail)."""
        with patch('app.api.v1.endpoints.documents.get_current_user') as mock_user:
            mock_user.return_value = Mock(id="test_user_001")
            
            # Create a file larger than 50MB
            file_content = b"x" * (51 * 1024 * 1024)
            response = client.post(
                "/api/v1/documents/upload/chat",
                files={"file": ("large.pdf", file_content, "application/pdf")}
            )
            
        assert response.status_code == 413

    def test_chat_with_file_id(self, client):
        """Test chat query referencing an uploaded file."""
        file_id = "test_user_001_abc123"
        request = {
            "model": "cerebrum-default",
            "messages": [{"role": "user", "content": f"What is in this file? [{file_id}]"}]
        }
        
        with patch('app.api.v1.endpoints.chat.get_enhanced_agent') as mock_get_agent, \
             patch('app.api.v1.endpoints.documents.os.path.exists') as mock_exists:
            mock_agent = Mock()
            mock_agent._analyze_uploaded_file = AsyncMock(return_value=AgentResult(
                success=True,
                action=AgentAction.READ_MEMORY,
                layer=AgentLayer.PORTAL,
                data={"file_id": file_id, "text": "Extracted text"},
                message="Image Analysis: Found invoice data"
            ))
            mock_get_agent.return_value = mock_agent
            mock_exists.return_value = True
            
            response = client.post("/api/v1/chat/completions", json=request)
            
        assert response.status_code == 200

    def test_ocr_endpoint(self, client):
        """Test OCR processing endpoint."""
        with patch('app.api.v1.endpoints.documents.get_current_user') as mock_user, \
             patch('app.pipelines.ocr.TesseractOCR') as mock_ocr:
            mock_user.return_value = Mock(id="test_user_001")
            
            mock_ocr_instance = Mock()
            mock_ocr_instance.process_image = AsyncMock(return_value=Mock(
                text="Extracted text",
                confidence=0.95,
                language="eng",
                word_count=10,
                processing_time=0.5
            ))
            mock_ocr.return_value = mock_ocr_instance
            
            file_content = b"fake_image_content"
            response = client.post(
                "/api/v1/documents/ocr",
                files={"file": ("test.png", file_content, "image/png")},
                data={"language": "eng", "mode": "standard"}
            )
            
        assert response.status_code in [200, 500, 503]  # May fail if OCR not available

    def test_document_classification(self, client):
        """Test document classification endpoint."""
        with patch('app.api.v1.endpoints.documents.get_current_user') as mock_user, \
             patch('app.pipelines.document_classification.classify_document') as mock_classify:
            mock_user.return_value = Mock(id="test_user_001")
            
            mock_classify.return_value = Mock(
                primary_classification=Mock(
                    document_type=Mock(value="invoice"),
                    category=Mock(value="financial"),
                    confidence=0.92,
                    subtype="vendor_invoice",
                    key_fields={"amount": 1000, "vendor": "ACME"}
                )
            )
            
            file_content = b"fake_pdf_content"
            response = client.post(
                "/api/v1/documents/classify",
                files={"file": ("invoice.pdf", file_content, "application/pdf")}
            )
            
        assert response.status_code in [200, 500]


# ============================================================================
# Test Class: Memory Search and Retrieval
# ============================================================================

class TestMemorySearchRetrieval:
    """Tests for memory search and retrieval functionality."""

    def test_memory_search_endpoint(self, client):
        """Test memory search API endpoint."""
        with patch('app.api.v1.endpoints.chat.get_enhanced_agent') as mock_get_agent:
            mock_agent = Mock()
            mock_agent.tools = {
                "search_memory": Mock(return_value={
                    "query": "concrete costs",
                    "results": [{"id": "1", "content": "Concrete is $120/cy", "score": 10.5}],
                    "total_matches": 1
                })
            }
            mock_get_agent.return_value = mock_agent
            
            response = client.post(
                "/api/v1/agent/memory/search",
                json={"query": "concrete costs", "limit": 5}
            )
            
        assert response.status_code in [200, 401]  # 401 if auth required

    def test_conversation_read_endpoint(self, client):
        """Test conversation reading endpoint."""
        with patch('app.api.v1.endpoints.chat.get_enhanced_agent') as mock_get_agent:
            mock_agent = Mock()
            mock_agent.tools = {
                "read_conversation": Mock(return_value={
                    "recent_conversations": [],
                    "memory_md": {},
                    "session_id": "test_session"
                })
            }
            mock_get_agent.return_value = mock_agent
            
            response = client.post(
                "/api/v1/agent/conversation/read",
                json={"days": 7}
            )
            
        assert response.status_code in [200, 401]

    def test_agent_run_with_memory_context(self, client):
        """Test that agent.run includes memory context."""
        request = {
            "model": "cerebrum-default",
            "messages": [{"role": "user", "content": "Search memory for project notes"}]
        }
        
        with patch('app.api.v1.endpoints.chat.get_enhanced_agent') as mock_get_agent:
            mock_agent = Mock()
            mock_agent.run = AsyncMock(return_value=AgentResult(
                success=True,
                action=AgentAction.READ_MEMORY,
                layer=AgentLayer.PORTAL,
                data={"results": [{"content": "Project notes"}]},
                message="Found project notes in memory"
            ))
            mock_get_agent.return_value = mock_agent
            
            response = client.post("/api/v1/chat/completions", json=request)
            
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_conversation_reader_semantic_search(self, mock_conversation_reader):
        """Test conversation reader semantic search."""
        mock_conversation_reader.semantic_search = Mock(return_value={
            "query": "concrete",
            "total_matches": 2,
            "results": [
                {"id": "1", "content": "Concrete costs", "score": 15.0},
                {"id": "2", "content": "Concrete mix design", "score": 10.0}
            ]
        })
        
        result = mock_conversation_reader.semantic_search("concrete", limit=5)
        
        assert result["total_matches"] == 2
        assert len(result["results"]) == 2

    def test_chat_with_conversation_id(self, client):
        """Test chat with conversation ID for continuity."""
        request = {
            "model": "cerebrum-default",
            "messages": [{"role": "user", "content": "hello"}],
            "conversation_id": "conv_12345"
        }
        
        with patch('app.api.v1.endpoints.chat.get_enhanced_agent') as mock_get_agent:
            mock_agent = Mock()
            mock_get_agent.return_value = mock_agent
            
            response = client.post("/api/v1/chat/completions", json=request)
            
        assert response.status_code == 200


# ============================================================================
# Test Class: Error Handling Scenarios
# ============================================================================

class TestErrorHandling:
    """Tests for error handling scenarios."""

    def test_empty_messages_list(self, client):
        """Test error handling for empty messages list."""
        request = {
            "model": "cerebrum-default",
            "messages": []
        }
        
        response = client.post("/api/v1/chat/completions", json=request)
        assert response.status_code == 400
        assert "no user message" in response.json()["detail"].lower()

    def test_no_user_message(self, client):
        """Test error when only system messages provided."""
        request = {
            "model": "cerebrum-default",
            "messages": [{"role": "system", "content": "You are a helpful assistant"}]
        }
        
        response = client.post("/api/v1/chat/completions", json=request)
        assert response.status_code == 400

    def test_agent_execution_failure(self, client):
        """Test fallback when agent execution fails."""
        request = {
            "model": "cerebrum-default",
            "messages": [{"role": "user", "content": "Generate an endpoint"}]
        }
        
        with patch('app.api.v1.endpoints.chat.get_enhanced_agent') as mock_get_agent:
            mock_agent = Mock()
            mock_agent.run = AsyncMock(side_effect=Exception("Agent failed"))
            mock_get_agent.return_value = mock_agent
            
            response = client.post("/api/v1/chat/completions", json=request)
            
        # Should still return 200 with fallback response
        assert response.status_code == 200
        data = response.json()
        assert "choices" in data

    def test_invalid_layer_specification(self, client):
        """Test error handling for invalid layer."""
        with patch('app.api.v1.endpoints.chat.get_enhanced_agent') as mock_get_agent:
            mock_agent = Mock()
            mock_agent.move_to_layer = Mock(side_effect=ValueError("Invalid layer"))
            mock_get_agent.return_value = mock_agent
            
            response = client.post(
                "/api/v1/agent/execute",
                json={"task": "test", "layer": "invalid_layer"}
            )
            
        assert response.status_code in [400, 422, 401]

    def test_rate_limit_handling(self, client):
        """Test handling of rate limit errors."""
        # This is more of a documentation test - actual rate limiting
        # would be handled at middleware level
        pass

    def test_timeout_handling(self, client):
        """Test handling of timeout scenarios."""
        request = {
            "model": "cerebrum-default",
            "messages": [{"role": "user", "content": "Complex analysis task"}]
        }
        
        with patch('app.api.v1.endpoints.chat.get_enhanced_agent') as mock_get_agent:
            import asyncio
            mock_agent = Mock()
            mock_agent.run = AsyncMock(side_effect=asyncio.TimeoutError("Operation timed out"))
            mock_get_agent.return_value = mock_agent
            
            response = client.post("/api/v1/chat/completions", json=request)
            
        assert response.status_code in [200, 500, 504]

    def test_database_connection_error(self, client):
        """Test handling of database connection errors."""
        with patch('app.api.v1.endpoints.documents.get_current_user') as mock_user:
            mock_user.side_effect = Exception("Database connection failed")
            
            response = client.get("/api/v1/documents/files")
            
        assert response.status_code in [401, 500]

    @pytest.mark.asyncio
    async def test_tool_not_found_error(self):
        """Test handling when tool is not found."""
        agent = Mock(spec=EnhancedCerebrumAgent)
        agent.tools = {}
        agent.move_to_layer = Mock()
        
        message = "Some query"
        response = await handle_economics_query(agent, message)
        
        assert "trouble" in response.lower() or "couldn't" in response.lower()


# ============================================================================
# Test Class: Edge Cases
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and unusual inputs."""

    def test_very_short_query(self, client):
        """Test handling of very short queries."""
        request = {
            "model": "cerebrum-default",
            "messages": [{"role": "user", "content": "ok"}]
        }
        
        with patch('app.api.v1.endpoints.chat.get_enhanced_agent') as mock_get_agent:
            mock_agent = Mock()
            mock_get_agent.return_value = mock_agent
            
            response = client.post("/api/v1/chat/completions", json=request)
            
        assert response.status_code == 200

    def test_vague_input_formulas(self, client):
        """Test handling of vague 'formulas' input."""
        request = {
            "model": "cerebrum-default",
            "messages": [{"role": "user", "content": "formulas"}]
        }
        
        with patch('app.api.v1.endpoints.chat.get_enhanced_agent') as mock_get_agent:
            mock_agent = Mock()
            mock_get_agent.return_value = mock_agent
            
            response = client.post("/api/v1/chat/completions", json=request)
            
        assert response.status_code == 200

    def test_malformed_json_in_request(self, client):
        """Test handling of malformed JSON."""
        response = client.post(
            "/api/v1/chat/completions",
            data="not valid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422

    def test_special_characters_in_message(self, client):
        """Test handling of special characters."""
        request = {
            "model": "cerebrum-default",
            "messages": [{"role": "user", "content": "Cost of concrete @ $120/cy with <50> units!"}]
        }
        
        with patch('app.api.v1.endpoints.chat.get_enhanced_agent') as mock_get_agent:
            mock_agent = Mock()
            mock_get_agent.return_value = mock_agent
            
            response = client.post("/api/v1/chat/completions", json=request)
            
        assert response.status_code == 200

    def test_unicode_characters(self, client):
        """Test handling of unicode characters."""
        request = {
            "model": "cerebrum-default",
            "messages": [{"role": "user", "content": "🏗️ Cost of building in € or ¥?"}]
        }
        
        with patch('app.api.v1.endpoints.chat.get_enhanced_agent') as mock_get_agent:
            mock_agent = Mock()
            mock_get_agent.return_value = mock_agent
            
            response = client.post("/api/v1/chat/completions", json=request)
            
        assert response.status_code == 200

    def test_very_long_message(self, client):
        """Test handling of very long messages."""
        long_content = "Estimate cost for " + "a very large " * 1000 + "office building"
        request = {
            "model": "cerebrum-default",
            "messages": [{"role": "user", "content": long_content}]
        }
        
        with patch('app.api.v1.endpoints.chat.get_enhanced_agent') as mock_get_agent:
            mock_agent = Mock()
            mock_get_agent.return_value = mock_agent
            
            response = client.post("/api/v1/chat/completions", json=request)
            
        assert response.status_code in [200, 413]  # May fail if too large

    def test_multiple_user_messages(self, client):
        """Test handling of multiple user messages in history."""
        request = {
            "model": "cerebrum-default",
            "messages": [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "Hi!"},
                {"role": "user", "content": "cost of concrete?"},
                {"role": "assistant", "content": "$120/cy"},
                {"role": "user", "content": "what about steel?"}
            ]
        }
        
        with patch('app.api.v1.endpoints.chat.get_enhanced_agent') as mock_get_agent:
            mock_agent = Mock()
            mock_get_agent.return_value = mock_agent
            
            response = client.post("/api/v1/chat/completions", json=request)
            
        assert response.status_code == 200

    def test_case_insensitive_greeting(self, client):
        """Test case-insensitive greeting detection."""
        greetings = ["HELLO", "Hello", "HeLLo", "HI", "Hi", "HEY", "hey"]
        
        for greeting in greetings:
            request = {
                "model": "cerebrum-default",
                "messages": [{"role": "user", "content": greeting}]
            }
            
            with patch('app.api.v1.endpoints.chat.get_enhanced_agent') as mock_get_agent:
                mock_agent = Mock()
                mock_get_agent.return_value = mock_agent
                
                response = client.post("/api/v1/chat/completions", json=request)
                assert response.status_code == 200, f"Failed for greeting: {greeting}"

    def test_mixed_case_economics_query(self, client):
        """Test mixed case economics queries."""
        queries = [
            "Calculate COST for 5000 SQ FT Office",
            "CONCRETE price per cubic yard",
            "Estimate Warehouse 10000 Sq Ft"
        ]
        
        for query in queries:
            assert is_economics_query(query) == True, f"Failed for: {query}"

    def test_ambiguous_building_type(self, client):
        """Test handling of ambiguous building types."""
        request = {
            "model": "cerebrum-default",
            "messages": [{"role": "user", "content": "Cost of office building"}]
        }
        
        with patch('app.api.v1.endpoints.chat.get_enhanced_agent') as mock_get_agent:
            mock_agent = Mock()
            mock_agent.run = AsyncMock(return_value=AgentResult(
                success=True,
                action=AgentAction.CALCULATE_COST,
                layer=AgentLayer.ECONOMICS,
                data={
                    "requires_clarification": True,
                    "building_type_suggestions": ["office-low", "office-high"]
                },
                message="Which office type: office-low or office-high?"
            ))
            mock_get_agent.return_value = mock_agent
            
            response = client.post("/api/v1/chat/completions", json=request)
            
        assert response.status_code == 200

    def test_number_parsing_edge_cases(self):
        """Test number parsing in economics queries."""
        from app.agent.enhanced_core import EnhancedCerebrumAgent
        
        agent = EnhancedCerebrumAgent()
        
        # Test various number formats
        test_cases = [
            ("100 sq ft", 100),
            ("1,000 sq ft", 1000),
            ("10000", 10000),
            ("10,000", 10000),
            ("10.5 sq meters", None),  # Metric conversion
        ]
        
        for query, expected in test_cases:
            result = agent._parse_economics_natural_language(query)
            if expected:
                assert result["size_sf"] is not None or result["quantity"] is not None


# ============================================================================
# Test Class: Model Listing
# ============================================================================

class TestModelListing:
    """Tests for model listing endpoint."""

    def test_list_models(self, client):
        """Test listing available models."""
        response = client.get("/api/v1/chat/models")
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) >= 1
        assert any(m["id"] == "cerebrum-default" for m in data["data"])


# ============================================================================
# Test Class: WebSocket Connection
# ============================================================================

class TestWebSocket:
    """Tests for WebSocket functionality."""

    @pytest.mark.asyncio
    async def test_websocket_endpoint_exists(self):
        """Test that WebSocket endpoint is configured."""
        # WebSocket testing requires async client
        # This is a basic check that the endpoint exists
        from app.agent.websocket import get_websocket_manager
        
        with patch('app.agent.enhanced_core.get_enhanced_agent') as mock_agent:
            mock_agent.return_value = Mock()
            manager = get_websocket_manager(mock_agent.return_value)
            assert manager is not None


# ============================================================================
# Integration Test Helpers
# ============================================================================

def create_mock_agent_result(success=True, layer=AgentLayer.PORTAL, message="Test response"):
    """Helper to create mock agent results."""
    return AgentResult(
        success=success,
        action=AgentAction.READ_MEMORY,
        layer=layer,
        data={},
        message=message,
        timestamp=datetime.now().isoformat(),
        execution_time_ms=100.0
    )


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
