"""
Redis Connection Management

Manages multiple Redis instances for different purposes:
- Cache (DB 0): Application caching
- Queue (DB 1): Background job queues
- Sessions (DB 2): User session storage
- Rate Limit (DB 3): Rate limiting counters
"""

from enum import IntEnum
from typing import Optional, Any
import json

import redis.asyncio as redis
from redis.asyncio.client import Redis
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RedisDatabase(IntEnum):
    """Redis database enumeration for different use cases."""
    CACHE = 0
    QUEUE = 1
    SESSIONS = 2
    RATE_LIMIT = 3


class RedisManager:
    """
    Manages Redis connections for multiple databases.
    
    Provides separate connection pools for cache, queue, sessions,
    and rate limiting to ensure isolation and optimal performance.
    """
    
    def __init__(self) -> None:
        """Initialize Redis manager."""
        self._connections: dict[RedisDatabase, Optional[Redis]] = {
            RedisDatabase.CACHE: None,
            RedisDatabase.QUEUE: None,
            RedisDatabase.SESSIONS: None,
            RedisDatabase.RATE_LIMIT: None,
        }
        
    async def initialize(self) -> None:
        """Initialize all Redis connections."""
        logger.info("Initializing Redis connections")
        
        for db in RedisDatabase:
            await self._connect(db)
            
        logger.info("Redis connections initialized")
    
    async def _connect(self, db: RedisDatabase) -> Redis:
        """
        Create connection to specific Redis database.
        
        Args:
            db: Redis database to connect to
            
        Returns:
            Redis client instance
        """
        try:
            connection = redis.from_url(
                settings.redis_url,
                db=db.value,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
                health_check_interval=30,
                max_connections=50,
            )
            
            # Verify connection
            await connection.ping()
            
            self._connections[db] = connection
            logger.debug(f"Redis connection established", database=db.name, db=db.value)
            
            return connection
            
        except RedisError as e:
            logger.error(f"Failed to connect to Redis", database=db.name, error=str(e))
            raise
    
    def get(self, db: RedisDatabase) -> Redis:
        """
        Get Redis connection for specific database.
        
        Args:
            db: Redis database to get connection for
            
        Returns:
            Redis client instance
            
        Raises:
            RuntimeError: If connection not initialized
        """
        connection = self._connections.get(db)
        if connection is None:
            raise RuntimeError(f"Redis connection for {db.name} not initialized")
        return connection
    
    async def close(self) -> None:
        """Close all Redis connections."""
        logger.info("Closing Redis connections")
        
        for db, connection in self._connections.items():
            if connection:
                await connection.close()
                logger.debug(f"Redis connection closed", database=db.name)
                
        self._connections = {db: None for db in RedisDatabase}
        logger.info("All Redis connections closed")
    
    async def health_check(self) -> dict[str, bool]:
        """
        Check health of all Redis connections.
        
        Returns:
            Dictionary of database names to health status
        """
        health = {}
        
        for db, connection in self._connections.items():
            try:
                if connection:
                    await connection.ping()
                    health[db.name] = True
                else:
                    health[db.name] = False
            except RedisError:
                health[db.name] = False
                
        return health


# Global Redis manager instance
redis_manager = RedisManager()


# Convenience functions for specific databases
def get_cache_redis() -> Redis:
    """Get Redis connection for caching (DB 0)."""
    return redis_manager.get(RedisDatabase.CACHE)


def get_queue_redis() -> Redis:
    """Get Redis connection for queues (DB 1)."""
    return redis_manager.get(RedisDatabase.QUEUE)


def get_session_redis() -> Redis:
    """Get Redis connection for sessions (DB 2)."""
    return redis_manager.get(RedisDatabase.SESSIONS)


def get_rate_limit_redis() -> Redis:
    """Get Redis connection for rate limiting (DB 3)."""
    return redis_manager.get(RedisDatabase.RATE_LIMIT)


class RedisCache:
    """
    High-level cache interface using Redis.
    
    Provides convenient methods for caching with automatic
    serialization and TTL support.
    """
    
    def __init__(self, redis_client: Optional[Redis] = None) -> None:
        """
        Initialize cache with Redis client.
        
        Args:
            redis_client: Redis client, uses cache Redis if not provided
        """
        self._redis = redis_client
    
    def _get_redis(self) -> Redis:
        """Get Redis client, initializing from manager if not provided."""
        if self._redis is None:
            self._redis = get_cache_redis()
        return self._redis
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        try:
            value = await self._get_redis().get(key)
            if value:
                return json.loads(value)
            return None
        except RedisError as e:
            logger.warning("Cache get failed", key=key, error=str(e))
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            
        Returns:
            True if successful
        """
        try:
            serialized = json.dumps(value, default=str)
            if ttl:
                await self._get_redis().setex(key, ttl, serialized)
            else:
                await self._get_redis().set(key, serialized)
            return True
        except RedisError as e:
            logger.warning("Cache set failed", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if successful
        """
        try:
            await self._get_redis().delete(key)
            return True
        except RedisError as e:
            logger.warning("Cache delete failed", key=key, error=str(e))
            return False
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists
        """
        try:
            return bool(await self._get_redis().exists(key))
        except RedisError:
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """
        Clear all keys matching pattern.
        
        Args:
            pattern: Key pattern (e.g., "user:*")
            
        Returns:
            Number of keys deleted
        """
        try:
            keys = await self._get_redis().keys(pattern)
            if keys:
                return await self._get_redis().delete(*keys)
            return 0
        except RedisError as e:
            logger.warning("Cache clear failed", pattern=pattern, error=str(e))
            return 0


class RedisQueue:
    """
    Redis-based queue implementation.
    
    Provides simple queue operations for background job processing.
    """
    
    def __init__(self, name: str, redis_client: Optional[Redis] = None) -> None:
        """
        Initialize queue.
        
        Args:
            name: Queue name
            redis_client: Redis client, uses queue Redis if not provided
        """
        self.name = name
        self._redis = redis_client
    
    def _get_redis(self) -> Redis:
        """Get Redis client, initializing from manager if not provided."""
        if self._redis is None:
            self._redis = get_queue_redis()
        return self._redis
    
    async def push(self, item: dict) -> bool:
        """
        Push item to queue.
        
        Args:
            item: Item to queue
            
        Returns:
            True if successful
        """
        try:
            await self._get_redis().lpush(self.name, json.dumps(item, default=str))
            return True
        except RedisError as e:
            logger.error("Queue push failed", queue=self.name, error=str(e))
            return False
    
    async def pop(self, timeout: int = 0) -> Optional[dict]:
        """
        Pop item from queue.
        
        Args:
            timeout: Blocking timeout in seconds (0 = non-blocking)
            
        Returns:
            Item or None if queue empty
        """
        try:
            if timeout > 0:
                result = await self._get_redis().brpop(self.name, timeout=timeout)
                if result:
                    return json.loads(result[1])
                return None
            else:
                result = await self._get_redis().rpop(self.name)
                if result:
                    return json.loads(result)
                return None
        except RedisError as e:
            logger.error("Queue pop failed", queue=self.name, error=str(e))
            return None
    
    async def length(self) -> int:
        """
        Get queue length.
        
        Returns:
            Number of items in queue
        """
        try:
            return await self._get_redis().llen(self.name)
        except RedisError:
            return 0


# Cache instance for general use
cache = RedisCache()
