"""
Cache Manager Block - Infrastructure layer for Redis-backed caching.
"""

from typing import Any, Dict, Optional

from app.core.block import BaseBlock, BlockConfig
from app.core.block_registry import BLOCK_REGISTRY
from app.db.redis import cache


class CacheManagerBlock(BaseBlock):
    """Redis wrapper with get/set/delete/stats operations."""

    def __init__(self):
        super().__init__()
        self.config = BlockConfig(
            name="cache_manager",
            version="1.0",
            description="Redis-backed cache manager with TTL support",
        )
        self._cache = cache

    async def execute(self, action: str, input_data: dict, params: dict) -> dict:
        return await super().execute(action, input_data, params)

    async def get(self, input_data: dict, params: dict) -> dict:
        """Get a cached value by key."""
        key = input_data.get("key")
        if not key:
            return {"status": "error", "error": "Missing 'key' in input_data"}
        value = await self._cache.get(key)
        return {"status": "success", "key": key, "found": value is not None, "value": value}

    async def set(self, input_data: dict, params: dict) -> dict:
        """Set a cached value with optional TTL."""
        key = input_data.get("key")
        value = input_data.get("value")
        ttl = params.get("ttl") or input_data.get("ttl")
        if key is None or value is None:
            return {"status": "error", "error": "Missing 'key' or 'value' in input_data"}
        ok = await self._cache.set(key, value, ttl=ttl)
        return {"status": "success" if ok else "error", "key": key, "ttl": ttl}

    async def delete(self, input_data: dict, params: dict) -> dict:
        """Delete a cached key."""
        key = input_data.get("key")
        if not key:
            return {"status": "error", "error": "Missing 'key' in input_data"}
        ok = await self._cache.delete(key)
        return {"status": "success" if ok else "error", "key": key, "deleted": ok}

    async def exists(self, input_data: dict, params: dict) -> dict:
        """Check if a key exists in cache."""
        key = input_data.get("key")
        if not key:
            return {"status": "error", "error": "Missing 'key' in input_data"}
        found = await self._cache.exists(key)
        return {"status": "success", "key": key, "exists": found}

    async def stats(self, input_data: dict, params: dict) -> dict:
        """Return basic cache stats."""
        try:
            redis = self._cache._get_redis()
            info = await redis.info("stats")
            return {
                "status": "success",
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "hit_rate": self._compute_hit_rate(info),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _compute_hit_rate(self, info: dict) -> float:
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses
        if total == 0:
            return 0.0
        return round(hits / total, 4)

    def get_actions(self) -> Dict[str, Any]:
        return {
            "get": self.get,
            "set": self.set,
            "delete": self.delete,
            "exists": self.exists,
            "stats": self.stats,
        }


# Auto-register on import
BLOCK_REGISTRY.register(CacheManagerBlock())
