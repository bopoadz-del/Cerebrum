"""
JWT Authentication

Provides JWT token generation, validation, and refresh functionality.
Supports access tokens (15 min) and refresh tokens (7 days).
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TokenPair:
    """Access and refresh token pair."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900  # 15 minutes in seconds


@dataclass
class TokenPayload:
    """Decoded JWT payload."""
    sub: str  # Subject (user ID)
    jti: str  # JWT ID
    iat: datetime  # Issued at
    exp: datetime  # Expiration
    type: str  # Token type (access/refresh)
    tenant_id: Optional[str] = None
    roles: Optional[list] = None


class JWTError(Exception):
    """JWT-related error."""
    pass


class TokenExpiredError(JWTError):
    """Token has expired."""
    pass


class InvalidTokenError(JWTError):
    """Token is invalid."""
    pass


class JWTManager:
    """
    JWT token manager.
    
    Handles creation and validation of access and refresh tokens
    with configurable expiration times.
    """
    
    def __init__(self) -> None:
        """Initialize JWT manager with settings."""
        self.secret_key = settings.SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
        self.access_token_expire = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        self.refresh_token_expire = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    def create_access_token(
        self,
        user_id: str,
        tenant_id: Optional[str] = None,
        roles: Optional[list] = None,
        extra_claims: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create access token for user.
        
        Args:
            user_id: User ID (subject)
            tenant_id: Tenant ID for multi-tenancy
            roles: User roles
            extra_claims: Additional claims to include
            
        Returns:
            Encoded JWT access token
        """
        now = datetime.utcnow()
        jti = str(uuid.uuid4())
        
        payload = {
            "sub": str(user_id),
            "jti": jti,
            "iat": now,
            "exp": now + self.access_token_expire,
            "type": "access",
            "tenant_id": str(tenant_id) if tenant_id else None,
            "roles": roles or [],
        }
        
        if extra_claims:
            payload.update(extra_claims)
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        logger.debug(
            "Created access token",
            user_id=user_id,
            jti=jti,
            expires=now + self.access_token_expire,
        )
        
        return token
    
    def create_refresh_token(
        self,
        user_id: str,
        tenant_id: Optional[str] = None,
    ) -> str:
        """
        Create refresh token for user.
        
        Args:
            user_id: User ID (subject)
            tenant_id: Tenant ID for multi-tenancy
            
        Returns:
            Encoded JWT refresh token
        """
        now = datetime.utcnow()
        jti = str(uuid.uuid4())
        
        payload = {
            "sub": str(user_id),
            "jti": jti,
            "iat": now,
            "exp": now + self.refresh_token_expire,
            "type": "refresh",
            "tenant_id": str(tenant_id) if tenant_id else None,
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        logger.debug(
            "Created refresh token",
            user_id=user_id,
            jti=jti,
            expires=now + self.refresh_token_expire,
        )
        
        return token
    
    def create_token_pair(
        self,
        user_id: str,
        tenant_id: Optional[str] = None,
        roles: Optional[list] = None,
        extra_claims: Optional[Dict[str, Any]] = None,
    ) -> TokenPair:
        """
        Create both access and refresh tokens.
        
        Args:
            user_id: User ID
            tenant_id: Tenant ID
            roles: User roles
            extra_claims: Additional claims
            
        Returns:
            TokenPair with access and refresh tokens
        """
        access_token = self.create_access_token(
            user_id=user_id,
            tenant_id=tenant_id,
            roles=roles,
            extra_claims=extra_claims,
        )
        refresh_token = self.create_refresh_token(
            user_id=user_id,
            tenant_id=tenant_id,
        )
        
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=int(self.access_token_expire.total_seconds()),
        )
    
    def decode_token(
        self,
        token: str,
        token_type: Optional[str] = None,
    ) -> TokenPayload:
        """
        Decode and validate JWT token.
        
        Args:
            token: JWT token string
            token_type: Expected token type (access/refresh)
            
        Returns:
            Decoded token payload
            
        Raises:
            TokenExpiredError: If token has expired
            InvalidTokenError: If token is invalid
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
            )
            
            # Validate token type if specified
            if token_type and payload.get("type") != token_type:
                raise InvalidTokenError(
                    f"Invalid token type. Expected {token_type}, got {payload.get('type')}"
                )
            
            return TokenPayload(
                sub=payload["sub"],
                jti=payload["jti"],
                iat=datetime.fromtimestamp(payload["iat"]),
                exp=datetime.fromtimestamp(payload["exp"]),
                type=payload["type"],
                tenant_id=payload.get("tenant_id"),
                roles=payload.get("roles", []),
            )
            
        except ExpiredSignatureError as e:
            logger.warning("Token has expired")
            raise TokenExpiredError("Token has expired") from e
            
        except InvalidTokenError as e:
            logger.warning("Invalid token", error=str(e))
            raise InvalidTokenError(f"Invalid token: {e}") from e
    
    def get_token_expiry(self, token: str) -> Optional[datetime]:
        """
        Get token expiration time without full validation.
        
        Args:
            token: JWT token
            
        Returns:
            Expiration datetime or None
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False},
            )
            exp = payload.get("exp")
            return datetime.fromtimestamp(exp) if exp else None
        except Exception:
            return None
    
    def get_token_jti(self, token: str) -> Optional[str]:
        """
        Get token JTI (JWT ID) without full validation.
        
        Args:
            token: JWT token
            
        Returns:
            JTI string or None
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False},
            )
            return payload.get("jti")
        except Exception:
            return None
    
    def refresh_access_token(
        self,
        refresh_token: str,
        user_id: str,
        tenant_id: Optional[str] = None,
        roles: Optional[list] = None,
    ) -> str:
        """
        Create new access token using valid refresh token.
        
        Args:
            refresh_token: Valid refresh token
            user_id: User ID
            tenant_id: Tenant ID
            roles: User roles
            
        Returns:
            New access token
            
        Raises:
            TokenExpiredError: If refresh token has expired
            InvalidTokenError: If refresh token is invalid
        """
        # Validate refresh token
        payload = self.decode_token(refresh_token, token_type="refresh")
        
        # Create new access token
        return self.create_access_token(
            user_id=user_id,
            tenant_id=tenant_id or payload.tenant_id,
            roles=roles,
        )


# Global JWT manager instance
jwt_manager = JWTManager()


def create_access_token(
    user_id: str,
    tenant_id: Optional[str] = None,
    roles: Optional[list] = None,
) -> str:
    """Create access token convenience function."""
    return jwt_manager.create_access_token(user_id, tenant_id, roles)


def create_refresh_token(user_id: str, tenant_id: Optional[str] = None) -> str:
    """Create refresh token convenience function."""
    return jwt_manager.create_refresh_token(user_id, tenant_id)


def decode_token(token: str, token_type: Optional[str] = None) -> TokenPayload:
    """Decode token convenience function."""
    return jwt_manager.decode_token(token, token_type)
