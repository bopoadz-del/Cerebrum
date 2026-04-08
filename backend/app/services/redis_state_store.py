"""
Redis State Store Service

Uses Redis for:
- Caching search results
- Task progress tracking
- Rate limiting
- Session state
- Feature flags
"""

import json
import os
from typing import Any, Dict, Optional, List
from datetime import datetime, timedelta
import redis.asyncio as redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

class RedisStateStore:
    """
    Redis-backed state store for caching and progress tracking.
    """
    
    def __init__(self, redis_url: str = None):
        self._redis_url = redis_url or REDIS_URL
        self._client = None
        self._available = False
    
    async def connect(self):
        """Initialize Redis connection."""
        try:
            self._client = redis.from_url(
                self._redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            await self._client.ping()
            self._available = True
        except Exception as e:
            print(f"Redis connection failed: {e}")
            self._available = False
    
    async def disconnect(self):
        """Close Redis connection."""
        if self._client:
            await self._client.close()
    
    # =========================================================================
    # SEARCH RESULT CACHING
    # =========================================================================
    
    async def cache_search_results(
        self,
        query: str,
        user_id: str,
        results: List[Dict],
        ttl_seconds: int = 300  # 5 minutes
    ) -> bool:
        """Cache search results for faster repeat queries."""
        if not self._available:
            return False
        
        try:
            cache_key = f"search:{user_id}:{hash(query) % 1000000}"
            data = {
                "query": query,
                "results": results,
                "cached_at": datetime.utcnow().isoformat(),
                "count": len(results)
            }
            await self._client.setex(
                cache_key,
                ttl_seconds,
                json.dumps(data)
            )
            return True
        except Exception as e:
            print(f"Cache write failed: {e}")
            return False
    
    async def get_cached_search(
        self,
        query: str,
        user_id: str
    ) -> Optional[Dict]:
        """Get cached search results if available."""
        if not self._available:
            return None
        
        try:
            cache_key = f"search:{user_id}:{hash(query) % 1000000}"
            data = await self._client.get(cache_key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            print(f"Cache read failed: {e}")
            return None
    
    async def invalidate_search_cache(self, user_id: str) -> bool:
        """Invalidate all search cache for a user (after new upload)."""
        if not self._available:
            return False
        
        try:
            pattern = f"search:{user_id}:*"
            keys = await self._client.keys(pattern)
            if keys:
                await self._client.delete(*keys)
            return True
        except Exception as e:
            print(f"Cache invalidation failed: {e}")
            return False
    
    # =========================================================================
    # TASK PROGRESS TRACKING
    # =========================================================================
    
    async def set_task_progress(
        self,
        task_id: str,
        progress: int,  # 0-100
        status: str,    # pending, running, completed, failed
        message: str = "",
        result: Any = None
    ) -> bool:
        """Update task progress."""
        if not self._available:
            return False
        
        try:
            key = f"task:{task_id}"
            data = {
                "task_id": task_id,
                "progress": progress,
                "status": status,
                "message": message,
                "result": result,
                "updated_at": datetime.utcnow().isoformat()
            }
            # Store for 24 hours
            await self._client.setex(key, 86400, json.dumps(data))
            return True
        except Exception as e:
            print(f"Task progress update failed: {e}")
            return False
    
    async def get_task_progress(self, task_id: str) -> Optional[Dict]:
        """Get task progress."""
        if not self._available:
            return None
        
        try:
            key = f"task:{task_id}"
            data = await self._client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            print(f"Task progress read failed: {e}")
            return None
    
    async def delete_task_progress(self, task_id: str) -> bool:
        """Delete task progress entry."""
        if not self._available:
            return False
        
        try:
            await self._client.delete(f"task:{task_id}")
            return True
        except Exception:
            return False
    
    # =========================================================================
    # RATE LIMITING
    # =========================================================================
    
    async def check_rate_limit(
        self,
        key: str,           # e.g., "api:user_123" or "upload:user_123"
        max_requests: int,  # max requests allowed
        window_seconds: int # time window
    ) -> Dict[str, Any]:
        """
        Check if request is within rate limit.
        Returns {"allowed": bool, "remaining": int, "reset_at": timestamp}
        """
        if not self._available:
            # Allow if Redis unavailable (fail open)
            return {"allowed": True, "remaining": max_requests, "reset_at": None}
        
        try:
            current = await self._client.get(key)
            
            if current is None:
                # First request in window
                await self._client.setex(key, window_seconds, "1")
                return {
                    "allowed": True,
                    "remaining": max_requests - 1,
                    "reset_at": (datetime.utcnow() + timedelta(seconds=window_seconds)).isoformat()
                }
            
            count = int(current)
            if count >= max_requests:
                ttl = await self._client.ttl(key)
                return {
                    "allowed": False,
                    "remaining": 0,
                    "reset_at": (datetime.utcnow() + timedelta(seconds=ttl)).isoformat()
                }
            
            # Increment count
            await self._client.incr(key)
            return {
                "allowed": True,
                "remaining": max_requests - count - 1,
                "reset_at": (datetime.utcnow() + timedelta(seconds=window_seconds)).isoformat()
            }
            
        except Exception as e:
            print(f"Rate limit check failed: {e}")
            return {"allowed": True, "remaining": max_requests, "reset_at": None}
    
    # =========================================================================
    # SESSION STATE
    # =========================================================================
    
    async def set_session_data(
        self,
        session_id: str,
        data: Dict,
        ttl_seconds: int = 3600  # 1 hour
    ) -> bool:
        """Store session data in Redis."""
        if not self._available:
            return False
        
        try:
            key = f"session:{session_id}"
            await self._client.setex(key, ttl_seconds, json.dumps(data))
            return True
        except Exception:
            return False
    
    async def get_session_data(self, session_id: str) -> Optional[Dict]:
        """Get session data from Redis."""
        if not self._available:
            return None
        
        try:
            key = f"session:{session_id}"
            data = await self._client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception:
            return None
    
    async def extend_session(self, session_id: str, ttl_seconds: int = 3600) -> bool:
        """Extend session TTL."""
        if not self._available:
            return False
        
        try:
            key = f"session:{session_id}"
            await self._client.expire(key, ttl_seconds)
            return True
        except Exception:
            return False
    
    # =========================================================================
    # FEATURE FLAGS
    # =========================================================================
    
    async def get_feature_flag(
        self,
        flag_name: str,
        default: bool = False
    ) -> bool:
        """Check if feature flag is enabled."""
        if not self._available:
            return default
        
        try:
            key = f"feature:{flag_name}"
            value = await self._client.get(key)
            if value is None:
                return default
            return value.lower() == "true"
        except Exception:
            return default
    
    async def set_feature_flag(
        self,
        flag_name: str,
        enabled: bool
    ) -> bool:
        """Set feature flag (no expiry - persistent)."""
        if not self._available:
            return False
        
        try:
            key = f"feature:{flag_name}"
            await self._client.set(key, "true" if enabled else "false")
            return True
        except Exception:
            return False
    
    # =========================================================================
    # HEALTH & STATS
    # =========================================================================
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get Redis stats."""
        if not self._available:
            return {"available": False}
        
        try:
            info = await self._client.info()
            return {
                "available": True,
                "version": info.get("redis_version"),
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_keys": await self._client.dbsize()
            }
        except Exception as e:
            return {"available": False, "error": str(e)}


# Global singleton
_redis_store_instance = None

async def get_redis_store() -> RedisStateStore:
    """Get global Redis state store."""
    global _redis_store_instance
    if _redis_store_instance is None:
        _redis_store_instance = RedisStateStore()
        await _redis_store_instance.connect()
    return _redis_store_instance
