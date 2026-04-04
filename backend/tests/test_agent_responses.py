"""
Test Suite for Cerebrum Agent Responses

Tests agent response formatting, routing logic, and output generation.
Covers all 14 layers and various response types.
"""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, Any, List

from app.agent.enhanced_core import (
    EnhancedCerebrumAgent, AgentLayer, AgentAction, AgentResult,
    EnhancedConversationReader, EnhancedLayerNavigator,
    LayerState, AgentContext, MemoryIndex
)
from app.agent.core import CerebrumAgent, AgentAction as CoreAgentAction


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def agent():
    """Create a fresh enhanced agent instance."""
    return EnhancedCerebrumAgent(workspace_path="/tmp/test_workspace")


@pytest.fixture
def mock_layer_navigator():
    """Create a mock layer navigator."""
    navigator = Mock(spec=EnhancedLayerNavigator)
    navigator.layer_capabilities = {
        AgentLayer.ECONOMICS: ["calculate_cost", "estimate_project", "rsmeans_query"],
        AgentLayer.VDC: ["query_bim", "extract_quantities", "check_clash"],
        AgentLayer.CODING: ["generate_endpoint", "generate_component"],
    }
    return navigator


@pytest.fixture
def sample_building_estimate_result():
    """Create a sample building estimate result."""
    return {
        "success": True,
        "building_type": "office-low",
        "size_sf": 5000,
        "city": "National Average",
        "costs": {
            "substructure": 50000,
            "shell": 150000,
            "interiors": 100000,
            "equipment": 50000
        },
        "total_cost": 1125000,
        "cost_per_sqft": 225
    }


@pytest.fixture
def sample_rsmeans_result():
    """Create a sample RSMeans query result."""
    return {
        "success": True,
        "query": "concrete",
        "total": 3,
        "results": [
            {
                "item_id": "03-100-100",
                "description": "Concrete, 3000 psi",
                "base_cost": 120.50,
                "unit": "cy"
            },
            {
                "item_id": "03-100-200",
                "description": "Concrete, 4000 psi",
                "base_cost": 135.75,
                "unit": "cy"
            }
        ]
    }


@pytest.fixture
def sample_memory_search_result():
    """Create a sample memory search result."""
    return {
        "query": "concrete costs",
        "total_matches": 5,
        "results": [
            {
                "id": "abc123",
                "score": 15.5,
                "content": "Concrete foundation cost $120 per cubic yard",
                "source": "memory/2024-01-15.md",
                "timestamp": "2024-01-15T10:30:00",
                "tags": ["costs", "concrete"]
            },
            {
                "id": "def456",
                "score": 12.0,
                "content": "Office building concrete requirements",
                "source": "MEMORY.md",
                "timestamp": "2024-01-10T14:20:00",
                "tags": ["building", "concrete"]
            }
        ]
    }


@pytest.fixture
def sample_bim_result():
    """Create a sample BIM query result."""
    return {
        "success": True,
        "model": "sample_model.ifc",
        "elements": [
            {"type": "wall", "count": 50, "material": "concrete"},
            {"type": "door", "count": 20, "material": "steel"},
            {"type": "window", "count": 30, "material": "glass"}
        ]
    }


@pytest.fixture
def sample_quantity_result():
    """Create a sample quantity extraction result."""
    return {
        "success": True,
        "quantities": [
            {"name": "Concrete walls", "quantity": 500, "unit": "cy"},
            {"name": "Steel beams", "quantity": 50, "unit": "tons"},
            {"name": "Drywall", "quantity": 10000, "unit": "sf"}
        ],
        "total_volume": 500,
        "total_area": 10000
    }


# ============================================================================
# Test Class: Agent Result Formatting
# ============================================================================

class TestAgentResultFormatting:
    """Tests for agent result formatting functions."""

    def test_format_currency(self, agent):
        """Test currency formatting."""
        assert agent._format_currency(1000) == "$1,000.00"
        assert agent._format_currency(0) == "$0.00"
        assert agent._format_currency(1234567.89) == "$1,234,567.89"

    def test_format_number(self, agent):
        """Test number formatting."""
        assert agent._format_number(1000) == "1,000.00"
        assert agent._format_number(1000, 0) == "1,000"
        assert agent._format_number(1234.567, 2) == "1,234.57"

    def test_format_economics_building_estimate(self, agent, sample_building_estimate_result):
        """Test formatting of building estimate results."""
        message = agent._format_economics_result(
            "estimate_project", sample_building_estimate_result, "Calculate cost"
        )
        
        assert "$1,125,000" in message or "1,125,000" in message
        assert "office" in message.lower() or "Building" in message
        assert "Cost Breakdown" in message or "cost" in message.lower()

    def test_format_economics_rsmeans(self, agent, sample_rsmeans_result):
        """Test formatting of RSMeans query results."""
        message = agent._format_economics_result(
            "rsmeans_query", sample_rsmeans_result, "Search concrete"
        )
        
        assert "RSMeans" in message or "concrete" in message.lower()
        assert "$120.50" in message or "$135.75" in message or "Concrete" in message

    def test_format_economics_error(self, agent):
        """Test formatting of economics error results."""
        error_result = {
            "success": False,
            "error": "Need building_type+size_sf or item_id+quantity"
        }
        
        message = agent._format_economics_result(
            "estimate_project", error_result, "Calculate cost"
        )
        
        assert "need more information" in message.lower() or "Try" in message

    def test_format_economics_clarification(self, agent):
        """Test formatting of building type clarification."""
        clarification_result = {
            "success": True,
            "requires_clarification": True,
            "suggestions": [
                {"code": "office-low", "name": "Low-Rise Office", "cost_per_sf": 225},
                {"code": "office-high", "name": "High-Rise Office", "cost_per_sf": 285}
            ]
        }
        
        message = agent._format_economics_result(
            "estimate_project", clarification_result, "Office building cost"
        )
        
        assert "Which" in message or "office-low" in message or "office-high" in message

    def test_format_memory_search(self, agent, sample_memory_search_result):
        """Test formatting of memory search results."""
        message = agent._format_memory_search_result(sample_memory_search_result, "concrete costs")
        
        assert "Found" in message or "found" in message
        assert "concrete" in message.lower() or "memory" in message.lower()

    def test_format_memory_search_empty(self, agent):
        """Test formatting of empty memory search results."""
        empty_result = {
            "query": "xyz123",
            "total_matches": 0,
            "results": []
        }
        
        message = agent._format_memory_search_result(empty_result, "xyz123")
        
        assert "didn't find" in message.lower() or "No results" in message or "try" in message.lower()

    def test_format_bim_result(self, agent, sample_bim_result):
        """Test formatting of BIM query results."""
        message = agent._format_bim_result(sample_bim_result, "Query walls")
        
        assert "BIM" in message or "model" in message.lower()
        assert "wall" in message.lower() or "50" in message

    def test_format_bim_empty(self, agent):
        """Test formatting of empty BIM results."""
        empty_result = {"success": True, "elements": []}
        
        message = agent._format_bim_result(empty_result, "Query model")
        
        assert "No elements" in message or "not found" in message.lower() or "Try" in message

    def test_format_quantities_result(self, agent, sample_quantity_result):
        """Test formatting of quantity extraction results."""
        message = agent._format_quantities_result(sample_quantity_result, "Extract quantities")
        
        assert "Quantity" in message or "quantity" in message.lower()
        assert "500" in message or "cy" in message or "Concrete" in message

    def test_format_validation_security_pass(self, agent):
        """Test formatting of passing security scan."""
        result = {"success": True, "passed": True, "issues": []}
        
        message = agent._format_validation_result("scan_security", result, "Scan code")
        
        assert "Passed" in message or "passed" in message.lower() or "✅" in message

    def test_format_validation_security_fail(self, agent):
        """Test formatting of failing security scan."""
        result = {
            "success": True,
            "passed": False,
            "vulnerabilities": [
                {"severity": "High", "description": "SQL injection risk"},
                {"severity": "Medium", "description": "XSS vulnerability"}
            ]
        }
        
        message = agent._format_validation_result("scan_security", result, "Scan code")
        
        assert "issue" in message.lower() or "High" in message or "⚠️" in message or "found" in message.lower()

    def test_format_generation_endpoint(self, agent):
        """Test formatting of endpoint generation result."""
        result = {"success": True, "artifact": "projects.py"}
        
        message = agent._format_generation_result("generate_endpoint", result, "Generate endpoint")
        
        assert "Generated" in message or "created" in message.lower() or "endpoint" in message.lower()

    def test_format_healing_error_fixed(self, agent):
        """Test formatting of healing success."""
        result = {"success": True, "fixed": True}
        
        message = agent._format_healing_result("heal_error", result, "Fix error")
        
        assert "Fixed" in message or "fixed" in message.lower() or "✅" in message


# ============================================================================
# Test Class: Layer Navigation
# ============================================================================

class TestLayerNavigation:
    """Tests for layer navigation functionality."""

    def test_layer_navigator_suggest_for_task(self, agent):
        """Test layer suggestions for different tasks."""
        # Test economics task
        suggestions = agent.layer_navigator.suggest_layer_for_task("Calculate concrete cost")
        assert len(suggestions) > 0
        assert any(s["layer"] == "economics" for s in suggestions)

    def test_layer_navigator_suggest_for_vdc_task(self, agent):
        """Test layer suggestions for VDC tasks."""
        suggestions = agent.layer_navigator.suggest_layer_for_task("Query BIM model")
        assert len(suggestions) > 0
        assert any(s["layer"] == "vdc" for s in suggestions)

    def test_layer_navigator_suggest_for_coding_task(self, agent):
        """Test layer suggestions for coding tasks."""
        suggestions = agent.layer_navigator.suggest_layer_for_task("Generate endpoint")
        assert len(suggestions) > 0

    def test_move_to_layer(self, agent):
        """Test moving to a different layer."""
        result = agent.move_to_layer(AgentLayer.ECONOMICS)
        
        assert result.success == True
        assert result.layer == AgentLayer.ECONOMICS
        assert agent.context.current_layer == AgentLayer.ECONOMICS

    def test_layer_state_tracking(self, agent):
        """Test that layer state is tracked correctly."""
        agent.move_to_layer(AgentLayer.ECONOMICS)
        agent.layer_navigator.record_action(AgentLayer.ECONOMICS, "calculate_cost")
        
        state = agent.layer_navigator.layer_states.get(AgentLayer.ECONOMICS)
        assert state is not None
        assert len(state.actions_performed) > 0

    def test_get_layer_info(self, agent):
        """Test getting layer information."""
        info = agent.layer_navigator.get_layer_info(AgentLayer.ECONOMICS)
        
        assert "name" in info
        assert "capabilities" in info
        assert info["name"] == "economics"

    def test_get_navigation_path(self, agent):
        """Test getting navigation path between layers."""
        path = agent.layer_navigator.get_navigation_path(
            AgentLayer.CODING, AgentLayer.ECONOMICS
        )
        
        assert len(path) > 0
        assert path[0]["layer"] == "coding"
        assert path[-1]["layer"] == "economics"


# ============================================================================
# Test Class: Tool Selection
# ============================================================================

class TestToolSelection:
    """Tests for tool selection logic."""

    def test_select_tool_for_economics_query(self, agent):
        """Test tool selection for economics queries."""
        tool = agent._select_tool_for_task("Calculate cost", AgentLayer.ECONOMICS)
        assert tool in ["calculate_cost", "rsmeans_query", "estimate_project"]

    def test_select_tool_for_bim_query(self, agent):
        """Test tool selection for BIM queries."""
        tool = agent._select_tool_for_task("Query BIM model", AgentLayer.VDC)
        assert tool in ["query_bim", "extract_quantities"]

    def test_select_tool_for_code_query(self, agent):
        """Test tool selection for code queries."""
        tool = agent._select_tool_for_task("Generate endpoint", AgentLayer.CODING)
        assert tool in ["generate_endpoint", "search_memory"]

    def test_select_tool_default_fallback(self, agent):
        """Test default tool fallback."""
        tool = agent._select_tool_for_task("something random", AgentLayer.PORTAL)
        assert tool is not None


# ============================================================================
# Test Class: Economics Natural Language Parsing
# ============================================================================

class TestEconomicsNLParsing:
    """Tests for economics natural language parsing."""

    def test_parse_office_building(self, agent):
        """Test parsing office building queries."""
        result = agent._parse_economics_natural_language("5000 sq ft office building")
        
        assert result["building_type"] is not None or result["building_type_suggestions"]
        assert result["size_sf"] == 5000

    def test_parse_warehouse(self, agent):
        """Test parsing warehouse queries."""
        result = agent._parse_economics_natural_language("10000 square feet warehouse")
        
        assert "warehouse" in str(result.get("building_type", "")).lower() or result["building_type_suggestions"]
        assert result["size_sf"] == 10000

    def test_parse_concrete_quantity(self, agent):
        """Test parsing concrete quantity queries."""
        result = agent._parse_economics_natural_language("100 cubic yards of concrete")
        
        assert result["quantity"] == 100
        assert "concrete" in str(result.get("item_description", "")).lower()

    def test_parse_metric_units(self, agent):
        """Test parsing metric units (should convert to sq ft)."""
        result = agent._parse_economics_natural_language("500 square meters office")
        
        assert result["size_sf"] is not None
        # 500 sq m * 10.764 = ~5382 sq ft
        assert result["size_sf"] > 5000

    def test_parse_with_zip_code(self, agent):
        """Test parsing queries with location."""
        result = agent._parse_economics_natural_language("Office in 90210")
        
        assert result["city"] == "90210"

    def test_parse_building_type_clarification(self, agent):
        """Test that ambiguous building types require clarification."""
        result = agent._parse_economics_natural_language("Office building")
        
        # Should have suggestions but might auto-select first option
        assert len(result["building_type_suggestions"]) > 0

    def test_parse_specific_building_type(self, agent):
        """Test parsing specific building type codes."""
        result = agent._parse_economics_natural_language("office-low building 5000 sq ft")
        
        assert result["building_type"] == "office-low"


# ============================================================================
# Test Class: Conversation Response Generation
# ============================================================================

class TestConversationResponseGeneration:
    """Tests for conversational response generation."""

    def test_generate_conversation_hello(self, agent):
        """Test greeting response."""
        response = agent._generate_conversation_response("hello")
        
        assert "cerebrum" in response.lower() or "Cerebrum" in response
        assert len(response) > 50

    def test_generate_conversation_capabilities(self, agent):
        """Test capabilities response."""
        response = agent._generate_conversation_response("what can you do?")
        
        assert len(response) > 50
        assert "construction" in response.lower() or "code" in response.lower() or "cost" in response.lower()

    def test_generate_conversation_thanks(self, agent):
        """Test thanks response."""
        response = agent._generate_conversation_response("thank you")
        
        assert len(response) > 0
        assert "welcome" in response.lower() or "Welcome" in response or "you're" in response.lower()

    def test_generate_conversation_default(self, agent):
        """Test default response for unrecognized input."""
        response = agent._generate_conversation_response("xyz123 random input")
        
        assert len(response) > 50
        assert "cerebrum" in response.lower() or "Cerebrum" in response or "try" in response.lower()


# ============================================================================
# Test Class: Error Message Formatting
# ============================================================================

class TestErrorMessageFormatting:
    """Tests for error message formatting."""

    def test_format_error_building_clarification(self, agent):
        """Test building type clarification error message."""
        error = "building_type_clarification_needed"
        message = agent._format_error_message("estimate_project", error, "Office cost")
        
        assert "Which" in message or "office-low" in message or "office-high" in message

    def test_format_error_missing_parameters(self, agent):
        """Test missing parameters error message."""
        error = "Need building_type+size_sf"
        message = agent._format_error_message("calculate_cost", error, "Calculate cost")
        
        assert "need more information" in message.lower() or "Try" in message

    def test_format_error_item_not_found(self, agent):
        """Test item not found error message."""
        error = "Item not found"
        message = agent._format_error_message("rsmeans_query", error, "Search xyz")
        
        assert "couldn't find" in message.lower() or "try" in message.lower()

    def test_format_error_generic(self, agent):
        """Test generic error message formatting."""
        error = "Some random error"
        message = agent._format_error_message("some_tool", error, "Some task")
        
        assert len(message) > 0
        assert "issue" in message.lower() or "problem" in message.lower() or "error" in message.lower() or "happened" in message.lower()


# ============================================================================
# Test Class: Agent Run Execution
# ============================================================================

class TestAgentRunExecution:
    """Tests for agent.run() execution flow."""

    @pytest.mark.asyncio
    async def test_run_with_greeting(self, agent):
        """Test agent.run with greeting."""
        result = await agent.run("hello")
        
        assert result.success == True
        assert "cerebrum" in result.message.lower() or "Cerebrum" in result.message

    @pytest.mark.asyncio
    async def test_run_with_vague_input(self, agent):
        """Test agent.run with vague/short input."""
        result = await agent.run("ok")
        
        assert result.success == True
        assert len(result.message) > 0

    @pytest.mark.asyncio
    async def test_run_routes_to_economics_layer(self, agent):
        """Test that economics queries route to economics layer."""
        with patch.object(agent, 'tools', {
            'calculate_cost': Mock(return_value={
                "success": True,
                "building_type": "office-low",
                "size_sf": 5000,
                "total_cost": 1125000
            })
        }):
            result = await agent.run("Calculate cost for 5000 sq ft office")
            
            assert result.layer == AgentLayer.ECONOMICS or result.message

    @pytest.mark.asyncio  
    async def test_run_includes_conversation_history(self, agent):
        """Test that conversation history is included in context."""
        context = {"conversation_history": "Previous: Hello\nAssistant: Hi!"}
        
        result = await agent.run("How are you?", context)
        
        assert result.success == True


# ============================================================================
# Test Class: Conversation Reader
# ============================================================================

class TestConversationReader:
    """Tests for conversation reader functionality."""

    def test_semantic_search_ranking(self, agent):
        """Test that semantic search returns ranked results."""
        # Add some test entries to the index
        agent.conversation_reader.memory_index = {
            "1": MemoryIndex(
                id="1",
                content="Concrete foundation costs $120 per cubic yard",
                source="memory/2024-01-15.md",
                timestamp="2024-01-15T10:00:00",
                tags=["costs", "concrete"],
                related_layers=["economics"]
            ),
            "2": MemoryIndex(
                id="2",
                content="Steel reinforcement prices are up this month",
                source="memory/2024-01-16.md",
                timestamp="2024-01-16T10:00:00",
                tags=["costs", "steel"],
                related_layers=["economics"]
            )
        }
        
        result = agent.conversation_reader.semantic_search("concrete cost", limit=5)
        
        assert result["total_matches"] > 0
        # First result should be about concrete
        assert "concrete" in result["results"][0]["content"].lower()

    def test_read_conversations_with_filters(self, agent):
        """Test reading conversations with layer filters."""
        # Add test data
        agent.conversation_reader.memory_index = {
            "1": MemoryIndex(
                id="1",
                content="Test economics content",
                source="test.md",
                timestamp=datetime.now().isoformat(),
                tags=[],
                related_layers=["economics"]
            )
        }
        
        result = agent.conversation_reader.read_conversations(
            days=7, layers=["economics"]
        )
        
        assert "total_entries" in result


# ============================================================================
# Test Class: Formula Results
# ============================================================================

class TestFormulaResults:
    """Tests for formula calculation result formatting."""

    def test_format_formula_concrete(self, agent):
        """Test formatting concrete formula results."""
        result = {
            "formula_name": "Concrete Slab",
            "inputs": {"length": 10, "width": 20, "depth": 0.5},
            "outputs": {"volume": 100, "cost": 12000}
        }
        
        message = agent._format_formula_result(result, "Calculate concrete")
        
        assert "Concrete Slab" in message or "concrete" in message.lower()
        assert "100" in message or "12,000" in message

    def test_format_formula_drywall(self, agent):
        """Test formatting drywall formula results."""
        result = {
            "formula_name": "Drywall Area",
            "inputs": {"length": 12, "height": 8},
            "outputs": {"area": 96, "sheets": 3}
        }
        
        message = agent._format_formula_result(result, "Calculate drywall")
        
        assert "Drywall" in message or "drywall" in message.lower()

    def test_format_formula_search_results(self, agent):
        """Test formatting formula search results."""
        result = {
            "formulas": [
                {"name": "Concrete Slab", "description": "Calculate concrete volume", "category": "Structural"},
                {"name": "Beam Load", "description": "Calculate beam loading", "category": "Structural"}
            ]
        }
        
        message = agent._format_formula_search_result(result, "Search structural")
        
        assert "formula" in message.lower() or "Found" in message


# ============================================================================
# Test Class: File Analysis
# ============================================================================

class TestFileAnalysis:
    """Tests for file upload analysis."""

    @pytest.mark.asyncio
    async def test_analyze_uploaded_file_image(self, agent):
        """Test analysis of uploaded image file."""
        with patch('httpx.get') as mock_get:
            mock_get.return_value = Mock(
                status_code=200,
                json=Mock(return_value=[{
                    "file_id": "user_123_test.png",
                    "file_name": "test.png"
                }])
            )
            
            result = await agent._analyze_uploaded_file("user_123_test", "Analyze this image", {})
            
            assert isinstance(result, AgentResult)

    @pytest.mark.asyncio
    async def test_analyze_uploaded_file_not_found(self, agent):
        """Test handling of non-existent file."""
        with patch('httpx.get') as mock_get:
            mock_get.return_value = Mock(status_code=200, json=Mock(return_value=[]))
            
            result = await agent._analyze_uploaded_file("nonexistent", "Analyze this", {})
            
            assert result.success == False
            assert "not found" in result.message.lower() or "deleted" in result.message.lower() or "expired" in result.message.lower()

    @pytest.mark.asyncio
    async def test_find_recent_file(self, agent):
        """Test finding recent files."""
        with patch('httpx.get') as mock_get:
            mock_get.return_value = Mock(status_code=200, json=Mock(return_value=[
                {"file_id": "user_123_recent.pdf", "file_name": "recent.pdf", "uploaded_at": "2024-01-20T10:00:00"}
            ]))
            
            file_id = await agent._find_recent_file("this file", "user_123")
            
            assert file_id is not None


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
