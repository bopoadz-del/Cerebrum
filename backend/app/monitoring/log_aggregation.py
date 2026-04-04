"""
Log Aggregation System
ELK Stack (Elasticsearch, Logstash, Kibana) integration
"""

import json
import logging
import logging.handlers
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import asyncio
import traceback
import hashlib

from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class LogEntry:
    """Structured log entry"""
    timestamp: datetime
    level: str
    message: str
    source: str
    service: str
    environment: str
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    request_id: Optional[str] = None
    http_method: Optional[str] = None
    http_path: Optional[str] = None
    http_status: Optional[int] = None
    duration_ms: Optional[float] = None
    error_type: Optional[str] = None
    error_stack: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Elasticsearch"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['@timestamp'] = self.timestamp.isoformat()
        return data
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), default=str)


class ElasticsearchHandler(logging.Handler):
    """Custom logging handler for Elasticsearch"""
    
    def __init__(self, hosts: List[str], index_prefix: str = 'cerebrum-logs'):
        super().__init__()
        self.hosts = hosts
        self.index_prefix = index_prefix
        self.es_client: Optional[AsyncElasticsearch] = None
        self.buffer: List[Dict] = []
        self.buffer_size = 100
        self.flush_interval = 5  # seconds
        self._flush_task = None
    
    async def initialize(self):
        """Initialize Elasticsearch connection"""
        self.es_client = AsyncElasticsearch(hosts=self.hosts)
        self._flush_task = asyncio.create_task(self._periodic_flush())
    
    async def close(self):
        """Close Elasticsearch connection"""
        if self._flush_task:
            self._flush_task.cancel()
        
        await self._flush_buffer()
        
        if self.es_client:
            await self.es_client.close()
    
    def emit(self, record: logging.LogRecord):
        """Emit log record to Elasticsearch"""
        try:
            log_entry = self._format_log_entry(record)
            self.buffer.append(log_entry)
            
            if len(self.buffer) >= self.buffer_size:
                asyncio.create_task(self._flush_buffer())
                
        except Exception as e:
            self.handleError(record)
    
    def _format_log_entry(self, record: logging.LogRecord) -> Dict[str, Any]:
        """Format log record to structured entry"""
        # Extract extra fields from record
        extra = getattr(record, 'extra', {})
        
        entry = {
            'timestamp': datetime.utcnow().isoformat(),
            '@timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'message': self.format(record),
            'source': f"{record.name}:{record.lineno}",
            'service': settings.SERVICE_NAME,
            'environment': settings.ENVIRONMENT,
            'host': getattr(record, 'host', None),
            'trace_id': getattr(record, 'trace_id', None),
            'span_id': getattr(record, 'span_id', None),
            'user_id': getattr(record, 'user_id', None),
            'tenant_id': getattr(record, 'tenant_id', None),
            'request_id': getattr(record, 'request_id', None),
        }
        
        # Add exception info if present
        if record.exc_info:
            entry['error_type'] = record.exc_info[0].__name__ if record.exc_info[0] else None
            entry['error_stack'] = traceback.format_exception(*record.exc_info)
        
        # Merge extra fields
        entry.update(extra)
        
        return entry
    
    async def _periodic_flush(self):
        """Periodically flush buffer"""
        while True:
            try:
                await asyncio.sleep(self.flush_interval)
                await self._flush_buffer()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic flush: {e}")
    
    async def _flush_buffer(self):
        """Flush buffer to Elasticsearch"""
        if not self.buffer or not self.es_client:
            return
        
        docs = self.buffer[:]
        self.buffer = []
        
        try:
            index_name = f"{self.index_prefix}-{datetime.utcnow().strftime('%Y.%m.%d')}"
            
            actions = [
                {
                    '_index': index_name,
                    '_source': doc
                }
                for doc in docs
            ]
            
            success, errors = await async_bulk(
                self.es_client,
                actions,
                raise_on_error=False
            )
            
            if errors:
                logger.error(f"Failed to index {len(errors)} log entries")
                
        except Exception as e:
            logger.error(f"Error flushing logs to Elasticsearch: {e}")
            # Put docs back in buffer
            self.buffer = docs + self.buffer


class LogAggregator:
    """Centralized log aggregation service"""
    
    def __init__(self):
        self.elasticsearch_url = settings.ELASTICSEARCH_URL
        self.kibana_url = settings.KIBANA_URL
        self.es_client: Optional[AsyncElasticsearch] = None
        self.handlers: List[logging.Handler] = []
    
    async def initialize(self):
        """Initialize log aggregation"""
        self.es_client = AsyncElasticsearch([self.elasticsearch_url])
        
        # Create index templates
        await self._create_index_templates()
        
        # Create Kibana dashboards
        await self._create_kibana_dashboards()
    
    async def _create_index_templates(self):
        """Create Elasticsearch index templates"""
        template = {
            'index_patterns': ['cerebrum-logs-*'],
            'settings': {
                'number_of_shards': 1,
                'number_of_replicas': 1,
                'index.lifecycle.name': 'cerebrum-logs-policy',
                'index.lifecycle.rollover_alias': 'cerebrum-logs'
            },
            'mappings': {
                'properties': {
                    '@timestamp': {'type': 'date'},
                    'timestamp': {'type': 'date'},
                    'level': {'type': 'keyword'},
                    'message': {'type': 'text', 'analyzer': 'standard'},
                    'source': {'type': 'keyword'},
                    'service': {'type': 'keyword'},
                    'environment': {'type': 'keyword'},
                    'trace_id': {'type': 'keyword'},
                    'span_id': {'type': 'keyword'},
                    'user_id': {'type': 'keyword'},
                    'tenant_id': {'type': 'keyword'},
                    'request_id': {'type': 'keyword'},
                    'http_method': {'type': 'keyword'},
                    'http_path': {'type': 'keyword'},
                    'http_status': {'type': 'integer'},
                    'duration_ms': {'type': 'float'},
                    'error_type': {'type': 'keyword'},
                    'error_stack': {'type': 'text'},
                    'metadata': {'type': 'object', 'enabled': False}
                }
            }
        }
        
        try:
            await self.es_client.indices.put_template(
                name='cerebrum-logs-template',
                body=template
            )
            logger.info("Created Elasticsearch index template")
        except Exception as e:
            logger.error(f"Failed to create index template: {e}")
    
    async def _create_kibana_dashboards(self):
        """Create Kibana dashboards programmatically"""
        # This would use Kibana's API to create dashboards
        pass
    
    async def search_logs(
        self,
        query: str = None,
        level: str = None,
        service: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Search logs in Elasticsearch"""
        must_clauses = []
        
        if query:
            must_clauses.append({
                'multi_match': {
                    'query': query,
                    'fields': ['message', 'error_stack']
                }
            })
        
        if level:
            must_clauses.append({'term': {'level': level}})
        
        if service:
            must_clauses.append({'term': {'service': service}})
        
        # Time range
        time_range = {}
        if start_time:
            time_range['gte'] = start_time.isoformat()
        if end_time:
            time_range['lte'] = end_time.isoformat()
        
        if time_range:
            must_clauses.append({
                'range': {'@timestamp': time_range}
            })
        
        search_body = {
            'query': {
                'bool': {
                    'must': must_clauses
                }
            },
            'sort': [{'@timestamp': {'order': 'desc'}}],
            'size': limit
        }
        
        try:
            response = await self.es_client.search(
                index='cerebrum-logs-*',
                body=search_body
            )
            
            return [
                {
                    'id': hit['_id'],
                    'index': hit['_index'],
                    **hit['_source']
                }
                for hit in response['hits']['hits']
            ]
        except Exception as e:
            logger.error(f"Error searching logs: {e}")
            return []
    
    async def get_log_stats(
        self,
        start_time: datetime = None,
        end_time: datetime = None,
        interval: str = '1h'
    ) -> Dict[str, Any]:
        """Get log statistics"""
        time_range = {}
        if start_time:
            time_range['gte'] = start_time.isoformat()
        if end_time:
            time_range['lte'] = end_time.isoformat()
        
        aggs = {
            'levels_over_time': {
                'date_histogram': {
                    'field': '@timestamp',
                    'calendar_interval': interval
                },
                'aggs': {
                    'levels': {
                        'terms': {'field': 'level'}
                    }
                }
            },
            'error_types': {
                'terms': {'field': 'error_type', 'size': 10}
            },
            'top_services': {
                'terms': {'field': 'service', 'size': 10}
            }
        }
        
        search_body = {
            'query': {
                'bool': {
                    'filter': [
                        {'range': {'@timestamp': time_range}} if time_range else {'match_all': {}}
                    ]
                }
            },
            'aggs': aggs,
            'size': 0
        }
        
        try:
            response = await self.es_client.search(
                index='cerebrum-logs-*',
                body=search_body
            )
            
            return {
                'total_logs': response['hits']['total']['value'],
                'levels_over_time': response['aggregations']['levels_over_time']['buckets'],
                'error_types': response['aggregations']['error_types']['buckets'],
                'top_services': response['aggregations']['top_services']['buckets']
            }
        except Exception as e:
            logger.error(f"Error getting log stats: {e}")
            return {}


# Global log aggregator
log_aggregator = LogAggregator()


class StructuredLogger:
    """Structured logging utility"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.context = {}
    
    def with_context(self, **kwargs) -> 'StructuredLogger':
        """Add context to logger"""
        new_logger = StructuredLogger(self.logger.name)
        new_logger.context = {**self.context, **kwargs}
        return new_logger
    
    def _log(self, level: int, message: str, **kwargs):
        """Internal log method"""
        extra = {**self.context, **kwargs}
        
        # Create log record with extra fields
        record = self.logger.makeRecord(
            self.logger.name,
            level,
            '(unknown file)',
            0,
            message,
            (),
            None
        )
        record.extra = extra
        
        self.logger.handle(record)
    
    def debug(self, message: str, **kwargs):
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self._log(logging.CRITICAL, message, **kwargs)
    
    def exception(self, message: str, **kwargs):
        """Log exception with stack trace"""
        self.logger.exception(message, extra={**self.context, **kwargs})


def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger"""
    return StructuredLogger(name)


class LogAnalytics:
    """Log analytics and insights"""
    
    def __init__(self, es_client: AsyncElasticsearch):
        self.es_client = es_client
    
    async def get_error_patterns(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Identify common error patterns"""
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        search_body = {
            'query': {
                'bool': {
                    'must': [
                        {'terms': {'level': ['ERROR', 'CRITICAL']}},
                        {'range': {'@timestamp': {'gte': start_time.isoformat()}}}
                    ]
                }
            },
            'aggs': {
                'error_signatures': {
                    'terms': {
                        'script': {
                            'source': "doc['error_type'].value + ': ' + doc['source'].value"
                        },
                        'size': 20
                    }
                }
            },
            'size': 0
        }
        
        response = await self.es_client.search(
            index='cerebrum-logs-*',
            body=search_body
        )
        
        return [
            {
                'signature': bucket['key'],
                'count': bucket['doc_count']
            }
            for bucket in response['aggregations']['error_signatures']['buckets']
        ]
    
    async def get_slow_operations(self, threshold_ms: float = 1000, limit: int = 50) -> List[Dict[str, Any]]:
        """Get slow operations"""
        search_body = {
            'query': {
                'bool': {
                    'must': [
                        {'range': {'duration_ms': {'gte': threshold_ms}}},
                        {'exists': {'field': 'http_path'}}
                    ]
                }
            },
            'sort': [{'duration_ms': {'order': 'desc'}}],
            'size': limit
        }
        
        response = await self.es_client.search(
            index='cerebrum-logs-*',
            body=search_body
        )
        
        return [
            {
                'timestamp': hit['_source']['@timestamp'],
                'path': hit['_source'].get('http_path'),
                'method': hit['_source'].get('http_method'),
                'duration_ms': hit['_source'].get('duration_ms'),
                'user_id': hit['_source'].get('user_id')
            }
            for hit in response['hits']['hits']
        ]
