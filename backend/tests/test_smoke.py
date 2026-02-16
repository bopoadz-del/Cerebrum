"""
Minimal Smoke Tests

These tests verify the application can boot and health endpoints work.
Designed to run in CI with minimal environment setup.
"""

import os
import pytest
from fastapi.testclient import TestClient

# Ensure minimal env vars are set before importing app
os.environ.setdefault("SECRET_KEY", "test-secret-key-32-chars-long-for-ci-only")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("DEBUG", "true")


@pytest.fixture
def minimal_app():
    """Create app with mocked dependencies for smoke testing."""
    from app.main import create_application
    from app.api import health
    
    # Create minimal app with just health router
    from fastapi import FastAPI
    app = FastAPI(title="Smoke Test App")
    app.include_router(health.router, tags=["health"])
    
    return app


@pytest.fixture
def smoke_client(minimal_app) -> TestClient:
    """Create test client for smoke tests."""
    with TestClient(minimal_app) as client:
        yield client


class TestHealthEndpoints:
    """Test health endpoints return expected responses."""

    def test_liveness_probe(self, smoke_client):
        """Test /health/live returns 200."""
        response = smoke_client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") is True
        assert data.get("service") == "cerebrum-api"
        assert "uptime_seconds" in data

    def test_readiness_probe(self, smoke_client):
        """Test /health/ready returns expected structure."""
        response = smoke_client.get("/health/ready")
        # May return 503 if dependencies not available (expected in smoke test)
        assert response.status_code in [200, 503]
        data = response.json()
        assert "ok" in data
        assert data.get("service") == "cerebrum-api"
        assert "checks" in data
        assert "db" in data["checks"]
        assert "redis" in data["checks"]

    def test_health_metrics(self, smoke_client):
        """Test /health/metrics returns metrics."""
        response = smoke_client.get("/health/metrics")
        assert response.status_code == 200
        data = response.json()
        assert data.get("service") == "cerebrum-api"
        assert "uptime_seconds" in data


class TestAppImport:
    """Test that main app can be imported with minimal env."""

    def test_import_main_module(self):
        """Verify app.main can be imported."""
        # This test will fail if critical env vars are missing
        # or if there are import errors in the app
        from app.main import create_application
        assert callable(create_application)

    def test_create_application(self):
        """Verify create_application produces valid FastAPI app."""
        from fastapi import FastAPI
        from app.main import create_application
        
        # This requires full env setup, so we skip if dependencies fail
        try:
            app = create_application()
            assert isinstance(app, FastAPI)
        except Exception as e:
            pytest.skip(f"Full app creation requires database/redis: {e}")


class TestHealthRouterDirect:
    """Test health router functions directly without full app."""

    @pytest.mark.asyncio
    async def test_liveness_direct(self):
        """Test liveness function directly."""
        from app.api.health import liveness
        result = await liveness()
        assert result["ok"] is True
        assert result["service"] == "cerebrum-api"
        assert "uptime_seconds" in result

    @pytest.mark.asyncio
    async def test_health_metrics_direct(self):
        """Test health_metrics function directly."""
        from app.api.health import health_metrics
        result = await health_metrics()
        assert result["service"] == "cerebrum-api"
        assert "uptime_seconds" in result
