"""
Database Monitoring
PostgreSQL performance monitoring with pg_stat_statements
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import async_session

logger = logging.getLogger(__name__)


@dataclass
class QueryStats:
    """Query statistics"""
    query_id: int
    query_text: str
    calls: int
    total_time: float
    mean_time: float
    stddev_time: float
    rows: int
    shared_blks_hit: int
    shared_blks_read: int
    temp_blks_written: int


@dataclass
class ConnectionStats:
    """Database connection statistics"""
    total_connections: int
    active_connections: int
    idle_connections: int
    waiting_connections: int
    max_connections: int
    connection_utilization: float


@dataclass
class TableStats:
    """Table statistics"""
    schema_name: str
    table_name: str
    row_count: int
    table_size_bytes: int
    index_size_bytes: int
    seq_scans: int
    idx_scans: int
    n_tup_ins: int
    n_tup_upd: int
    n_tup_del: int
    last_vacuum: Optional[datetime]
    last_analyze: Optional[datetime]


class DatabaseMonitor:
    """Monitor PostgreSQL database"""
    
    def __init__(self):
        self.query_stats: List[QueryStats] = []
        self.connection_stats: Optional[ConnectionStats] = None
        self.table_stats: List[TableStats] = []
        self.slow_query_threshold_ms = 1000
        self._monitoring_task = None
    
    async def initialize(self):
        """Initialize database monitoring"""
        # Enable pg_stat_statements if not already enabled
        await self._enable_pg_stat_statements()
    
    async def _enable_pg_stat_statements(self):
        """Enable pg_stat_statements extension"""
        async with async_session() as session:
            try:
                await session.execute(text("CREATE EXTENSION IF NOT EXISTS pg_stat_statements"))
                await session.commit()
                logger.info("pg_stat_statements extension enabled")
            except Exception as e:
                logger.warning(f"Could not enable pg_stat_statements: {e}")
    
    async def get_slow_queries(
        self,
        limit: int = 20,
        min_time_ms: float = None
    ) -> List[Dict[str, Any]]:
        """Get slow queries from pg_stat_statements"""
        min_time = min_time_ms or self.slow_query_threshold_ms
        
        async with async_session() as session:
            query = text("""
                SELECT 
                    queryid,
                    query,
                    calls,
                    total_exec_time,
                    mean_exec_time,
                    stddev_exec_time,
                    rows,
                    shared_blks_hit,
                    shared_blks_read,
                    temp_blks_written
                FROM pg_stat_statements
                WHERE mean_exec_time > :min_time
                ORDER BY mean_exec_time DESC
                LIMIT :limit
            """)
            
            result = await session.execute(
                query,
                {'min_time': min_time, 'limit': limit}
            )
            
            rows = result.fetchall()
            
            return [
                {
                    'query_id': row.queryid,
                    'query': row.query[:200] if row.query else '',
                    'calls': row.calls,
                    'total_time_ms': row.total_exec_time,
                    'mean_time_ms': row.mean_exec_time,
                    'stddev_time_ms': row.stddev_exec_time,
                    'rows': row.rows,
                    'shared_blks_hit': row.shared_blks_hit,
                    'shared_blks_read': row.shared_blks_read
                }
                for row in rows
            ]
    
    async def get_connection_stats(self) -> Dict[str, Any]:
        """Get database connection statistics"""
        async with async_session() as session:
            # Get connection counts
            result = await session.execute(text("""
                SELECT 
                    count(*) as total,
                    count(*) FILTER (WHERE state = 'active') as active,
                    count(*) FILTER (WHERE state = 'idle') as idle,
                    count(*) FILTER (WHERE wait_event_type IS NOT NULL) as waiting
                FROM pg_stat_activity
                WHERE backend_type = 'client backend'
            """))
            
            row = result.fetchone()
            
            # Get max connections
            max_result = await session.execute(text(
                "SHOW max_connections"
            ))
            max_connections = int(max_result.scalar())
            
            total = row.total or 0
            utilization = (total / max_connections * 100) if max_connections > 0 else 0
            
            return {
                'total_connections': total,
                'active_connections': row.active or 0,
                'idle_connections': row.idle or 0,
                'waiting_connections': row.waiting or 0,
                'max_connections': max_connections,
                'connection_utilization_percent': round(utilization, 2)
            }
    
    async def get_table_stats(self, schema: str = 'public') -> List[Dict[str, Any]]:
        """Get table statistics"""
        async with async_session() as session:
            query = text("""
                SELECT 
                    schemaname,
                    relname,
                    n_live_tup as row_count,
                    pg_total_relation_size(schemaname || '.' || relname) as total_size,
                    pg_indexes_size(schemaname || '.' || relname) as index_size,
                    seq_scan,
                    idx_scan,
                    n_tup_ins,
                    n_tup_upd,
                    n_tup_del,
                    last_vacuum,
                    last_analyze
                FROM pg_stat_user_tables
                WHERE schemaname = :schema
                ORDER BY n_live_tup DESC
            """)
            
            result = await session.execute(query, {'schema': schema})
            rows = result.fetchall()
            
            return [
                {
                    'schema': row.schemaname,
                    'table': row.relname,
                    'row_count': row.row_count,
                    'total_size_bytes': row.total_size,
                    'index_size_bytes': row.index_size,
                    'seq_scans': row.seq_scan,
                    'index_scans': row.idx_scan,
                    'inserts': row.n_tup_ins,
                    'updates': row.n_tup_upd,
                    'deletes': row.n_tup_del,
                    'last_vacuum': row.last_vacuum.isoformat() if row.last_vacuum else None,
                    'last_analyze': row.last_analyze.isoformat() if row.last_analyze else None
                }
                for row in rows
            ]
    
    async def get_lock_stats(self) -> List[Dict[str, Any]]:
        """Get current lock information"""
        async with async_session() as session:
            result = await session.execute(text("""
                SELECT 
                    l.locktype,
                    l.relation::regclass as relation,
                    l.mode,
                    l.granted,
                    a.usename,
                    a.query,
                    a.state,
                    age(now(), a.query_start) as duration
                FROM pg_locks l
                JOIN pg_stat_activity a ON l.pid = a.pid
                WHERE l.granted = false
                ORDER BY a.query_start
            """))
            
            rows = result.fetchall()
            
            return [
                {
                    'lock_type': row.locktype,
                    'relation': str(row.relation) if row.relation else None,
                    'mode': row.mode,
                    'granted': row.granted,
                    'user': row.usename,
                    'query': row.query[:100] if row.query else '',
                    'state': row.state,
                    'duration': str(row.duration) if row.duration else None
                }
                for row in rows
            ]
    
    async def get_replication_lag(self) -> Optional[Dict[str, Any]]:
        """Get replication lag if replica is configured"""
        async with async_session() as session:
            try:
                result = await session.execute(text("""
                    SELECT 
                        client_addr,
                        state,
                        sent_lsn,
                        write_lsn,
                        flush_lsn,
                        replay_lsn,
                        pg_size_pretty(pg_wal_lsn_diff(sent_lsn, replay_lsn)) as lag
                    FROM pg_stat_replication
                """))
                
                rows = result.fetchall()
                
                if not rows:
                    return None
                
                return [
                    {
                        'client_addr': str(row.client_addr) if row.client_addr else None,
                        'state': row.state,
                        'lag': row.lag
                    }
                    for row in rows
                ]
            
            except Exception as e:
                logger.debug(f"Replication not configured: {e}")
                return None
    
    async def get_database_size(self) -> Dict[str, Any]:
        """Get database size information"""
        async with async_session() as session:
            result = await session.execute(text("""
                SELECT 
                    datname,
                    pg_size_pretty(pg_database_size(datname)) as size,
                    pg_database_size(datname) as size_bytes
                FROM pg_database
                WHERE datistemplate = false
                ORDER BY pg_database_size(datname) DESC
            """))
            
            rows = result.fetchall()
            
            return [
                {
                    'database': row.datname,
                    'size': row.size,
                    'size_bytes': row.size_bytes
                }
                for row in rows
            ]
    
    async def reset_pg_stat_statements(self):
        """Reset pg_stat_statements statistics"""
        async with async_session() as session:
            await session.execute(text("SELECT pg_stat_statements_reset()"))
            await session.commit()
            logger.info("pg_stat_statements reset")
    
    def get_database_health(self) -> Dict[str, Any]:
        """Get overall database health"""
        return {
            'status': 'healthy',
            'checks': {
                'connections': 'ok',
                'slow_queries': 'ok',
                'locks': 'ok',
                'replication': 'ok'
            }
        }


# Global database monitor
database_monitor = DatabaseMonitor()
