"""
Redis Sentinel - High Availability Setup
Configures Redis Sentinel for automatic failover and high availability.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from redis.sentinel import Sentinel
from redis import Redis
import logging

logger = logging.getLogger(__name__)


@dataclass
class SentinelConfig:
    """Redis Sentinel configuration."""
    
    # Sentinel hosts
    sentinels: List[tuple] = None  # [(host, port), ...]
    
    # Master name
    service_name: str = "mymaster"
    
    # Connection settings
    socket_timeout: float = 0.5
    socket_connect_timeout: float = 0.5
    retry_on_timeout: bool = True
    
    # Pool settings
    max_connections: int = 100
    
    # Password (if Redis is password protected)
    password: Optional[str] = None
    
    # Database
    db: int = 0
    
    # SSL
    ssl: bool = False
    ssl_certfile: Optional[str] = None
    ssl_keyfile: Optional[str] = None
    ssl_ca_certs: Optional[str] = None
    
    def __post_init__(self):
        if self.sentinels is None:
            self.sentinels = [
                ("redis-sentinel-1", 26379),
                ("redis-sentinel-2", 26379),
                ("redis-sentinel-3", 26379),
            ]


class RedisSentinelManager:
    """Manages Redis Sentinel connections."""
    
    def __init__(self, config: Optional[SentinelConfig] = None):
        self.config = config or SentinelConfig()
        self._sentinel: Optional[Sentinel] = None
        self._master: Optional[Redis] = None
        self._slave: Optional[Redis] = None
        self._connect()
    
    def _connect(self):
        """Connect to Redis Sentinel."""
        try:
            self._sentinel = Sentinel(
                self.config.sentinels,
                socket_timeout=self.config.socket_timeout,
                socket_connect_timeout=self.config.socket_connect_timeout,
                retry_on_timeout=self.config.retry_on_timeout,
                password=self.config.password,
                ssl=self.config.ssl,
                ssl_certfile=self.config.ssl_certfile,
                ssl_keyfile=self.config.ssl_keyfile,
                ssl_ca_certs=self.config.ssl_ca_certs,
                max_connections=self.config.max_connections
            )
            logger.info(f"Connected to Redis Sentinel: {self.config.sentinels}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis Sentinel: {e}")
            raise
    
    @property
    def master(self) -> Redis:
        """Get Redis master connection (for writes)."""
        if self._master is None:
            self._master = self._sentinel.master_for(
                self.config.service_name,
                socket_timeout=self.config.socket_timeout,
                db=self.config.db
            )
        return self._master
    
    @property
    def slave(self) -> Redis:
        """Get Redis slave connection (for reads)."""
        if self._slave is None:
            self._slave = self._sentinel.slave_for(
                self.config.service_name,
                socket_timeout=self.config.socket_timeout,
                db=self.config.db
            )
        return self._slave
    
    def get_master_info(self) -> Dict[str, Any]:
        """Get information about the current master."""
        try:
            master = self._sentinel.discover_master(self.config.service_name)
            return {
                "host": master[0],
                "port": master[1],
                "status": "up"
            }
        except Exception as e:
            return {
                "status": "down",
                "error": str(e)
            }
    
    def get_slaves_info(self) -> List[Dict[str, Any]]:
        """Get information about all slaves."""
        try:
            slaves = self._sentinel.discover_slaves(self.config.service_name)
            return [
                {"host": s[0], "port": s[1], "status": "up"}
                for s in slaves
            ]
        except Exception as e:
            return [{"status": "error", "error": str(e)}]
    
    def check_health(self) -> Dict[str, Any]:
        """Check Redis Sentinel health."""
        health = {
            "sentinels": [],
            "master": None,
            "slaves": [],
            "overall_status": "healthy"
        }
        
        # Check each sentinel
        for host, port in self.config.sentinels:
            try:
                # Try to connect to sentinel
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                sock.close()
                
                health["sentinels"].append({
                    "host": host,
                    "port": port,
                    "status": "up" if result == 0 else "down"
                })
            except Exception as e:
                health["sentinels"].append({
                    "host": host,
                    "port": port,
                    "status": "error",
                    "error": str(e)
                })
        
        # Check master
        health["master"] = self.get_master_info()
        
        # Check slaves
        health["slaves"] = self.get_slaves_info()
        
        # Determine overall status
        if health["master"]["status"] != "up":
            health["overall_status"] = "critical"
        elif len([s for s in health["slaves"] if s.get("status") == "up"]) == 0:
            health["overall_status"] = "degraded"
        
        return health
    
    def reconnect(self):
        """Reconnect to Sentinel."""
        self._master = None
        self._slave = None
        self._connect()


# Docker Compose configuration for Redis Sentinel
REDIS_SENTINEL_DOCKER_COMPOSE = """
version: '3.8'

services:
  redis-master:
    image: redis:7-alpine
    container_name: redis-master
    ports:
      - "6379:6379"
    volumes:
      - redis-master-data:/data
    command: >
      redis-server
      --appendonly yes
      --appendfsync everysec
      --maxmemory 256mb
      --maxmemory-policy allkeys-lru
    networks:
      - redis-network
    restart: unless-stopped

  redis-slave-1:
    image: redis:7-alpine
    container_name: redis-slave-1
    ports:
      - "6380:6379"
    command: >
      redis-server
      --slaveof redis-master 6379
      --appendonly yes
    networks:
      - redis-network
    depends_on:
      - redis-master
    restart: unless-stopped

  redis-slave-2:
    image: redis:7-alpine
    container_name: redis-slave-2
    ports:
      - "6381:6379"
    command: >
      redis-server
      --slaveof redis-master 6379
      --appendonly yes
    networks:
      - redis-network
    depends_on:
      - redis-master
    restart: unless-stopped

  redis-sentinel-1:
    image: redis:7-alpine
    container_name: redis-sentinel-1
    ports:
      - "26379:26379"
    volumes:
      - ./sentinel.conf:/etc/redis/sentinel.conf
    command: >
      redis-sentinel /etc/redis/sentinel.conf
    networks:
      - redis-network
    depends_on:
      - redis-master
      - redis-slave-1
      - redis-slave-2
    restart: unless-stopped

  redis-sentinel-2:
    image: redis:7-alpine
    container_name: redis-sentinel-2
    ports:
      - "26380:26379"
    volumes:
      - ./sentinel.conf:/etc/redis/sentinel.conf
    command: >
      redis-sentinel /etc/redis/sentinel.conf
    networks:
      - redis-network
    depends_on:
      - redis-master
      - redis-slave-1
      - redis-slave-2
    restart: unless-stopped

  redis-sentinel-3:
    image: redis:7-alpine
    container_name: redis-sentinel-3
    ports:
      - "26381:26379"
    volumes:
      - ./sentinel.conf:/etc/redis/sentinel.conf
    command: >
      redis-sentinel /etc/redis/sentinel.conf
    networks:
      - redis-network
    depends_on:
      - redis-master
      - redis-slave-1
      - redis-slave-2
    restart: unless-stopped

volumes:
  redis-master-data:

networks:
  redis-network:
    driver: bridge
"""


# Sentinel configuration file
SENTINEL_CONFIG = """
port 26379
dir /tmp
sentinel monitor mymaster redis-master 6379 2
sentinel down-after-milliseconds mymaster 5000
sentinel parallel-syncs mymaster 1
sentinel failover-timeout mymaster 10000
sentinel auth-pass mymaster your-password-here
"""


# Kubernetes StatefulSet for Redis
REDIS_K8S_STATEFULSET = """
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: redis
spec:
  serviceName: redis
  replicas: 3
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
          name: redis
        command:
        - redis-server
        - --appendonly
        - "yes"
        - --maxmemory
        - "256mb"
        volumeMounts:
        - name: data
          mountPath: /data
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 10Gi
"""


# Kubernetes ConfigMap for Sentinel
SENTINEL_K8S_CONFIGMAP = """
apiVersion: v1
kind: ConfigMap
metadata:
  name: sentinel-config
data:
  sentinel.conf: |
    port 26379
    dir /tmp
    sentinel monitor mymaster redis-0.redis 6379 2
    sentinel down-after-milliseconds mymaster 5000
    sentinel parallel-syncs mymaster 1
    sentinel failover-timeout mymaster 10000
"""


# Celery broker URL with Sentinel
def get_celery_broker_url(sentinel_config: SentinelConfig) -> str:
    """Generate Celery broker URL for Redis Sentinel."""
    sentinel_hosts = ','.join([f"{host}:{port}" for host, port in sentinel_config.sentinels])
    return (
        f"sentinel://{sentinel_config.service_name}/"
        f"{sentinel_hosts}/"
        f"{sentinel_config.db}"
    )


# Cache configuration for Django/Flask
def get_cache_config(sentinel_config: SentinelConfig) -> Dict[str, Any]:
    """Generate Django cache configuration for Redis Sentinel."""
    return {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": f"redis://{sentinel_config.service_name}/0",
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.SentinelClient",
                "SENTINELS": sentinel_config.sentinels,
                "SENTINEL_KWARGS": {
                    "socket_timeout": sentinel_config.socket_timeout,
                    "socket_connect_timeout": sentinel_config.socket_connect_timeout,
                },
                "PASSWORD": sentinel_config.password,
            }
        }
    }


# Singleton instance
_sentinel_manager: Optional[RedisSentinelManager] = None


def get_sentinel_manager(config: Optional[SentinelConfig] = None) -> RedisSentinelManager:
    """Get singleton Redis Sentinel manager."""
    global _sentinel_manager
    if _sentinel_manager is None:
        _sentinel_manager = RedisSentinelManager(config)
    return _sentinel_manager
