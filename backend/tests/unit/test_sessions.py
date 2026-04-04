"""
Unit Tests for Conversation Session Service

Tests run using SQLite in-memory database (no Postgres/Redis required).
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.conversation_session import ConversationSession
from app.services.session_service import (
    SessionService,
    generate_session_token,
    calculate_capacity_percent,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
async def async_engine():
    """Create in-memory SQLite engine for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )
    
    # Create tables
    from app.db.base_class import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    await engine.dispose()


@pytest.fixture
async def db_session(async_engine):
    """Create database session for testing."""
    async_session = sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def session_service(db_session):
    """Create session service with test database."""
    return SessionService(db_session)


@pytest.fixture
def user_id():
    """Sample user ID."""
    return str(uuid4())


# =============================================================================
# Token Generation Tests
# =============================================================================

class TestTokenGeneration:
    """Tests for session token generation."""

    def test_generate_session_token(self):
        """Test that tokens are generated and are unique."""
        token1 = generate_session_token()
        token2 = generate_session_token()
        
        assert token1 != token2
        assert len(token1) >= 32
        assert len(token2) >= 32


# =============================================================================
# Capacity Calculation Tests
# =============================================================================

class TestCapacityCalculation:
    """Tests for capacity calculation logic."""

    def test_calculate_capacity_zero_messages(self):
        """Test capacity with zero messages."""
        assert calculate_capacity_percent(0) == 0

    def test_calculate_capacity_message_based(self):
        """Test capacity based on message count."""
        # 10 messages = 10% capacity (baseline proxy)
        assert calculate_capacity_percent(10) == 10
        
        # 50 messages = 50% capacity
        assert calculate_capacity_percent(50) == 50
        
        # 100 messages = 100% capacity (capped)
        assert calculate_capacity_percent(100) == 100
        
        # 200 messages = 100% capacity (still capped)
        assert calculate_capacity_percent(200) == 100

    def test_calculate_capacity_with_tokens(self):
        """Test capacity with actual token count."""
        # 1000 tokens in 4000 context window = 25%
        assert calculate_capacity_percent(0, 1000) == 25
        
        # 4000 tokens = 100%
        assert calculate_capacity_percent(0, 4000) == 100
        
        # 8000 tokens = 100% (capped)
        assert calculate_capacity_percent(0, 8000) == 100

    def test_calculate_capacity_clamped(self):
        """Test capacity is clamped to 0-100 range."""
        assert calculate_capacity_percent(-10) == 0
        assert calculate_capacity_percent(1000) == 100


# =============================================================================
# Session Service Tests
# =============================================================================

class TestSessionService:
    """Tests for SessionService."""

    @pytest.mark.asyncio
    async def test_create_session(self, session_service, user_id):
        """Test creating a new session."""
        session = await session_service.create_session(
            user_id=user_id,
            title="Test Session",
            ttl_hours=24,
        )
        
        assert session is not None
        assert session.user_id == user_id
        assert session.title == "Test Session"
        assert session.session_token is not None
        assert len(session.session_token) >= 32
        assert session.capacity_percent == 0
        assert session.message_count == 0
        assert session.is_active is True

    @pytest.mark.asyncio
    async def test_create_session_default_title(self, session_service, user_id):
        """Test creating session without title."""
        session = await session_service.create_session(user_id=user_id)
        
        assert session.title is None
        assert session.is_active is True

    @pytest.mark.asyncio
    async def test_create_session_ttl_clamped(self, session_service, user_id):
        """Test that TTL is clamped to max."""
        session = await session_service.create_session(
            user_id=user_id,
            ttl_hours=1000,  # Exceeds max
        )
        
        # Should be clamped to 168 hours (7 days)
        max_expires = datetime.utcnow() + timedelta(hours=168)
        assert session.expires_at <= max_expires

    @pytest.mark.asyncio
    async def test_get_session_by_token(self, session_service, user_id):
        """Test retrieving session by token."""
        created = await session_service.create_session(user_id=user_id)
        
        retrieved = await session_service.get_session_by_token(created.session_token)
        
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.session_token == created.session_token

    @pytest.mark.asyncio
    async def test_get_session_by_token_not_found(self, session_service):
        """Test retrieving non-existent session."""
        retrieved = await session_service.get_session_by_token("invalid-token")
        
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_get_session_by_token_expired(self, session_service, user_id):
        """Test that expired sessions are not returned by default."""
        # Create session with very short TTL
        session = await session_service.create_session(
            user_id=user_id,
            ttl_hours=-1,  # Already expired
        )
        
        # Should not be returned with check_active=True (default)
        retrieved = await session_service.get_session_by_token(session.session_token)
        assert retrieved is None
        
        # Should be returned with check_active=False
        retrieved = await session_service.get_session_by_token(
            session.session_token,
            check_active=False,
        )
        assert retrieved is not None
        assert retrieved.id == session.id

    @pytest.mark.asyncio
    async def test_get_user_sessions(self, session_service, user_id):
        """Test listing user sessions."""
        # Create multiple sessions
        await session_service.create_session(user_id=user_id, title="Session 1")
        await session_service.create_session(user_id=user_id, title="Session 2")
        
        # Create session for different user
        other_user = str(uuid4())
        await session_service.create_session(user_id=other_user, title="Other Session")
        
        sessions = await session_service.get_user_sessions(user_id)
        
        assert len(sessions) == 2
        assert all(s.user_id == user_id for s in sessions)

    @pytest.mark.asyncio
    async def test_update_capacity(self, session_service, user_id):
        """Test updating session capacity."""
        session = await session_service.create_session(user_id=user_id)
        
        updated = await session_service.update_capacity(
            session.session_token,
            capacity_percent=50,
        )
        
        assert updated is not None
        assert updated.capacity_percent == 50

    @pytest.mark.asyncio
    async def test_update_capacity_clamped(self, session_service, user_id):
        """Test that capacity is clamped to 0-100."""
        session = await session_service.create_session(user_id=user_id)
        
        updated = await session_service.update_capacity(
            session.session_token,
            capacity_percent=150,  # Should clamp to 100
        )
        
        assert updated.capacity_percent == 100
        
        updated = await session_service.update_capacity(
            session.session_token,
            capacity_percent=-10,  # Should clamp to 0
        )
        
        assert updated.capacity_percent == 0

    @pytest.mark.asyncio
    async def test_increment_message_count(self, session_service, user_id):
        """Test incrementing message count."""
        session = await session_service.create_session(user_id=user_id)
        
        # Add messages
        for _ in range(5):
            updated = await session_service.increment_message_count(session.session_token)
        
        assert updated is not None
        assert updated.message_count == 5
        # Capacity should be calculated based on message count
        assert updated.capacity_percent > 0

    @pytest.mark.asyncio
    async def test_deactivate_session(self, session_service, user_id):
        """Test deactivating a session."""
        session = await session_service.create_session(user_id=user_id)
        
        success = await session_service.deactivate_session(session.session_token)
        
        assert success is True
        
        # Should not appear in active sessions
        retrieved = await session_service.get_session_by_token(session.session_token)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_deactivate_session_not_found(self, session_service):
        """Test deactivating non-existent session."""
        success = await session_service.deactivate_session("invalid-token")
        
        assert success is False

    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self, session_service, user_id):
        """Test cleaning up expired sessions."""
        # Create expired session
        expired = await session_service.create_session(
            user_id=user_id,
            ttl_hours=-1,
        )
        
        # Create active session
        active = await session_service.create_session(
            user_id=user_id,
            ttl_hours=24,
        )
        
        # Cleanup
        count = await session_service.cleanup_expired_sessions()
        
        assert count == 1
        
        # Verify expired is now inactive
        expired_session = await session_service.get_session_by_token(
            expired.session_token,
            check_active=False,
        )
        assert expired_session.is_active is False
        
        # Verify active is still active
        active_session = await session_service.get_session_by_token(active.session_token)
        assert active_session is not None
        assert active_session.is_active is True


# =============================================================================
# Model Tests
# =============================================================================

class TestConversationSessionModel:
    """Tests for ConversationSession model."""

    def test_is_expired(self):
        """Test expiration check."""
        session = ConversationSession(
            user_id=uuid4(),
            session_token="test-token",
            expires_at=datetime.utcnow() - timedelta(hours=1),  # Expired
        )
        
        assert session.is_expired() is True
        
        session.expires_at = datetime.utcnow() + timedelta(hours=1)  # Not expired
        assert session.is_expired() is False

    def test_touch(self):
        """Test updating last activity."""
        old_time = datetime.utcnow() - timedelta(hours=1)
        session = ConversationSession(
            user_id=uuid4(),
            session_token="test-token",
            last_activity_at=old_time,
            expires_at=datetime.utcnow() + timedelta(hours=24),
        )
        
        session.touch()
        
        assert session.last_activity_at > old_time

    def test_to_dict(self):
        """Test serialization to dict."""
        session = ConversationSession(
            id=uuid4(),
            user_id=uuid4(),
            session_token="test-token",
            title="Test Session",
            capacity_percent=50,
            message_count=10,
            is_active=True,
            last_activity_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24),
            created_at=datetime.utcnow(),
        )
        
        data = session.to_dict()
        
        assert data["session_token"] == "test-token"
        assert data["title"] == "Test Session"
        assert data["capacity_percent"] == 50
        assert data["is_expired"] is False
        assert "id" in data
        assert "user_id" in data
