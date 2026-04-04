"""
Pytest Configuration and Fixtures

Provides shared fixtures for all tests.
"""

import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.base_class import Base
from app.db.session import get_db_session
from app.main import create_application

# Test database URL
TEST_DATABASE_URL = settings.TEST_DATABASE_URL or "postgresql+asyncpg://test:test@localhost/test"


# =============================================================================
# Event Loop
# =============================================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Database Fixtures
# =============================================================================

@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True,
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Drop tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


# =============================================================================
# Application Fixtures
# =============================================================================

@pytest.fixture
def app(db_session) -> FastAPI:
    """Create test FastAPI application."""
    app = create_application()
    
    # Override database dependency
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db_session] = override_get_db
    
    return app


@pytest.fixture
def client(app) -> Generator[TestClient, None, None]:
    """Create test client."""
    with TestClient(app) as test_client:
        yield test_client


@pytest_asyncio.fixture
async def async_client(app) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


# =============================================================================
# User Fixtures
# =============================================================================

@pytest.fixture
def user_data():
    """Sample user data."""
    return {
        "email": "test@example.com",
        "password": "TestPassword123!",
        "full_name": "Test User",
    }


@pytest.fixture
def admin_data():
    """Sample admin user data."""
    return {
        "email": "admin@example.com",
        "password": "AdminPassword123!",
        "full_name": "Admin User",
        "role": "admin",
    }


# =============================================================================
# Authentication Fixtures
# =============================================================================

@pytest.fixture
def auth_headers():
    """Sample authentication headers."""
    return {"Authorization": "Bearer test-token"}


# =============================================================================
# Mock Fixtures
# =============================================================================

@pytest.fixture
def mock_redis(mocker):
    """Mock Redis client."""
    return mocker.patch("app.db.redis.redis_manager")


@pytest.fixture
def mock_sentry(mocker):
    """Mock Sentry SDK."""
    return mocker.patch("app.core.sentry.sentry_sdk")
