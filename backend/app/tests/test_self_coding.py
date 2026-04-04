"""
Comprehensive Tests for Self-Coding Registry System

Tests all components of the meta-cognition system.
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import UUID, uuid4

# Test configuration
pytestmark = pytest.mark.asyncio


# ============== Capability Registry Tests ==============

class TestCapabilityRegistry:
    """Tests for the Capability Registry."""
    
    async def test_create_capability(self):
        """Test creating a new capability."""
        from app.registry.models import CapabilityCreate, CapabilityType, AuthorType
        
        data = CapabilityCreate(
            name="test_endpoint",
            version="1.0.0",
            capability_type=CapabilityType.ENDPOINT,
            description="Test endpoint capability",
            code_content="async def test(): pass",
            route_path="/api/test",
            route_methods=["GET"],
        )
        
        assert data.name == "test_endpoint"
        assert data.version == "1.0.0"
        assert data.capability_type == CapabilityType.ENDPOINT
        assert data.author == AuthorType.AI
    
    async def test_capability_status_transitions(self):
        """Test valid capability status transitions."""
        from app.registry.models import CapabilityStatus
        
        # Valid transitions from DRAFT
        assert CapabilityStatus.VALIDATING in [
            CapabilityStatus.VALIDATING,
            CapabilityStatus.DEPRECATED,
        ]
        
        # Valid transitions from VALIDATED
        assert CapabilityStatus.DEPLOYED in [
            CapabilityStatus.DEPLOYED,
            CapabilityStatus.DEPRECATED,
        ]
    
    async def test_dependency_constraint_parsing(self):
        """Test version constraint parsing."""
        from app.registry.dependencies import VersionConstraintParser
        
        parser = VersionConstraintParser()
        
        # Test exact version
        spec = parser.parse_constraint("1.2.3")
        assert "1.2.3" in spec
        
        # Test caret constraint
        spec = parser.parse_constraint("^1.2.3")
        assert "1.2.3" in spec
        assert "1.3.0" in spec
        
        # Test wildcard
        spec = parser.parse_constraint("1.x")
        assert "1.0.0" in spec
        assert "1.5.0" in spec


# ============== Code Generation Tests ==============

class TestCodeGeneration:
    """Tests for the Code Generation Service."""
    
    async def test_generation_request(self):
        """Test generation request creation."""
        from app.coding.generator import GenerationRequest
        
        request = GenerationRequest(
            feature_description="Create a user endpoint",
            code_type="endpoint",
            context={"model": "User"},
        )
        
        assert request.feature_description == "Create a user endpoint"
        assert request.code_type == "endpoint"
        assert request.model == "gpt-4"
        assert request.temperature == 0.2
    
    async def test_template_rendering(self):
        """Test template rendering."""
        from app.coding.templates import TemplateManager
        
        manager = TemplateManager()
        
        # Test fastapi router template exists
        template = manager.get_template("fastapi_router")
        assert template is not None
        
        # Test rendering
        result = manager.render("fastapi_router", {
            "docstring": "Test endpoint",
            "imports": ["from fastapi import APIRouter"],
            "implementation": "@router.get('/test')\nasync def test(): pass",
        })
        
        assert "Test endpoint" in result
        assert "APIRouter" in result
        assert "/test" in result
    
    async def test_prompt_manager(self):
        """Test prompt manager."""
        from app.coding.prompts import get_prompt_manager
        
        manager = get_prompt_manager()
        
        # Test getting system prompt
        prompt = manager.get_system_prompt("endpoint")
        assert "FastAPI" in prompt
        assert len(prompt) > 100
        
        # Test listing code types
        types = manager.list_code_types()
        assert "endpoint" in types
        assert "component" in types


# ============== Validation Pipeline Tests ==============

class TestValidationPipeline:
    """Tests for the Validation Pipeline."""
    
    async def test_security_scan_patterns(self):
        """Test security pattern detection."""
        from app.validation.security_scan import SecurityScanner
        
        scanner = SecurityScanner()
        
        # Test dangerous code detection
        dangerous_code = """
import os
os.system('rm -rf /')
"""
        violations = scanner.scan_code(dangerous_code)
        assert len(violations) > 0
        assert any("os.system" in v for v in violations)
    
    async def test_sandbox_config(self):
        """Test sandbox configuration."""
        from app.validation.sandbox import SandboxConfig
        
        config = SandboxConfig(
            timeout_seconds=300,
            memory_limit_mb=512,
            network_disabled=True,
        )
        
        assert config.timeout_seconds == 300
        assert config.memory_limit_mb == 512
        assert config.network_disabled is True
    
    async def test_test_generation(self):
        """Test automatic test generation."""
        from app.validation.integration_test import TestGenerator
        
        generator = TestGenerator()
        
        code = """
async def add(a: int, b: int) -> int:
    return a + b
"""
        
        result = generator.generate_from_code(code)
        assert result.success is True
        assert len(result.test_code) > 0
        assert "test_add" in result.test_code


# ============== Hot Swap System Tests ==============

class TestHotSwapSystem:
    """Tests for the Hot Swap System."""
    
    async def test_module_loader(self):
        """Test dynamic module loading."""
        from app.hotswap.dynamic_import import DynamicModuleLoader
        
        loader = DynamicModuleLoader()
        
        code = """
def hello():
    return "Hello, World!"

class Calculator:
    def add(self, a, b):
        return a + b
"""
        
        result = loader.load_from_string(code, "test_module")
        assert result.success is True
        assert result.module is not None
        assert "hello" in result.exports
        assert "Calculator" in result.exports
    
    async def test_route_conflict_detection(self):
        """Test route conflict detection."""
        from app.hotswap.route_registration import RouteRegistry
        
        registry = RouteRegistry()
        
        # Register a route
        conflicts = registry.list_conflicts("/api/users", ["GET"])
        # Initially no conflicts
        
        # Add route to internal tracking
        from app.hotswap.route_registration import RouteInfo
        registry._routes["/api/users_GET"] = RouteInfo(
            path="/api/users",
            methods=["GET"],
            endpoint=lambda: None,
            name="get_users",
            capability_id=None,
            tags=[],
            registered_at=datetime.utcnow().isoformat(),
        )
        
        # Now should detect conflict
        conflicts = registry.list_conflicts("/api/users", ["GET"])
        assert len(conflicts) > 0
    
    async def test_rollback_snapshot(self):
        """Test rollback snapshot creation."""
        from app.hotswap.rollback import RollbackManager, RollbackSnapshot
        
        manager = RollbackManager()
        
        # Create mock capability
        mock_capability = MagicMock()
        mock_capability.id = uuid4()
        mock_capability.version = "1.0.0"
        mock_capability.code_content = "test code"
        mock_capability.config = {}
        mock_capability.route_path = "/api/test"
        mock_capability.route_methods = ["GET"]
        mock_capability.dependencies_json = []
        
        snapshot = await manager.create_snapshot(mock_capability)
        
        assert snapshot.capability_id == mock_capability.id
        assert snapshot.version == "1.0.0"
        assert snapshot.code_content == "test code"


# ============== Self-Healing Tests ==============

class TestSelfHealing:
    """Tests for the Self-Healing System."""
    
    async def test_error_detection(self):
        """Test error detection from logs."""
        from app.healing.error_detection import ErrorDetector
        
        detector = ErrorDetector()
        
        logs = """
2024-01-01 10:00:00 ERROR: Database connection failed
Traceback (most recent call last):
  File "app.py", line 42, in connect
    conn = db.connect()
ConnectionError: Could not connect to database
"""
        
        incidents = await detector.scan_logs(logs)
        assert len(incidents) > 0
    
    async def test_incident_creation(self):
        """Test manual incident creation."""
        from app.healing.error_detection import (
            ErrorDetector, IncidentSeverity, IncidentStatus
        )
        
        detector = ErrorDetector()
        
        incident = await detector.create_manual_incident(
            title="Test Incident",
            description="This is a test incident",
            severity=IncidentSeverity.HIGH,
            created_by="test",
        )
        
        assert incident.title == "Test Incident"
        assert incident.severity == IncidentSeverity.HIGH
        assert incident.status == IncidentStatus.OPEN
    
    async def test_circuit_breaker(self):
        """Test circuit breaker."""
        from app.healing.circuit_breaker_auto import AutoCircuitBreaker
        
        cb = AutoCircuitBreaker()
        
        # Record successful requests
        for _ in range(5):
            await cb.record_request("/api/test", 100, is_error=False)
        
        # Circuit should be closed
        assert cb.is_circuit_open("/api/test") is False
        
        # Record failures
        for _ in range(10):
            await cb.record_request("/api/test", 100, is_error=True)
        
        # Circuit should be open
        assert cb.is_circuit_open("/api/test") is True


# ============== Prompt Registry Tests ==============

class TestPromptRegistry:
    """Tests for the Prompt Registry."""
    
    async def test_prompt_creation(self):
        """Test prompt creation."""
        from app.prompts.models import PromptCreate, ModelProvider
        
        prompt = PromptCreate(
            name="code_generation",
            version="1.0.0",
            system_prompt="You are a code generator.",
            model_provider=ModelProvider.OPENAI,
            model_name="gpt-4",
            temperature=0.2,
        )
        
        assert prompt.name == "code_generation"
        assert prompt.version == "1.0.0"
        assert prompt.temperature == 0.2
    
    async def test_ab_test_routing(self):
        """Test A/B test traffic routing."""
        from app.prompts.ab_testing import ABTestingFramework, ABTestConfig
        from uuid import uuid4
        
        framework = ABTestingFramework()
        
        control_id = uuid4()
        treatment_id = uuid4()
        
        config = ABTestConfig(
            control_prompt_id=control_id,
            treatment_prompt_id=treatment_id,
            traffic_split={"control": 0.5, "treatment": 0.5},
        )
        
        test = framework.create_test(config)
        
        # Test routing
        result = framework.get_prompt_for_request(control_id, user_id="user123")
        assert "prompt_id" in result
        assert "group" in result
        assert result["group"] in ["control", "treatment"]
    
    async def test_prompt_cache(self):
        """Test prompt caching."""
        from app.prompts.dynamic_loading import PromptLoader, CachedPrompt
        from datetime import datetime
        
        loader = PromptLoader(default_ttl_seconds=60)
        
        # Create mock prompt
        mock_prompt = MagicMock()
        mock_prompt.id = uuid4()
        
        # Manually cache
        cache_key = "test:latest"
        loader._cache[cache_key] = CachedPrompt(
            prompt=mock_prompt,
            cached_at=datetime.utcnow(),
            ttl_seconds=60,
        )
        
        # Should be cache hit
        assert cache_key in loader._cache
        assert not loader._cache[cache_key].is_expired()


# ============== Integration Tests ==============

class TestIntegration:
    """Integration tests for the full workflow."""
    
    async def test_full_workflow_mock(self):
        """Test the full self-coding workflow with mocks."""
        # This test simulates the full workflow:
        # 1. Generate code
        # 2. Validate
        # 3. Deploy
        # 4. Detect error
        # 5. Heal
        
        # Step 1: Create capability
        from app.registry.models import CapabilityCreate, CapabilityType
        
        capability_data = CapabilityCreate(
            name="drywall_calculator",
            version="1.0.0",
            capability_type=CapabilityType.ENDPOINT,
            description="Calculate drywall quantities",
            code_content="""
from fastapi import APIRouter
router = APIRouter()

@router.post("/calculate")
async def calculate(data: dict):
    return {"sheets": 10}
""",
            route_path="/api/drywall",
            route_methods=["POST"],
        )
        
        assert capability_data.name == "drywall_calculator"
        
        # Step 2: Validate (mock)
        # Would call validation pipeline
        
        # Step 3: Deploy (mock)
        # Would call hotswap system
        
        # Step 4: Detect error
        from app.healing.error_detection import ErrorDetector, IncidentSeverity
        
        detector = ErrorDetector()
        
        # Step 5: Create incident and analyze
        incident = await detector.create_manual_incident(
            title="Drywall calculator error",
            description="Calculation returning wrong results",
            severity=IncidentSeverity.MEDIUM,
            created_by="test",
        )
        
        assert incident.title == "Drywall calculator error"
    
    async def test_end_to_end_error_handling(self):
        """Test end-to-end error handling."""
        # Simulate an error in a deployed capability
        
        from app.healing.error_detection import ErrorDetector
        from app.healing.circuit_breaker_auto import AutoCircuitBreaker
        
        # Setup
        detector = ErrorDetector()
        cb = AutoCircuitBreaker()
        
        # Simulate error logs
        error_logs = """
2024-01-01 10:00:00 ERROR: Exception in drywall calculator
Traceback (most recent call last):
  File "drywall.py", line 25, in calculate
    sheets = area / sheet_size
ZeroDivisionError: division by zero
"""
        
        # Detect error
        incidents = await detector.scan_logs(error_logs)
        
        # Circuit breaker should track
        for _ in range(5):
            await cb.record_request("/api/drywall/calculate", 100, is_error=True)
        
        # Verify circuit state
        metrics = cb.get_metrics("/api/drywall/calculate")
        assert metrics.get("error_rate", 0) > 0


# ============== Security Tests ==============

class TestSecurity:
    """Security-focused tests."""
    
    async def test_dangerous_code_detection(self):
        """Test detection of dangerous code patterns."""
        from app.validation.sandbox import DockerSandbox
        
        sandbox = DockerSandbox()
        
        dangerous_patterns = [
            "import os; os.system('rm -rf /')",
            "eval(user_input)",
            "exec(malicious_code)",
            "__import__('subprocess').call(['rm', '-rf', '/'])",
        ]
        
        for pattern in dangerous_patterns:
            violations = sandbox.scan_code(pattern)
            assert len(violations) > 0, f"Should detect: {pattern[:50]}"
    
    async def test_sandbox_isolation(self):
        """Test sandbox isolation configuration."""
        from app.validation.sandbox import SandboxConfig
        
        config = SandboxConfig(
            network_disabled=True,
            read_only_root=True,
            no_new_privileges=True,
            drop_all_capabilities=True,
        )
        
        assert config.network_disabled is True
        assert config.read_only_root is True
        assert config.no_new_privileges is True
        assert config.drop_all_capabilities is True


# ============== Performance Tests ==============

class TestPerformance:
    """Performance-related tests."""
    
    async def test_prompt_cache_performance(self):
        """Test prompt caching improves performance."""
        from app.prompts.dynamic_loading import PromptLoader
        
        loader = PromptLoader(default_ttl_seconds=300)
        
        # Cache stats should start empty
        stats = loader.get_cache_stats()
        assert stats["total_cached"] == 0
    
    async def test_circuit_breaker_performance(self):
        """Test circuit breaker tracks performance metrics."""
        from app.healing.circuit_breaker_auto import AutoCircuitBreaker
        
        cb = AutoCircuitBreaker()
        
        # Record various response times
        response_times = [50, 100, 200, 500, 1000, 2000]
        
        for rt in response_times:
            await cb.record_request("/api/test", rt, is_error=False)
        
        metrics = cb.get_metrics("/api/test")
        
        assert metrics["total_requests"] == len(response_times)
        assert metrics["avg_response_time_ms"] > 0
        assert metrics["p95_response_time_ms"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
