"""
Unit Tests for Database Models

Tests for User, AuditLog, and other models.
"""

import pytest
from datetime import datetime, timedelta

from app.models.user import User, Role
from app.models.audit import AuditLog


class TestUserModel:
    """Tests for User model."""
    
    def test_user_creation(self):
        """Test user creation."""
        user = User(
            email="test@example.com",
            hashed_password="hashed_password",
            full_name="Test User",
            role="user",
        )
        
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.role == "user"
        assert user.is_active is True
    
    def test_user_is_locked(self):
        """Test account lock check."""
        user = User(email="test@example.com", hashed_password="hash")
        
        # Not locked initially
        assert user.is_locked is False
        
        # Lock account
        user.locked_until = datetime.utcnow() + timedelta(minutes=30)
        assert user.is_locked is True
        
        # Unlock account
        user.locked_until = datetime.utcnow() - timedelta(minutes=1)
        assert user.is_locked is False
    
    def test_user_can_login(self):
        """Test login permission check."""
        user = User(email="test@example.com", hashed_password="hash")
        
        # Can login by default
        assert user.can_login is True
        
        # Cannot login if inactive
        user.is_active = False
        assert user.can_login is False
        user.is_active = True
        
        # Cannot login if locked
        user.locked_until = datetime.utcnow() + timedelta(minutes=30)
        assert user.can_login is False
    
    def test_record_login(self):
        """Test login recording."""
        user = User(email="test@example.com", hashed_password="hash")
        user.failed_login_attempts = 3
        user.locked_until = datetime.utcnow() + timedelta(minutes=30)
        
        user.record_login(ip_address="192.168.1.1")
        
        assert user.last_login_at is not None
        assert user.last_login_ip == "192.168.1.1"
        assert user.failed_login_attempts == 0
        assert user.locked_until is None
    
    def test_record_failed_login(self):
        """Test failed login recording."""
        user = User(email="test@example.com", hashed_password="hash")
        
        # Record failed attempts
        for _ in range(5):
            user.record_failed_login(max_attempts=5)
        
        assert user.failed_login_attempts == 5
        assert user.locked_until is not None
    
    def test_to_dict(self):
        """Test user serialization."""
        user = User(
            email="test@example.com",
            hashed_password="hash",
            full_name="Test User",
        )
        
        data = user.to_dict()
        
        assert "id" in data
        assert data["email"] == "test@example.com"
        assert data["full_name"] == "Test User"
        assert "hashed_password" not in data  # Should not include password


class TestRoleModel:
    """Tests for Role model."""
    
    def test_role_creation(self):
        """Test role creation."""
        role = Role(
            name="admin",
            description="Administrator role",
            permissions=["users:read", "users:write"],
        )
        
        assert role.name == "admin"
        assert role.description == "Administrator role"
        assert "users:read" in role.permissions


class TestAuditLogModel:
    """Tests for AuditLog model."""
    
    def test_audit_log_creation(self):
        """Test audit log creation."""
        log = AuditLog(
            action="user_login",
            resource_type="user",
            resource_id="test-user-id",
            details={"ip": "192.168.1.1"},
        )
        
        assert log.action == "user_login"
        assert log.resource_type == "user"
        assert log.resource_id == "test-user-id"
    
    def test_calculate_hash(self):
        """Test hash calculation."""
        timestamp = datetime.utcnow()
        
        hash1 = AuditLog.calculate_hash(
            timestamp=timestamp,
            user_id=None,
            action="test",
            resource_type="user",
            resource_id="123",
            details=None,
            previous_hash=None,
        )
        
        hash2 = AuditLog.calculate_hash(
            timestamp=timestamp,
            user_id=None,
            action="test",
            resource_type="user",
            resource_id="123",
            details=None,
            previous_hash=None,
        )
        
        # Same inputs should produce same hash
        assert hash1 == hash2
        
        # Different inputs should produce different hash
        hash3 = AuditLog.calculate_hash(
            timestamp=timestamp,
            user_id=None,
            action="different",
            resource_type="user",
            resource_id="123",
            details=None,
            previous_hash=None,
        )
        
        assert hash1 != hash3
