"""
Token Blacklist

Manages revoked tokens using Redis for distributed token invalidation.
Provides immediate token revocation capability.
"""

from datetime import datetime, timedelta
from typing import Optional

from redis.asyncio.client import Redis

from app.core.config import settings
from app.core.logging import get_logger
from app.db.redis import get_cache_redis

logger = get_logger(__name__)


class TokenBlacklistError(Exception):
    """Token blacklist error."""
    pass


class TokenBlacklist:
    """
    Token blacklist manager using Redis.
    
    Stores revoked token JTIs (JWT IDs) in Redis with automatic
    expiration matching token expiration.
    """
    
    KEY_PREFIX = "token:blacklist:"
    
    def __init__(self, redis_client: Optional[Redis] = None) -> None:
        """
        Initialize token blacklist.
        
        Args:
            redis_client: Redis client, uses cache Redis if not provided
        """
        self._redis = redis_client
    
    async def _get_redis(self) -> Redis:
        """Get Redis connection."""
        if self._redis is None:
            self._redis = get_cache_redis()
        return self._redis
    
    async def blacklist(
        self,
        jti: str,
        expires_at: datetime,
        user_id: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> bool:
        """
        Add token JTI to blacklist.
        
        Args:
            jti: Token JTI (JWT ID)
            expires_at: Token expiration time
            user_id: Optional user ID for tracking
            reason: Optional reason for blacklisting
            
        Returns:
            True if successfully blacklisted
        """
        try:
            redis = await self._get_redis()
            
            # Calculate TTL until token expiration
            ttl = int((expires_at - datetime.utcnow()).total_seconds())
            
            if ttl <= 0:
                # Token already expired, no need to blacklist
                logger.debug(f"Token already expired, skipping blacklist: {jti}")
                return True
            
            key = f"{self.KEY_PREFIX}{jti}"
            value = {
                "blacklisted_at": datetime.utcnow().isoformat(),
                "user_id": user_id,
                "reason": reason,
                "expires_at": expires_at.isoformat(),
            }
            
            # Store with TTL
            await redis.setex(key, ttl, str(value))
            
            logger.info(
                f"Token blacklisted",
                jti=jti,
                user_id=user_id,
                reason=reason,
                ttl_seconds=ttl,
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to blacklist token: {e}", jti=jti, error=str(e))
            return False
    
    async def is_blacklisted(self, jti: str) -> bool:
        """
        Check if token JTI is blacklisted.
        
        Args:
            jti: Token JTI (JWT ID)
            
        Returns:
            True if token is blacklisted
        """
        try:
            redis = await self._get_redis()
            key = f"{self.KEY_PREFIX}{jti}"
            
            exists = await redis.exists(key)
            return bool(exists)
            
        except Exception as e:
            logger.error(f"Failed to check blacklist: {e}", jti=jti, error=str(e))
            # Fail open - assume not blacklisted on error
            return False
    
    async def blacklist_user_tokens(
        self,
        user_id: str,
        reason: str = "user_logout",
    ) -> bool:
        """
        Blacklist all tokens for a user.
        
        Note: This requires tracking user tokens separately.
        
        Args:
            user_id: User ID
            reason: Reason for blacklisting
            
        Returns:
            True if successful
        """
        try:
            redis = await self._get_redis()
            
            # Store user token blacklist marker
            key = f"{self.KEY_PREFIX}user:{user_id}"
            ttl = int(timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS).total_seconds())
            
            await redis.setex(
                key,
                ttl,
                str({
                    "blacklisted_at": datetime.utcnow().isoformat(),
                    "reason": reason,
                }),
            )
            
            logger.info(
                f"User tokens blacklisted",
                user_id=user_id,
                reason=reason,
            )
            
            return True
            
        except Exception as e:
            logger.error(
                f"Failed to blacklist user tokens: {e}",
                user_id=user_id,
                error=str(e),
            )
            return False
    
    async def is_user_blacklisted(self, user_id: str) -> bool:
        """
        Check if user's tokens are blacklisted.
        
        Args:
            user_id: User ID
            
        Returns:
            True if user's tokens are blacklisted
        """
        try:
            redis = await self._get_redis()
            key = f"{self.KEY_PREFIX}user:{user_id}"
            
            exists = await redis.exists(key)
            return bool(exists)
            
        except Exception as e:
            logger.error(
                f"Failed to check user blacklist: {e}",
                user_id=user_id,
                error=str(e),
            )
            return False
    
    async def cleanup_expired(self) -> int:
        """
        Clean up expired blacklist entries.
        
        Note: Redis automatically removes expired keys,
        so this is mainly for logging/reporting.
        
        Returns:
            Number of entries checked (not removed)
        """
        try:
            redis = await self._get_redis()
            
            # Get all blacklist keys
            pattern = f"{self.KEY_PREFIX}*"
            keys = await redis.keys(pattern)
            
            logger.info(f"Blacklist cleanup: {len(keys)} entries found")
            
            return len(keys)
            
        except Exception as e:
            logger.error(f"Blacklist cleanup failed: {e}", error=str(e))
            return 0
    
    async def get_stats(self) -> dict:
        """
        Get blacklist statistics.
        
        Returns:
            Statistics dictionary
        """
        try:
            redis = await self._get_redis()
            
            pattern = f"{self.KEY_PREFIX}*"
            keys = await redis.keys(pattern)
            
            # Separate user and token blacklists
            user_blacklists = [k for k in keys if k.startswith(f"{self.KEY_PREFIX}user:")]
            token_blacklists = [k for k in keys if not k.startswith(f"{self.KEY_PREFIX}user:")]
            
            return {
                "total_entries": len(keys),
                "user_blacklists": len(user_blacklists),
                "token_blacklists": len(token_blacklists),
            }
            
        except Exception as e:
            logger.error(f"Failed to get blacklist stats: {e}", error=str(e))
            return {
                "total_entries": 0,
                "user_blacklists": 0,
                "token_blacklists": 0,
                "error": str(e),
            }


# Global token blacklist instance
token_blacklist = TokenBlacklist()


async def blacklist_token(
    jti: str,
    expires_at: datetime,
    user_id: Optional[str] = None,
    reason: Optional[str] = None,
) -> bool:
    """Blacklist token convenience function."""
    return await token_blacklist.blacklist(jti, expires_at, user_id, reason)


async def is_token_blacklisted(jti: str) -> bool:
    """Check if token is blacklisted convenience function."""
    return await token_blacklist.is_blacklisted(jti)
