"""
Database Read Replicas - Read/Write Splitting
Automatic read replica routing with failover support.
"""

import os
import asyncio
import random
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
import asyncpg
import logging

logger = logging.getLogger(__name__)


class NodeRole(Enum):
    """Database node role."""
    PRIMARY = "primary"
    REPLICA = "replica"


@dataclass
class DatabaseNode:
    """Database node configuration."""
    host: str
    port: int
    database: str
    user: str
    password: str
    role: NodeRole
    weight: int = 1  # For load balancing
    healthy: bool = True
    last_check: Optional[float] = None
    latency_ms: Optional[float] = None


class ReadReplicaManager:
    """Manager for database read replicas."""
    
    def __init__(self):
        self.primary: Optional[DatabaseNode] = None
        self.replicas: List[DatabaseNode] = []
        self.logger = logging.getLogger(__name__)
        self._pools: Dict[str, asyncpg.Pool] = {}
        self._health_check_interval = 30  # seconds
        self._health_check_task: Optional[asyncio.Task] = None
    
    def configure_primary(
        self,
        host: str,
        port: int = 5432,
        database: str = "cerebrum",
        user: str = "postgres",
        password: str = ""
    ):
        """Configure primary database."""
        self.primary = DatabaseNode(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            role=NodeRole.PRIMARY
        )
    
    def add_replica(
        self,
        host: str,
        port: int = 5432,
        database: str = "cerebrum",
        user: str = "postgres",
        password: str = "",
        weight: int = 1
    ):
        """Add a read replica."""
        replica = DatabaseNode(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            role=NodeRole.REPLICA,
            weight=weight
        )
        self.replicas.append(replica)
    
    async def initialize(self):
        """Initialize connection pools."""
        # Create primary pool
        if self.primary:
            self._pools['primary'] = await asyncpg.create_pool(
                host=self.primary.host,
                port=self.primary.port,
                database=self.primary.database,
                user=self.primary.user,
                password=self.primary.password,
                min_size=5,
                max_size=20
            )
            self.logger.info(f"Created primary pool: {self.primary.host}")
        
        # Create replica pools
        for i, replica in enumerate(self.replicas):
            pool_key = f"replica_{i}"
            self._pools[pool_key] = await asyncpg.create_pool(
                host=replica.host,
                port=replica.port,
                database=replica.database,
                user=replica.user,
                password=replica.password,
                min_size=3,
                max_size=10
            )
            self.logger.info(f"Created replica pool: {replica.host}")
        
        # Start health check task
        self._health_check_task = asyncio.create_task(self._health_check_loop())
    
    async def close(self):
        """Close all connection pools."""
        # Stop health check
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Close pools
        for pool in self._pools.values():
            await pool.close()
        
        self._pools.clear()
        self.logger.info("All database pools closed")
    
    async def _health_check_loop(self):
        """Background health check loop."""
        while True:
            try:
                await self._check_health()
                await asyncio.sleep(self._health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Health check error: {e}")
                await asyncio.sleep(5)
    
    async def _check_health(self):
        """Check health of all database nodes."""
        # Check primary
        if self.primary:
            healthy, latency = await self._check_node_health(self.primary)
            self.primary.healthy = healthy
            self.primary.latency_ms = latency
            self.primary.last_check = asyncio.get_event_loop().time()
        
        # Check replicas
        for replica in self.replicas:
            healthy, latency = await self._check_node_health(replica)
            replica.healthy = healthy
            replica.latency_ms = latency
            replica.last_check = asyncio.get_event_loop().time()
    
    async def _check_node_health(self, node: DatabaseNode) -> tuple:
        """Check health of a single node."""
        try:
            start = asyncio.get_event_loop().time()
            
            conn = await asyncpg.connect(
                host=node.host,
                port=node.port,
                database=node.database,
                user=node.user,
                password=node.password
            )
            
            await conn.fetchval("SELECT 1")
            await conn.close()
            
            latency = (asyncio.get_event_loop().time() - start) * 1000
            return True, latency
            
        except Exception as e:
            self.logger.warning(f"Health check failed for {node.host}: {e}")
            return False, None
    
    def _get_replica_pool(self) -> Optional[asyncpg.Pool]:
        """Get a healthy replica pool using weighted random selection."""
        healthy_replicas = [
            (i, r) for i, r in enumerate(self.replicas)
            if r.healthy
        ]
        
        if not healthy_replicas:
            return None
        
        # Weighted random selection
        total_weight = sum(r.weight for _, r in healthy_replicas)
        pick = random.uniform(0, total_weight)
        
        current = 0
        for i, replica in healthy_replicas:
            current += replica.weight
            if pick <= current:
                return self._pools.get(f"replica_{i}")
        
        # Fallback to first
        return self._pools.get(f"replica_{healthy_replicas[0][0]}")
    
    async def execute_write(
        self,
        query: str,
        *args,
        timeout: Optional[float] = None
    ) -> Any:
        """Execute write query on primary."""
        if not self.primary or not self.primary.healthy:
            raise Exception("Primary database not available")
        
        pool = self._pools.get('primary')
        if not pool:
            raise Exception("Primary pool not initialized")
        
        async with pool.acquire() as conn:
            return await conn.execute(query, *args, timeout=timeout)
    
    async def fetch_read(
        self,
        query: str,
        *args,
        timeout: Optional[float] = None,
        prefer_replica: bool = True
    ) -> List[asyncpg.Record]:
        """Execute read query on replica (or primary if no replicas)."""
        pool = None
        
        if prefer_replica:
            pool = self._get_replica_pool()
        
        if not pool:
            # Fall back to primary
            if not self.primary or not self.primary.healthy:
                raise Exception("No database available")
            pool = self._pools.get('primary')
        
        if not pool:
            raise Exception("No database pool available")
        
        async with pool.acquire() as conn:
            return await conn.fetch(query, *args, timeout=timeout)
    
    async def fetchone_read(
        self,
        query: str,
        *args,
        timeout: Optional[float] = None,
        prefer_replica: bool = True
    ) -> Optional[asyncpg.Record]:
        """Execute read query and return single row."""
        results = await self.fetch_read(query, *args, timeout=timeout, prefer_replica=prefer_replica)
        return results[0] if results else None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database pool statistics."""
        stats = {
            'primary': {
                'host': self.primary.host if self.primary else None,
                'healthy': self.primary.healthy if self.primary else False,
                'latency_ms': self.primary.latency_ms if self.primary else None
            },
            'replicas': [],
            'pools': {}
        }
        
        for replica in self.replicas:
            stats['replicas'].append({
                'host': replica.host,
                'healthy': replica.healthy,
                'latency_ms': replica.latency_ms,
                'weight': replica.weight
            })
        
        for name, pool in self._pools.items():
            stats['pools'][name] = {
                'size': pool.get_size(),
                'free': pool.get_idle_size(),
                'max_size': pool.get_max_size()
            }
        
        return stats


class QueryRouter:
    """Route queries to appropriate database based on query type."""
    
    # SQL keywords that indicate write operations
    WRITE_KEYWORDS = {
        'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER',
        'TRUNCATE', 'GRANT', 'REVOKE', 'LOCK', 'UNLOCK'
    }
    
    @classmethod
    def is_write_query(cls, query: str) -> bool:
        """Determine if query is a write operation."""
        # Normalize query
        normalized = query.strip().upper()
        first_word = normalized.split()[0] if normalized else ''
        
        return first_word in cls.WRITE_KEYWORDS
    
    @classmethod
    def should_use_replica(cls, query: str, force_primary: bool = False) -> bool:
        """Determine if query should use replica."""
        if force_primary:
            return False
        
        return not cls.is_write_query(query)


# Decorator for automatic read/write splitting
def with_replica_fallback(read_timeout: float = 5.0):
    """Decorator that falls back to primary if replica fails."""
    def decorator(func):
        async def wrapper(self, *args, **kwargs):
            try:
                return await func(self, *args, **kwargs)
            except Exception as e:
                logger.warning(f"Replica query failed, falling back to primary: {e}")
                kwargs['prefer_replica'] = False
                return await func(self, *args, **kwargs)
        return wrapper
    return decorator
