"""
Cache Monitoring
Redis performance monitoring with latency and hit/miss ratios
"""

import asyncio
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
import logging

import aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
    """Cache statistics"""
    timestamp: datetime
    total_commands_processed: int
    keyspace_hits: int
    keyspace_misses: int
    hit_rate: float
    used_memory_bytes: int
    used_memory_human: str
    connected_clients: int
    blocked_clients: int
    evicted_keys: int
    expired_keys: int
    instantaneous_ops_per_sec: int
    latency_ms: float


@dataclass
class KeyStats:
    """Key space statistics"""
    db: int
    keys: int
    expires: int
    avg_ttl: int


class RedisMonitor:
    """Monitor Redis cache"""
    
    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None
        self.stats_history: List[CacheStats] = []
        self.max_history = 1000
        self.latency_threshold_ms = 10
        self.hit_rate_threshold = 0.8
        self._monitoring = False
    
    async def initialize(self):
        """Initialize Redis connection"""
        self.redis = await aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True
        )
        logger.info("Redis monitor initialized")
    
    async def close(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()
    
    async def get_info(self) -> Dict[str, Any]:
        """Get Redis INFO output"""
        if not self.redis:
            return {}
        
        info = await self.redis.info()
        return info
    
    async def get_stats(self) -> CacheStats:
        """Get current cache statistics"""
        if not self.redis:
            raise RuntimeError("Redis not connected")
        
        # Measure latency
        start = time.time()
        await self.redis.ping()
        latency_ms = (time.time() - start) * 1000
        
        # Get INFO stats
        info = await self.redis.info()
        
        stats = info.get('stats', {})
        memory = info.get('memory', {})
        clients = info.get('clients', {})
        
        hits = int(stats.get('keyspace_hits', 0))
        misses = int(stats.get('keyspace_misses', 0))
        total = hits + misses
        hit_rate = hits / total if total > 0 else 0
        
        cache_stats = CacheStats(
            timestamp=datetime.utcnow(),
            total_commands_processed=int(stats.get('total_commands_processed', 0)),
            keyspace_hits=hits,
            keyspace_misses=misses,
            hit_rate=hit_rate,
            used_memory_bytes=int(memory.get('used_memory', 0)),
            used_memory_human=memory.get('used_memory_human', '0B'),
            connected_clients=int(clients.get('connected_clients', 0)),
            blocked_clients=int(clients.get('blocked_clients', 0)),
            evicted_keys=int(stats.get('evicted_keys', 0)),
            expired_keys=int(stats.get('expired_keys', 0)),
            instantaneous_ops_per_sec=int(stats.get('instantaneous_ops_per_sec', 0)),
            latency_ms=latency_ms
        )
        
        # Store in history
        self.stats_history.append(cache_stats)
        if len(self.stats_history) > self.max_history:
            self.stats_history = self.stats_history[-self.max_history:]
        
        return cache_stats
    
    async def get_keyspace_stats(self) -> List[KeyStats]:
        """Get keyspace statistics by database"""
        if not self.redis:
            return []
        
        info = await self.redis.info('keyspace')
        
        keyspace_stats = []
        for key, value in info.items():
            if key.startswith('db'):
                db_num = int(key[2:])
                # Parse keyspace info (format: "keys=123,expires=45,avg_ttl=67890")
                parts = value.split(',')
                data = {}
                for part in parts:
                    k, v = part.split('=')
                    data[k] = int(v)
                
                keyspace_stats.append(KeyStats(
                    db=db_num,
                    keys=data.get('keys', 0),
                    expires=data.get('expires', 0),
                    avg_ttl=data.get('avg_ttl', 0)
                ))
        
        return keyspace_stats
    
    async def get_slowlog(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get slow query log"""
        if not self.redis:
            return []
        
        slowlog = await self.redis.slowlog_get(count)
        
        return [
            {
                'id': entry['id'],
                'timestamp': datetime.fromtimestamp(entry['time']).isoformat(),
                'duration_ms': entry['duration'] / 1000,  # Convert from microseconds
                'command': ' '.join(entry['command'])
            }
            for entry in slowlog
        ]
    
    async def get_big_keys(self, sample_size: int = 100) -> List[Dict[str, Any]]:
        """Find large keys"""
        if not self.redis:
            return []
        
        big_keys = []
        
        # Use RANDOMKEY to sample keys
        for _ in range(sample_size):
            key = await self.redis.randomkey()
            if key:
                size = await self.redis.memory_usage(key)
                key_type = await self.redis.type(key)
                
                big_keys.append({
                    'key': key,
                    'type': key_type,
                    'size_bytes': size
                })
        
        # Sort by size
        big_keys.sort(key=lambda x: x['size_bytes'], reverse=True)
        
        return big_keys[:20]
    
    async def measure_latency(self, iterations: int = 100) -> Dict[str, float]:
        """Measure Redis latency"""
        if not self.redis:
            return {}
        
        latencies = []
        
        for _ in range(iterations):
            start = time.time()
            await self.redis.ping()
            latencies.append((time.time() - start) * 1000)
        
        import statistics
        
        return {
            'min_ms': min(latencies),
            'max_ms': max(latencies),
            'avg_ms': statistics.mean(latencies),
            'p50_ms': sorted(latencies)[int(len(latencies) * 0.5)],
            'p95_ms': sorted(latencies)[int(len(latencies) * 0.95)],
            'p99_ms': sorted(latencies)[int(len(latencies) * 0.99)]
        }
    
    async def get_hit_rate_trend(self, hours: int = 24) -> Dict[str, Any]:
        """Get hit rate trend"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        recent_stats = [s for s in self.stats_history if s.timestamp > cutoff]
        
        if not recent_stats:
            return {'trend': 'unknown', 'avg_hit_rate': 0}
        
        hit_rates = [s.hit_rate for s in recent_stats]
        
        import statistics
        
        avg_hit_rate = statistics.mean(hit_rates)
        
        # Determine trend
        if len(hit_rates) >= 2:
            first_half = statistics.mean(hit_rates[:len(hit_rates)//2])
            second_half = statistics.mean(hit_rates[len(hit_rates)//2:])
            
            if second_half > first_half * 1.05:
                trend = 'improving'
            elif second_half < first_half * 0.95:
                trend = 'declining'
            else:
                trend = 'stable'
        else:
            trend = 'stable'
        
        return {
            'trend': trend,
            'avg_hit_rate': avg_hit_rate,
            'min_hit_rate': min(hit_rates),
            'max_hit_rate': max(hit_rates)
        }
    
    async def check_health(self) -> Dict[str, Any]:
        """Check Redis health"""
        if not self.redis:
            return {'status': 'unhealthy', 'error': 'Not connected'}
        
        try:
            # Check connection
            await self.redis.ping()
            
            # Get current stats
            stats = await self.get_stats()
            
            # Determine health status
            issues = []
            
            if stats.latency_ms > self.latency_threshold_ms:
                issues.append(f'High latency: {stats.latency_ms:.2f}ms')
            
            if stats.hit_rate < self.hit_rate_threshold:
                issues.append(f'Low hit rate: {stats.hit_rate*100:.1f}%')
            
            if stats.evicted_keys > 1000:
                issues.append(f'High eviction rate: {stats.evicted_keys} keys')
            
            if issues:
                return {
                    'status': 'degraded',
                    'issues': issues,
                    'stats': {
                        'latency_ms': stats.latency_ms,
                        'hit_rate': stats.hit_rate,
                        'connected_clients': stats.connected_clients
                    }
                }
            
            return {
                'status': 'healthy',
                'stats': {
                    'latency_ms': stats.latency_ms,
                    'hit_rate': stats.hit_rate,
                    'connected_clients': stats.connected_clients
                }
            }
        
        except Exception as e:
            return {'status': 'unhealthy', 'error': str(e)}
    
    def get_stats_summary(self) -> Dict[str, Any]:
        """Get cache statistics summary"""
        if not self.stats_history:
            return {}
        
        latest = self.stats_history[-1]
        
        return {
            'timestamp': latest.timestamp.isoformat(),
            'hit_rate': latest.hit_rate,
            'used_memory': latest.used_memory_human,
            'connected_clients': latest.connected_clients,
            'ops_per_sec': latest.instantaneous_ops_per_sec,
            'latency_ms': latest.latency_ms
        }


# Global Redis monitor
redis_monitor = RedisMonitor()
