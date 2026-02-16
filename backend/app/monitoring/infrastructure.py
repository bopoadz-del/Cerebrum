"""
Infrastructure Monitoring
Prometheus + Grafana metrics collection for Cerebrum AI Platform
"""

import os
import time
import psutil
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging
import asyncio

from prometheus_client import (
    Counter, Histogram, Gauge, Info, 
    generate_latest, CONTENT_TYPE_LATEST,
    CollectorRegistry, multiprocess
)
from prometheus_client.openmetrics.exposition import generate_latest as generate_openmetrics
import aiohttp

from app.core.config import settings

logger = logging.getLogger(__name__)


# Prometheus registry
registry = CollectorRegistry()


class InfrastructureMetrics:
    """Infrastructure-level metrics collection"""
    
    # HTTP Request metrics
    http_requests_total = Counter(
        'cerebrum_http_requests_total',
        'Total HTTP requests',
        ['method', 'endpoint', 'status_code'],
        registry=registry
    )
    
    http_request_duration = Histogram(
        'cerebrum_http_request_duration_seconds',
        'HTTP request duration in seconds',
        ['method', 'endpoint'],
        buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
        registry=registry
    )
    
    http_request_size = Histogram(
        'cerebrum_http_request_size_bytes',
        'HTTP request size in bytes',
        ['method', 'endpoint'],
        buckets=[100, 1000, 10000, 100000, 1000000],
        registry=registry
    )
    
    http_response_size = Histogram(
        'cerebrum_http_response_size_bytes',
        'HTTP response size in bytes',
        ['method', 'endpoint'],
        buckets=[100, 1000, 10000, 100000, 1000000],
        registry=registry
    )
    
    # System metrics
    system_cpu_usage = Gauge(
        'cerebrum_system_cpu_usage_percent',
        'CPU usage percentage',
        ['mode'],
        registry=registry
    )
    
    system_memory_usage = Gauge(
        'cerebrum_system_memory_usage_bytes',
        'Memory usage in bytes',
        ['type'],
        registry=registry
    )
    
    system_disk_usage = Gauge(
        'cerebrum_system_disk_usage_bytes',
        'Disk usage in bytes',
        ['mountpoint', 'type'],
        registry=registry
    )
    
    system_network_io = Counter(
        'cerebrum_system_network_io_bytes_total',
        'Network I/O in bytes',
        ['interface', 'direction'],
        registry=registry
    )
    
    # Application metrics
    app_info = Info(
        'cerebrum_app_info',
        'Application information',
        registry=registry
    )
    
    app_active_connections = Gauge(
        'cerebrum_app_active_connections',
        'Number of active connections',
        registry=registry
    )
    
    app_goroutines = Gauge(
        'cerebrum_app_goroutines',
        'Number of goroutines (threads)',
        registry=registry
    )
    
    app_gc_duration = Histogram(
        'cerebrum_app_gc_duration_seconds',
        'Garbage collection duration',
        registry=registry
    )
    
    # Database metrics
    db_connections_active = Gauge(
        'cerebrum_db_connections_active',
        'Active database connections',
        ['database'],
        registry=registry
    )
    
    db_connections_idle = Gauge(
        'cerebrum_db_connections_idle',
        'Idle database connections',
        ['database'],
        registry=registry
    )
    
    db_query_duration = Histogram(
        'cerebrum_db_query_duration_seconds',
        'Database query duration',
        ['database', 'operation'],
        buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
        registry=registry
    )
    
    db_query_total = Counter(
        'cerebrum_db_queries_total',
        'Total database queries',
        ['database', 'operation', 'status'],
        registry=registry
    )
    
    # Cache metrics
    cache_operations_total = Counter(
        'cerebrum_cache_operations_total',
        'Total cache operations',
        ['cache', 'operation', 'status'],
        registry=registry
    )
    
    cache_hit_ratio = Gauge(
        'cerebrum_cache_hit_ratio',
        'Cache hit ratio',
        ['cache'],
        registry=registry
    )
    
    # Queue metrics
    queue_depth = Gauge(
        'cerebrum_queue_depth',
        'Queue depth',
        ['queue'],
        registry=registry
    )
    
    queue_processing_time = Histogram(
        'cerebrum_queue_processing_seconds',
        'Queue processing time',
        ['queue'],
        registry=registry
    )
    
    # Business metrics
    active_users = Gauge(
        'cerebrum_active_users',
        'Number of active users',
        ['tenant'],
        registry=registry
    )
    
    tenant_projects = Gauge(
        'cerebrum_tenant_projects_total',
        'Total projects per tenant',
        ['tenant'],
        registry=registry
    )
    
    def __init__(self):
        self._app_info_set = False
        self._collection_task = None
    
    def set_app_info(self, version: str, build: str):
        """Set application information"""
        if not self._app_info_set:
            self.app_info.info({
                'version': version,
                'build': build,
                'environment': settings.ENVIRONMENT,
                'service': settings.SERVICE_NAME
            })
            self._app_info_set = True
    
    def record_http_request(self, method: str, endpoint: str, status_code: int, 
                          duration: float, request_size: int = 0, response_size: int = 0):
        """Record HTTP request metrics"""
        self.http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()
        
        self.http_request_duration.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
        
        if request_size > 0:
            self.http_request_size.labels(
                method=method,
                endpoint=endpoint
            ).observe(request_size)
        
        if response_size > 0:
            self.http_response_size.labels(
                method=method,
                endpoint=endpoint
            ).observe(response_size)
    
    def record_db_query(self, database: str, operation: str, duration: float, success: bool = True):
        """Record database query metrics"""
        self.db_query_duration.labels(
            database=database,
            operation=operation
        ).observe(duration)
        
        self.db_query_total.labels(
            database=database,
            operation=operation,
            status='success' if success else 'error'
        ).inc()
    
    def record_cache_operation(self, cache: str, operation: str, hit: bool = True):
        """Record cache operation metrics"""
        self.cache_operations_total.labels(
            cache=cache,
            operation=operation,
            status='hit' if hit else 'miss'
        ).inc()
    
    def update_cache_hit_ratio(self, cache: str, hits: int, misses: int):
        """Update cache hit ratio"""
        total = hits + misses
        if total > 0:
            ratio = hits / total
            self.cache_hit_ratio.labels(cache=cache).set(ratio)
    
    def record_queue_depth(self, queue: str, depth: int):
        """Record queue depth"""
        self.queue_depth.labels(queue=queue).set(depth)
    
    def start_collection(self):
        """Start background metrics collection"""
        if self._collection_task is None:
            self._collection_task = asyncio.create_task(self._collect_system_metrics())
    
    async def _collect_system_metrics(self):
        """Collect system metrics periodically"""
        while True:
            try:
                # CPU metrics
                cpu_percent = psutil.cpu_percent(interval=None)
                self.system_cpu_usage.labels(mode='total').set(cpu_percent)
                
                # Memory metrics
                memory = psutil.virtual_memory()
                self.system_memory_usage.labels(type='used').set(memory.used)
                self.system_memory_usage.labels(type='free').set(memory.free)
                self.system_memory_usage.labels(type='cached').set(memory.cached)
                self.system_memory_usage.labels(type='buffers').set(memory.buffers)
                
                # Disk metrics
                for partition in psutil.disk_partitions():
                    try:
                        usage = psutil.disk_usage(partition.mountpoint)
                        self.system_disk_usage.labels(
                            mountpoint=partition.mountpoint,
                            type='used'
                        ).set(usage.used)
                        self.system_disk_usage.labels(
                            mountpoint=partition.mountpoint,
                            type='free'
                        ).set(usage.free)
                    except PermissionError:
                        continue
                
                # Network metrics
                net_io = psutil.net_io_counters(pernic=True)
                for interface, counters in net_io.items():
                    self.system_network_io.labels(
                        interface=interface,
                        direction='sent'
                    )._value.set(counters.bytes_sent)
                    self.system_network_io.labels(
                        interface=interface,
                        direction='received'
                    )._value.set(counters.bytes_recv)
                
            except Exception as e:
                logger.error(f"Error collecting system metrics: {e}")
            
            await asyncio.sleep(15)  # Collect every 15 seconds
    
    def get_metrics(self, content_type: str = CONTENT_TYPE_LATEST) -> bytes:
        """Get metrics in Prometheus format"""
        return generate_latest(registry)
    
    def get_openmetrics(self) -> bytes:
        """Get metrics in OpenMetrics format"""
        return generate_openmetrics(registry)


# Global metrics instance
infrastructure_metrics = InfrastructureMetrics()


class HealthChecker:
    """Health check endpoints for infrastructure monitoring"""
    
    def __init__(self):
        self.checks: Dict[str, Callable] = {}
        self.results: Dict[str, Dict[str, Any]] = {}
    
    def register_check(self, name: str, check_func: Callable, timeout: float = 5.0):
        """Register a health check"""
        self.checks[name] = {
            'func': check_func,
            'timeout': timeout
        }
    
    async def run_checks(self) -> Dict[str, Any]:
        """Run all health checks"""
        results = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'checks': {}
        }
        
        for name, check in self.checks.items():
            try:
                start = time.time()
                
                # Run check with timeout
                if asyncio.iscoroutinefunction(check['func']):
                    healthy = await asyncio.wait_for(
                        check['func'](),
                        timeout=check['timeout']
                    )
                else:
                    healthy = check['func']()
                
                duration = time.time() - start
                
                results['checks'][name] = {
                    'status': 'healthy' if healthy else 'unhealthy',
                    'response_time_ms': duration * 1000
                }
                
                if not healthy:
                    results['status'] = 'unhealthy'
                    
            except asyncio.TimeoutError:
                results['checks'][name] = {
                    'status': 'timeout',
                    'response_time_ms': check['timeout'] * 1000
                }
                results['status'] = 'unhealthy'
                
            except Exception as e:
                results['checks'][name] = {
                    'status': 'error',
                    'error': str(e)
                }
                results['status'] = 'unhealthy'
        
        return results
    
    async def liveness_check(self) -> Dict[str, str]:
        """Simple liveness check"""
        return {'status': 'alive'}
    
    async def readiness_check(self) -> Dict[str, Any]:
        """Readiness check for Kubernetes"""
        results = await self.run_checks()
        
        # Kubernetes expects specific format
        if results['status'] == 'healthy':
            return {'status': 'ready'}
        else:
            return {
                'status': 'not_ready',
                'failed_checks': [
                    name for name, check in results['checks'].items()
                    if check['status'] != 'healthy'
                ]
            }


# Global health checker
health_checker = HealthChecker()


class GrafanaDashboardGenerator:
    """Generate Grafana dashboard JSON"""
    
    def generate_dashboard(self, title: str = "Cerebrum AI Platform") -> Dict[str, Any]:
        """Generate a complete Grafana dashboard"""
        return {
            'dashboard': {
                'id': None,
                'uid': 'cerebrum-platform',
                'title': title,
                'tags': ['cerebrum', 'monitoring'],
                'timezone': 'utc',
                'schemaVersion': 36,
                'refresh': '30s',
                'panels': [
                    self._generate_stat_panel(
                        'Request Rate',
                        'sum(rate(cerebrum_http_requests_total[5m]))',
                        0, 0, 6, 3
                    ),
                    self._generate_stat_panel(
                        'Error Rate',
                        'sum(rate(cerebrum_http_requests_total{status_code=~"5.."}[5m]))',
                        6, 0, 6, 3
                    ),
                    self._generate_stat_panel(
                        'P95 Latency',
                        'histogram_quantile(0.95, sum(rate(cerebrum_http_request_duration_seconds_bucket[5m])) by (le))',
                        12, 0, 6, 3
                    ),
                    self._generate_stat_panel(
                        'Active Users',
                        'sum(cerebrum_active_users)',
                        18, 0, 6, 3
                    ),
                    self._generate_graph_panel(
                        'HTTP Requests by Endpoint',
                        'sum(rate(cerebrum_http_requests_total[5m])) by (endpoint)',
                        0, 3, 12, 8
                    ),
                    self._generate_graph_panel(
                        'Database Query Duration',
                        'histogram_quantile(0.99, sum(rate(cerebrum_db_query_duration_seconds_bucket[5m])) by (le, operation))',
                        12, 3, 12, 8
                    ),
                    self._generate_graph_panel(
                        'System CPU Usage',
                        'cerebrum_system_cpu_usage_percent',
                        0, 11, 8, 8
                    ),
                    self._generate_graph_panel(
                        'System Memory Usage',
                        'cerebrum_system_memory_usage_bytes',
                        8, 11, 8, 8
                    ),
                    self._generate_graph_panel(
                        'Cache Hit Ratio',
                        'cerebrum_cache_hit_ratio',
                        16, 11, 8, 8
                    ),
                ]
            },
            'overwrite': True
        }
    
    def _generate_stat_panel(self, title: str, expr: str, x: int, y: int, w: int, h: int) -> Dict:
        """Generate a stat panel"""
        return {
            'id': hash(title) % 10000,
            'title': title,
            'type': 'stat',
            'gridPos': {'x': x, 'y': y, 'w': w, 'h': h},
            'targets': [{
                'expr': expr,
                'legendFormat': '{{label}}',
                'refId': 'A'
            }],
            'fieldConfig': {
                'defaults': {
                    'unit': 'short',
                    'thresholds': {
                        'steps': [
                            {'color': 'green', 'value': None},
                            {'color': 'yellow', 'value': 80},
                            {'color': 'red', 'value': 95}
                        ]
                    }
                }
            }
        }
    
    def _generate_graph_panel(self, title: str, expr: str, x: int, y: int, w: int, h: int) -> Dict:
        """Generate a graph panel"""
        return {
            'id': hash(title) % 10000,
            'title': title,
            'type': 'timeseries',
            'gridPos': {'x': x, 'y': y, 'w': w, 'h': h},
            'targets': [{
                'expr': expr,
                'legendFormat': '{{label}}',
                'refId': 'A'
            }],
            'fieldConfig': {
                'defaults': {
                    'custom': {
                        'drawStyle': 'line',
                        'lineInterpolation': 'linear',
                        'pointSize': 5,
                        'showPoints': 'auto'
                    }
                }
            }
        }
