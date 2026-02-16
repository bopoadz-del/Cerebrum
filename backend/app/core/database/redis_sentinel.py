"""
Redis Sentinel Configuration - High Availability Redis
Redis Sentinel setup for automatic failover and high availability.
"""

import os
import asyncio
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass
import redis.asyncio as redis
from redis.asyncio.sentinel import Sentinel
from redis.exceptions import RedisError, ConnectionError, TimeoutError
import logging
import json
import time

logger = logging.getLogger(__name__)


# Redis Sentinel Configuration
SENTINEL_HOSTS = os.getenv('REDIS_SENTINEL_HOSTS', 'localhost:26379').split(',')
SENTINEL_MASTER_NAME = os.getenv('REDIS_SENTINEL_MASTER_NAME', 'mymaster')
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')
REDIS_DB = int(os.getenv('REDIS_DB', '0'))
SENTINEL_SOCKET_TIMEOUT = float(os.getenv('SENTINEL_SOCKET_TIMEOUT', '5'))


@dataclass
class RedisNode:
    """Redis node information."""
    host: str
    port: int
    role: str  # 'master' or 'slave'
    flags: List[str]
    ping_sent: float
    ping_reply: float
    down_after_milliseconds: int


@dataclass
class SentinelMaster:
    """Sentinel master information."""
    name: str
    ip: str
    port: int
    flags: List[str]
    num_slaves: int
    num_sentinels: int
    quorum: int


class RedisSentinelManager:
    """Manager for Redis Sentinel connections."""
    
    def __init__(
        self,
        sentinel_hosts: List[str] = None,
        master_name: str = SENTINEL_MASTER_NAME,
        password: Optional[str] = REDIS_PASSWORD,
        db: int = REDIS_DB,
        socket_timeout: float = SENTINEL_SOCKET_TIMEOUT
    ):
        self.sentinel_hosts = sentinel_hosts or SENTINEL_HOSTS
        self.master_name = master_name
        self.password = password
        self.db = db
        self.socket_timeout = socket_timeout
        
        self.sentinel: Optional[Sentinel] = None
        self.master_client: Optional[redis.Redis] = None
        self.slave_client: Optional[redis.Redis] = None
        
        self.logger = logging.getLogger(__name__)
        self._connection_listeners: List[Callable] = []
        self._failover_listeners: List[Callable] = []
    
    def _parse_sentinel_hosts(self) -> List[tuple]:
        """Parse sentinel host strings to tuples."""
        hosts = []
        for host_str in self.sentinel_hosts:
            parts = host_str.strip().split(':')
            host = parts[0]
            port = int(parts[1]) if len(parts) > 1 else 26379
            hosts.append((host, port))
        return hosts
    
    async def connect(self) -> bool:
        """Connect to Redis Sentinel."""
        try:
            sentinel_hosts = self._parse_sentinel_hosts()
            
            self.sentinel = Sentinel(
                sentinel_hosts,
                socket_timeout=self.socket_timeout,
                password=self.password,
                decode_responses=True
            )
            
            # Test connection by getting master address
            master_addr = self.sentinel.discover_master(self.master_name)
            self.logger.info(f"Connected to Redis master at {master_addr}")
            
            # Get clients
            self.master_client = self.sentinel.master_for(
                self.master_name,
                socket_timeout=self.socket_timeout,
                db=self.db
            )
            
            self.slave_client = self.sentinel.slave_for(
                self.master_name,
                socket_timeout=self.socket_timeout,
                db=self.db
            )
            
            # Test connections
            await self.master_client.ping()
            self.logger.info("Redis master connection verified")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Redis Sentinel: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.master_client:
            await self.master_client.close()
        if self.slave_client:
            await self.slave_client.close()
        
        self.master_client = None
        self.slave_client = None
        self.sentinel = None
        
        self.logger.info("Disconnected from Redis")
    
    async def get_master_info(self) -> Optional[SentinelMaster]:
        """Get information about the current master."""
        if not self.sentinel:
            return None
        
        try:
            # Get master info from sentinel
            sentinel_client = redis.Redis(
                host=self._parse_sentinel_hosts()[0][0],
                port=self._parse_sentinel_hosts()[0][1],
                password=self.password,
                decode_responses=True
            )
            
            master_info = await sentinel_client.sentinel_master(self.master_name)
            await sentinel_client.close()
            
            return SentinelMaster(
                name=self.master_name,
                ip=master_info.get('ip', ''),
                port=int(master_info.get('port', 0)),
                flags=master_info.get('flags', '').split(','),
                num_slaves=int(master_info.get('num-slaves', 0)),
                num_sentinels=int(master_info.get('num-other-sentinels', 0)) + 1,
                quorum=int(master_info.get('quorum', 0))
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get master info: {e}")
            return None
    
    async def get_slaves_info(self) -> List[RedisNode]:
        """Get information about slave nodes."""
        if not self.sentinel:
            return []
        
        try:
            sentinel_client = redis.Redis(
                host=self._parse_sentinel_hosts()[0][0],
                port=self._parse_sentinel_hosts()[0][1],
                password=self.password,
                decode_responses=True
            )
            
            slaves = await sentinel_client.sentinel_slaves(self.master_name)
            await sentinel_client.close()
            
            return [
                RedisNode(
                    host=slave.get('ip', ''),
                    port=int(slave.get('port', 0)),
                    role='slave',
                    flags=slave.get('flags', '').split(','),
                    ping_sent=float(slave.get('ping-sent', 0)),
                    ping_reply=float(slave.get('ping-reply', 0)),
                    down_after_milliseconds=int(slave.get('down-after-milliseconds', 0))
                )
                for slave in slaves
            ]
            
        except Exception as e:
            self.logger.error(f"Failed to get slaves info: {e}")
            return []
    
    async def execute_on_master(self, command: str, *args, **kwargs) -> Any:
        """Execute a command on the master node."""
        if not self.master_client:
            raise ConnectionError("Not connected to Redis master")
        
        try:
            method = getattr(self.master_client, command)
            return await method(*args, **kwargs)
        except (ConnectionError, TimeoutError) as e:
            self.logger.error(f"Redis master command failed: {e}")
            # Try to reconnect
            await self.connect()
            raise
    
    async def execute_on_slave(self, command: str, *args, **kwargs) -> Any:
        """Execute a read command on a slave node."""
        if not self.slave_client:
            # Fall back to master if no slave available
            return await self.execute_on_master(command, *args, **kwargs)
        
        try:
            method = getattr(self.slave_client, command)
            return await method(*args, **kwargs)
        except (ConnectionError, TimeoutError) as e:
            self.logger.warning(f"Redis slave command failed, falling back to master: {e}")
            return await self.execute_on_master(command, *args, **kwargs)
    
    # High-level operations
    async def get(self, key: str, use_slave: bool = True) -> Optional[str]:
        """Get value by key."""
        if use_slave:
            return await self.execute_on_slave('get', key)
        return await self.execute_on_master('get', key)
    
    async def set(
        self,
        key: str,
        value: str,
        ex: Optional[int] = None,
        px: Optional[int] = None,
        nx: bool = False,
        xx: bool = False
    ) -> bool:
        """Set key-value pair."""
        return await self.execute_on_master('set', key, value, ex=ex, px=px, nx=nx, xx=xx)
    
    async def delete(self, *keys: str) -> int:
        """Delete keys."""
        return await self.execute_on_master('delete', *keys)
    
    async def exists(self, *keys: str) -> int:
        """Check if keys exist."""
        return await self.execute_on_slave('exists', *keys)
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set key expiration."""
        return await self.execute_on_master('expire', key, seconds)
    
    async def ttl(self, key: str) -> int:
        """Get time to live for key."""
        return await self.execute_on_slave('ttl', key)
    
    async def hget(self, name: str, key: str) -> Optional[str]:
        """Get hash field value."""
        return await self.execute_on_slave('hget', name, key)
    
    async def hset(self, name: str, key: str, value: str) -> int:
        """Set hash field value."""
        return await self.execute_on_master('hset', name, key, value)
    
    async def hgetall(self, name: str) -> Dict[str, str]:
        """Get all hash fields and values."""
        return await self.execute_on_slave('hgetall', name)
    
    async def lpush(self, name: str, *values: str) -> int:
        """Push values to list head."""
        return await self.execute_on_master('lpush', name, *values)
    
    async def rpop(self, name: str) -> Optional[str]:
        """Pop value from list tail."""
        return await self.execute_on_master('rpop', name)
    
    async def lrange(self, name: str, start: int, end: int) -> List[str]:
        """Get list range."""
        return await self.execute_on_slave('lrange', name, start, end)
    
    async def sadd(self, name: str, *values: str) -> int:
        """Add members to set."""
        return await self.execute_on_master('sadd', name, *values)
    
    async def smembers(self, name: str) -> set:
        """Get set members."""
        return await self.execute_on_slave('smembers', name)
    
    async def publish(self, channel: str, message: str) -> int:
        """Publish message to channel."""
        return await self.execute_on_master('publish', channel, message)
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        health = {
            'connected': False,
            'master': None,
            'slaves': [],
            'latency_ms': None,
            'timestamp': time.time()
        }
        
        if not self.sentinel:
            return health
        
        try:
            # Check master
            start = time.time()
            await self.master_client.ping()
            health['latency_ms'] = (time.time() - start) * 1000
            health['connected'] = True
            
            # Get master info
            master_info = await self.get_master_info()
            if master_info:
                health['master'] = {
                    'host': master_info.ip,
                    'port': master_info.port,
                    'flags': master_info.flags
                }
            
            # Get slaves info
            slaves = await self.get_slaves_info()
            health['slaves'] = [
                {'host': s.host, 'port': s.port, 'flags': s.flags}
                for s in slaves
            ]
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            health['error'] = str(e)
        
        return health


class RedisCache:
    """Redis-based cache with Sentinel support."""
    
    def __init__(self, sentinel_manager: RedisSentinelManager, default_ttl: int = 3600):
        self.redis = sentinel_manager
        self.default_ttl = default_ttl
        self.logger = logging.getLogger(__name__)
    
    async def get(self, key: str) -> Optional[Any]:
        """Get cached value."""
        try:
            data = await self.redis.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            self.logger.error(f"Cache get failed for {key}: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """Set cached value."""
        try:
            data = json.dumps(value)
            await self.redis.set(key, data, ex=ttl or self.default_ttl)
            return True
        except Exception as e:
            self.logger.error(f"Cache set failed for {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete cached value."""
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            self.logger.error(f"Cache delete failed for {key}: {e}")
            return False
    
    async def get_or_set(
        self,
        key: str,
        getter: Callable,
        ttl: Optional[int] = None
    ) -> Any:
        """Get from cache or set using getter function."""
        cached = await self.get(key)
        if cached is not None:
            return cached
        
        value = await getter()
        await self.set(key, value, ttl)
        return value
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate cache keys matching pattern."""
        try:
            # This requires scanning, which should be done on master
            keys = []
            async for key in self.redis.master_client.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                await self.redis.delete(*keys)
            
            return len(keys)
        except Exception as e:
            self.logger.error(f"Cache invalidation failed for pattern {pattern}: {e}")
            return 0


# Singleton instance
redis_sentinel = RedisSentinelManager()
redis_cache = RedisCache(redis_sentinel)
