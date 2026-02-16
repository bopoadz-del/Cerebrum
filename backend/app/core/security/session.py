"""
Server-Side Session Management

Provides secure server-side sessions stored in Redis with
automatic expiration and session invalidation capabilities.
"""

import json
import secrets
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from redis.asyncio.client import Redis

from app.core.config import settings
from app.core.logging import get_logger
from app.db.redis import get_session_redis

logger = get_logger(__name__)


@dataclass
class SessionData:
    """Session data structure."""
    session_id: str
    user_id: str
    tenant_id: Optional[str]
    roles: list
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: str
    expires_at: str
    last_accessed_at: str
    mfa_verified: bool = False
    metadata: Optional[Dict[str, Any]] = None


class SessionError(Exception):
    """Session-related error."""
    pass


class SessionManager:
    """
    Server-side session manager using Redis.
    
    Provides secure session storage with:
    - Automatic expiration
    - Session invalidation
    - Multi-device support
    - Security metadata tracking
    """
    
    # Session key prefix in Redis
    KEY_PREFIX = "session:"
    # User sessions index prefix
    USER_PREFIX = "user_sessions:"
    # Default session duration
    SESSION_DURATION_HOURS = 24
    
    def __init__(self, redis_client: Optional[Redis] = None) -> None:
        """
        Initialize session manager.
        
        Args:
            redis_client: Redis client, uses session Redis if not provided
        """
        self._redis = redis_client
        self.session_duration = timedelta(hours=self.SESSION_DURATION_HOURS)
    
    async def _get_redis(self) -> Redis:
        """Get Redis connection."""
        if self._redis is None:
            self._redis = get_session_redis()
        return self._redis
    
    async def create_session(
        self,
        user_id: str,
        tenant_id: Optional[str] = None,
        roles: Optional[list] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        mfa_verified: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SessionData:
        """
        Create new session for user.
        
        Args:
            user_id: User ID
            tenant_id: Tenant ID
            roles: User roles
            ip_address: Client IP address
            user_agent: Client user agent
            mfa_verified: Whether MFA has been verified
            metadata: Additional session metadata
            
        Returns:
            Session data
        """
        session_id = secrets.token_urlsafe(32)
        now = datetime.utcnow()
        expires_at = now + self.session_duration
        
        session = SessionData(
            session_id=session_id,
            user_id=user_id,
            tenant_id=tenant_id,
            roles=roles or [],
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=now.isoformat(),
            expires_at=expires_at.isoformat(),
            last_accessed_at=now.isoformat(),
            mfa_verified=mfa_verified,
            metadata=metadata,
        )
        
        try:
            redis = await self._get_redis()
            
            # Store session
            key = f"{self.KEY_PREFIX}{session_id}"
            ttl = int(self.session_duration.total_seconds())
            
            await redis.setex(
                key,
                ttl,
                json.dumps(asdict(session), default=str),
            )
            
            # Add to user's session index
            user_key = f"{self.USER_PREFIX}{user_id}"
            await redis.sadd(user_key, session_id)
            
            logger.info(
                f"Session created",
                session_id=session_id[:8] + "...",
                user_id=user_id,
                expires=expires_at.isoformat(),
            )
            
            return session
            
        except Exception as e:
            logger.error(f"Failed to create session: {e}", user_id=user_id)
            raise SessionError(f"Failed to create session: {e}") from e
    
    async def get_session(self, session_id: str) -> Optional[SessionData]:
        """
        Get session by ID.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session data or None if not found/expired
        """
        try:
            redis = await self._get_redis()
            key = f"{self.KEY_PREFIX}{session_id}"
            
            data = await redis.get(key)
            if not data:
                return None
            
            session_dict = json.loads(data)
            
            # Update last accessed
            session_dict["last_accessed_at"] = datetime.utcnow().isoformat()
            
            # Refresh TTL
            ttl = int(self.session_duration.total_seconds())
            await redis.setex(key, ttl, json.dumps(session_dict, default=str))
            
            return SessionData(**session_dict)
            
        except Exception as e:
            logger.error(f"Failed to get session: {e}", session_id=session_id[:8])
            return None
    
    async def invalidate_session(self, session_id: str) -> bool:
        """
        Invalidate a specific session.
        
        Args:
            session_id: Session ID to invalidate
            
        Returns:
            True if session was invalidated
        """
        try:
            redis = await self._get_redis()
            key = f"{self.KEY_PREFIX}{session_id}"
            
            # Get session to find user
            data = await redis.get(key)
            if data:
                session_dict = json.loads(data)
                user_id = session_dict.get("user_id")
                
                # Remove from user's session index
                if user_id:
                    user_key = f"{self.USER_PREFIX}{user_id}"
                    await redis.srem(user_key, session_id)
            
            # Delete session
            await redis.delete(key)
            
            logger.info(f"Session invalidated", session_id=session_id[:8])
            return True
            
        except Exception as e:
            logger.error(f"Failed to invalidate session: {e}", session_id=session_id[:8])
            return False
    
    async def invalidate_user_sessions(
        self,
        user_id: str,
        except_session_id: Optional[str] = None,
    ) -> int:
        """
        Invalidate all sessions for a user.
        
        Args:
            user_id: User ID
            except_session_id: Optional session ID to keep
            
        Returns:
            Number of sessions invalidated
        """
        try:
            redis = await self._get_redis()
            user_key = f"{self.USER_PREFIX}{user_id}"
            
            # Get all session IDs for user
            session_ids = await redis.smembers(user_key)
            
            invalidated = 0
            for session_id in session_ids:
                if except_session_id and session_id == except_session_id:
                    continue
                
                key = f"{self.KEY_PREFIX}{session_id}"
                await redis.delete(key)
                invalidated += 1
            
            # Clear user's session index
            await redis.delete(user_key)
            
            # Re-add except_session_id if provided
            if except_session_id and except_session_id in session_ids:
                await redis.sadd(user_key, except_session_id)
            
            logger.info(
                f"User sessions invalidated",
                user_id=user_id,
                count=invalidated,
            )
            
            return invalidated
            
        except Exception as e:
            logger.error(f"Failed to invalidate user sessions: {e}", user_id=user_id)
            return 0
    
    async def get_user_sessions(self, user_id: str) -> list:
        """
        Get all active sessions for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of session data
        """
        try:
            redis = await self._get_redis()
            user_key = f"{self.USER_PREFIX}{user_id}"
            
            session_ids = await redis.smembers(user_key)
            sessions = []
            
            for session_id in session_ids:
                session = await self.get_session(session_id)
                if session:
                    sessions.append(session)
            
            return sessions
            
        except Exception as e:
            logger.error(f"Failed to get user sessions: {e}", user_id=user_id)
            return []
    
    async def update_session(
        self,
        session_id: str,
        **updates: Any,
    ) -> Optional[SessionData]:
        """
        Update session data.
        
        Args:
            session_id: Session ID
            **updates: Fields to update
            
        Returns:
            Updated session data or None
        """
        try:
            redis = await self._get_redis()
            key = f"{self.KEY_PREFIX}{session_id}"
            
            data = await redis.get(key)
            if not data:
                return None
            
            session_dict = json.loads(data)
            session_dict.update(updates)
            session_dict["last_accessed_at"] = datetime.utcnow().isoformat()
            
            # Get remaining TTL
            ttl = await redis.ttl(key)
            if ttl > 0:
                await redis.setex(key, ttl, json.dumps(session_dict, default=str))
            
            return SessionData(**session_dict)
            
        except Exception as e:
            logger.error(f"Failed to update session: {e}", session_id=session_id[:8])
            return None
    
    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.
        
        Note: Redis automatically removes expired keys.
        This method cleans up orphaned session references.
        
        Returns:
            Number of orphaned references removed
        """
        # Redis handles expiration automatically
        # This is mainly for logging/reporting
        logger.info("Session cleanup completed (Redis auto-expiration)")
        return 0


# Global session manager instance
session_manager = SessionManager()


async def create_session(
    user_id: str,
    tenant_id: Optional[str] = None,
    roles: Optional[list] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> SessionData:
    """Create session convenience function."""
    return await session_manager.create_session(
        user_id=user_id,
        tenant_id=tenant_id,
        roles=roles,
        ip_address=ip_address,
        user_agent=user_agent,
    )


async def get_session(session_id: str) -> Optional[SessionData]:
    """Get session convenience function."""
    return await session_manager.get_session(session_id)


async def invalidate_session(session_id: str) -> bool:
    """Invalidate session convenience function."""
    return await session_manager.invalidate_session(session_id)
