"""
Unit Tests for Security Components

Tests for JWT, password hashing, MFA, and other security features.
"""

import pytest
from datetime import datetime, timedelta

from app.core.security.jwt import JWTManager, TokenPair
from app.core.security.password import PasswordManager
from app.core.security.mfa import MFAManager
from app.core.security.token_blacklist import TokenBlacklist


class TestJWTManager:
    """Tests for JWT manager."""
    
    @pytest.fixture
    def jwt_manager(self):
        """Create JWT manager for testing."""
        return JWTManager()
    
    def test_create_access_token(self, jwt_manager):
        """Test access token creation."""
        token = jwt_manager.create_access_token(
            user_id="test-user-id",
            tenant_id="test-tenant-id",
            roles=["user"],
        )
        
        assert token is not None
        assert isinstance(token, str)
    
    def test_create_refresh_token(self, jwt_manager):
        """Test refresh token creation."""
        token = jwt_manager.create_refresh_token(
            user_id="test-user-id",
            tenant_id="test-tenant-id",
        )
        
        assert token is not None
        assert isinstance(token, str)
    
    def test_create_token_pair(self, jwt_manager):
        """Test token pair creation."""
        tokens = jwt_manager.create_token_pair(
            user_id="test-user-id",
            tenant_id="test-tenant-id",
            roles=["user"],
        )
        
        assert isinstance(tokens, TokenPair)
        assert tokens.access_token is not None
        assert tokens.refresh_token is not None
        assert tokens.token_type == "bearer"
    
    def test_decode_token(self, jwt_manager):
        """Test token decoding."""
        token = jwt_manager.create_access_token(
            user_id="test-user-id",
            tenant_id="test-tenant-id",
        )
        
        payload = jwt_manager.decode_token(token)
        
        assert payload.sub == "test-user-id"
        assert payload.tenant_id == "test-tenant-id"
        assert payload.type == "access"
    
    def test_decode_invalid_token(self, jwt_manager):
        """Test decoding invalid token."""
        with pytest.raises(Exception):
            jwt_manager.decode_token("invalid-token")


class TestPasswordManager:
    """Tests for password manager."""
    
    @pytest.fixture
    def password_manager(self):
        """Create password manager for testing."""
        return PasswordManager()
    
    def test_hash_password(self, password_manager):
        """Test password hashing."""
        password = "TestPassword123!"
        hashed = password_manager.hash(password)
        
        assert hashed is not None
        assert hashed != password
        assert isinstance(hashed, str)
    
    def test_verify_password(self, password_manager):
        """Test password verification."""
        password = "TestPassword123!"
        hashed = password_manager.hash(password)
        
        assert password_manager.verify(password, hashed) is True
        assert password_manager.verify("wrong-password", hashed) is False
    
    def test_validate_password(self, password_manager):
        """Test password validation."""
        # Valid password
        is_valid, errors = password_manager.validate("TestPassword123!")
        assert is_valid is True
        assert len(errors) == 0
        
        # Too short
        is_valid, errors = password_manager.validate("Short1!")
        assert is_valid is False
        assert any("8 characters" in e for e in errors)
        
        # Missing uppercase
        is_valid, errors = password_manager.validate("testpassword123!")
        assert is_valid is False
        assert any("uppercase" in e for e in errors)
        
        # Missing digit
        is_valid, errors = password_manager.validate("TestPassword!")
        assert is_valid is False
        assert any("digit" in e for e in errors)
    
    def test_generate_password(self, password_manager):
        """Test password generation."""
        password = password_manager.generate_password(length=16)
        
        assert len(password) == 16
        
        # Validate generated password
        is_valid, errors = password_manager.validate(password)
        assert is_valid is True


class TestMFAManager:
    """Tests for MFA manager."""
    
    @pytest.fixture
    def mfa_manager(self):
        """Create MFA manager for testing."""
        return MFAManager()
    
    def test_generate_secret(self, mfa_manager):
        """Test MFA secret generation."""
        mfa_data = mfa_manager.generate_secret(
            user_id="test-user-id",
            email="test@example.com",
        )
        
        assert mfa_data.secret is not None
        assert mfa_data.uri is not None
        assert len(mfa_data.backup_codes) == 10
    
    def test_verify_token(self, mfa_manager):
        """Test token verification."""
        mfa_data = mfa_manager.generate_secret(
            user_id="test-user-id",
            email="test@example.com",
        )
        
        # Get current token
        token = mfa_manager.get_current_token(mfa_data.secret)
        
        # Verify token
        result = mfa_manager.verify_token(mfa_data.secret, token)
        assert result.valid is True
        
        # Verify invalid token
        result = mfa_manager.verify_token(mfa_data.secret, "000000")
        assert result.valid is False
    
    def test_verify_backup_code(self, mfa_manager):
        """Test backup code verification."""
        mfa_data = mfa_manager.generate_secret(
            user_id="test-user-id",
            email="test@example.com",
        )
        
        # Use first backup code
        backup_code = mfa_data.backup_codes[0]
        
        result = mfa_manager.verify_token(
            mfa_data.secret,
            backup_code,
            backup_codes=mfa_data.backup_codes,
        )
        assert result.valid is True


class TestTokenBlacklist:
    """Tests for token blacklist."""
    
    @pytest.mark.asyncio
    async def test_blacklist_token(self):
        """Test token blacklisting."""
        blacklist = TokenBlacklist()
        
        # Mock Redis
        class MockRedis:
            def __init__(self):
                self.data = {}
            
            async def setex(self, key, ttl, value):
                self.data[key] = value
            
            async def exists(self, key):
                return 1 if key in self.data else 0
        
        blacklist._redis = MockRedis()
        
        # Blacklist token
        expires_at = datetime.utcnow() + timedelta(hours=1)
        result = await blacklist.blacklist(
            jti="test-jti",
            expires_at=expires_at,
            user_id="test-user-id",
        )
        
        assert result is True
        
        # Check if blacklisted
        is_blacklisted = await blacklist.is_blacklisted("test-jti")
        assert is_blacklisted is True
