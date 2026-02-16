"""
Dejavu Database Visualization

Provides endpoints for visualizing database schema, tables, and relationships.
Inspired by the Dejavu database visualization tool.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin_user
from app.db.session import get_db_session
from app.core.logging import get_logger
from app.triggers import event_bus, EventType

logger = get_logger(__name__)

router = APIRouter(prefix="/dejavu", dependencies=[Depends(get_current_admin_user)])

# Whitelist of allowed tables for security
ALLOWED_TABLES: set = {"users", "projects", "documents", "audit_logs"}

# Columns to redact from responses (sensitive data)
REDACT_COLUMNS = {
    "password", "secret", "token", "api_key", "access_token", 
    "refresh_token", "private_key", "hash", "encrypted"
}


def _require_allowed_table(table_name: str) -> None:
    """Raise 403 if table is not in the allowed whitelist."""
    if table_name not in ALLOWED_TABLES:
        logger.warning(
            "Dejavu: Access denied to non-whitelisted table",
            table=table_name,
        )
        raise HTTPException(
            status_code=403,
            detail=f"Access to table '{table_name}' is not permitted"
        )


def _redact_sensitive_data(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Redact sensitive columns from row data."""
    redacted_rows = []
    for row in rows:
        redacted_row = {}
        for key, value in row.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in REDACT_COLUMNS):
                redacted_row[key] = "***REDACTED***"
            else:
                redacted_row[key] = value
        redacted_rows.append(redacted_row)
    return redacted_rows


async def _audit_dejavu_access(
    request: Request,
    endpoint: str,
    table_name: Optional[str] = None,
    row_count: int = 0,
) -> None:
    """Emit audit event for Dejavu access."""
    from app.triggers import Event
    
    user = request.state.user if hasattr(request.state, "user") else None
    tenant_id = request.headers.get("X-Tenant-ID")
    
    audit_event = Event(
        type=EventType.DATA_ACCESSED,
        source="dejavu",
        payload={
            "endpoint": endpoint,
            "table": table_name,
            "row_count": row_count,
            "user_id": str(user.id) if user else None,
            "tenant_id": tenant_id,
            "ip_address": request.client.host if request.client else None,
        },
        tenant_id=tenant_id,
        user_id=str(user.id) if user else None,
    )
    
    await event_bus.emit(audit_event)


@router.get("/schema", response_model=Dict[str, Any])
async def get_database_schema(
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Get complete database schema visualization.
    
    Returns:
        Database schema with tables, columns, and relationships
    """
    try:
        # Get all tables
        result = await db.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """))
        tables = result.scalars().all()
        
        schema = {
            "database": "cerebrum",
            "tables": [],
            "relationships": [],
        }
        
        for table_name in tables:
            # Get columns for each table - using parameterized query
            columns_result = await db.execute(
                text("""
                    SELECT 
                        column_name,
                        data_type,
                        is_nullable,
                        column_default
                    FROM information_schema.columns
                    WHERE table_name = :table_name
                    ORDER BY ordinal_position
                """),
                {"table_name": table_name}
            )
            columns = columns_result.fetchall()
            
            # Get primary keys - using parameterized query
            pk_result = await db.execute(
                text("""
                    SELECT kcu.column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu 
                        ON tc.constraint_name = kcu.constraint_name
                    WHERE tc.table_name = :table_name
                    AND tc.constraint_type = 'PRIMARY KEY'
                """),
                {"table_name": table_name}
            )
            primary_keys = [row[0] for row in pk_result.fetchall()]
            
            # Get foreign keys - using parameterized query
            fk_result = await db.execute(
                text("""
                    SELECT
                        kcu.column_name,
                        ccu.table_name AS foreign_table_name,
                        ccu.column_name AS foreign_column_name
                    FROM information_schema.table_constraints AS tc
                    JOIN information_schema.key_column_usage AS kcu
                        ON tc.constraint_name = kcu.constraint_name
                    JOIN information_schema.constraint_column_usage AS ccu
                        ON ccu.constraint_name = tc.constraint_name
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND tc.table_name = :table_name
                """),
                {"table_name": table_name}
            )
            foreign_keys = [
                {
                    "column": row[0],
                    "references_table": row[1],
                    "references_column": row[2],
                }
                for row in fk_result.fetchall()
            ]
            
            # Add to relationships
            for fk in foreign_keys:
                schema["relationships"].append({
                    "from_table": table_name,
                    "from_column": fk["column"],
                    "to_table": fk["references_table"],
                    "to_column": fk["references_column"],
                    "type": "one-to-many",
                })
            
            schema["tables"].append({
                "name": table_name,
                "columns": [
                    {
                        "name": col[0],
                        "type": col[1],
                        "nullable": col[2] == "YES",
                        "default": col[3],
                        "primary_key": col[0] in primary_keys,
                    }
                    for col in columns
                ],
                "primary_keys": primary_keys,
                "foreign_keys": foreign_keys,
            })
        
        return schema
        
    except Exception as e:
        logger.error("Failed to get database schema", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables", response_model=List[Dict[str, Any]])
async def get_tables(
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_admin_user),
) -> List[Dict[str, Any]]:
    """
    Get list of all tables with row counts.
    
    Returns:
        List of tables with metadata
    """
    try:
        result = await db.execute(text("""
            SELECT 
                t.table_name,
                (SELECT COUNT(*) FROM information_schema.columns 
                 WHERE table_name = t.table_name) as column_count
            FROM information_schema.tables t
            WHERE t.table_schema = 'public'
            ORDER BY t.table_name
        """))
        tables = result.fetchall()
        
        # Get row counts for each table
        table_list = []
        for table_name, column_count in tables:
            try:
                # Use parameterized query for table name in identifier
                count_result = await db.execute(
                    text('SELECT COUNT(*) FROM "' + table_name.replace('"', '""') + '"')
                )
                row_count = count_result.scalar()
            except Exception:
                row_count = None
            
            table_list.append({
                "name": table_name,
                "columns": column_count,
                "rows": row_count,
            })
        
        return table_list
        
    except Exception as e:
        logger.error("Failed to get tables", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables/{table_name}", response_model=Dict[str, Any])
async def get_table_details(
    table_name: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Get detailed information about a specific table.
    
    Args:
        table_name: Name of the table
        
    Returns:
        Table details with columns, indexes, and sample data (redacted)
    """
    # Enforce whitelist
    _require_allowed_table(table_name)
    """
    Get detailed information about a specific table.
    
    Args:
        table_name: Name of the table
        
    Returns:
        Table details with columns, indexes, and sample data
    """
    try:
        # Get columns - using parameterized query
        columns_result = await db.execute(
            text("""
                SELECT 
                    column_name,
                    data_type,
                    is_nullable,
                    column_default,
                    character_maximum_length
                FROM information_schema.columns
                WHERE table_name = :table_name
                ORDER BY ordinal_position
            """),
            {"table_name": table_name}
        )
        columns = columns_result.fetchall()
        
        if not columns:
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
        
        # Get indexes - using parameterized query
        indexes_result = await db.execute(
            text("""
                SELECT
                    indexname,
                    indexdef
                FROM pg_indexes
                WHERE tablename = :table_name
            """),
            {"table_name": table_name}
        )
        indexes = indexes_result.fetchall()
        
        # Get constraints - using parameterized query
        constraints_result = await db.execute(
            text("""
                SELECT
                    tc.constraint_name,
                    tc.constraint_type
                FROM information_schema.table_constraints tc
                WHERE tc.table_name = :table_name
            """),
            {"table_name": table_name}
        )
        constraints = constraints_result.fetchall()
        
        # Get sample data (first 5 rows)
        try:
            # Sanitize table name for use in identifier
            safe_table_name = table_name.replace('"', '""')
            sample_result = await db.execute(
                text(f'SELECT * FROM "{safe_table_name}" LIMIT 5')
            )
            raw_sample_data = [dict(row._mapping) for row in sample_result.fetchall()]
            # Redact sensitive columns
            sample_data = _redact_sensitive_data(raw_sample_data)
        except Exception:
            sample_data = []
        
        # Audit log the access
        await _audit_dejavu_access(
            request=request,
            endpoint="get_table_details",
            table_name=table_name,
            row_count=len(sample_data),
        )
        
        return {
            "name": table_name,
            "columns": [
                {
                    "name": col[0],
                    "type": col[1],
                    "nullable": col[2] == "YES",
                    "default": col[3],
                    "max_length": col[4],
                }
                for col in columns
            ],
            "indexes": [
                {
                    "name": idx[0],
                    "definition": idx[1],
                }
                for idx in indexes
            ],
            "constraints": [
                {
                    "name": con[0],
                    "type": con[1],
                }
                for con in constraints
            ],
            "sample_data": sample_data,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get table details", table=table_name, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables/{table_name}/data", response_model=Dict[str, Any])
async def get_table_data(
    table_name: str,
    request: Request,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Get paginated data from a table.
    
    Args:
        table_name: Name of the table
        limit: Number of rows to return
        offset: Offset for pagination
        
    Returns:
        Paginated table data (sensitive columns redacted)
    """
    # Enforce whitelist
    _require_allowed_table(table_name)
    
    try:
        # Sanitize table name for use in identifier
        safe_table_name = table_name.replace('"', '""')
        
        # Get total count
        count_result = await db.execute(
            text(f'SELECT COUNT(*) FROM "{safe_table_name}"')
        )
        total = count_result.scalar()
        
        # Get data with parameterized limit/offset
        data_result = await db.execute(
            text(f'SELECT * FROM "{safe_table_name}" LIMIT :limit OFFSET :offset'),
            {"limit": limit, "offset": offset}
        )
        raw_rows = [dict(row._mapping) for row in data_result.fetchall()]
        # Redact sensitive columns
        rows = _redact_sensitive_data(raw_rows)
        
        # Audit log the access
        await _audit_dejavu_access(
            request=request,
            endpoint="get_table_data",
            table_name=table_name,
            row_count=len(rows),
        )
        
        return {
            "table": table_name,
            "total": total,
            "limit": limit,
            "offset": offset,
            "data": rows,
        }
        
    except Exception as e:
        logger.error("Failed to get table data", table=table_name, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/relationships", response_model=List[Dict[str, Any]])
async def get_relationships(
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_admin_user),
) -> List[Dict[str, Any]]:
    """
    Get all foreign key relationships.
    
    Returns:
        List of table relationships
    """
    try:
        result = await db.execute(text("""
            SELECT
                tc.table_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
            ORDER BY tc.table_name
        """))
        relationships = result.fetchall()
        
        return [
            {
                "from_table": rel[0],
                "from_column": rel[1],
                "to_table": rel[2],
                "to_column": rel[3],
            }
            for rel in relationships
        ]
        
    except Exception as e:
        logger.error("Failed to get relationships", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=Dict[str, Any])
async def get_database_stats(
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Get database statistics.
    
    Returns:
        Database statistics
    """
    try:
        # Get database size
        size_result = await db.execute(text("""
            SELECT pg_size_pretty(pg_database_size(current_database()))
        """))
        db_size = size_result.scalar()
        
        # Get table count
        table_count_result = await db.execute(text("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = 'public'
        """))
        table_count = table_count_result.scalar()
        
        # Get connection info
        conn_result = await db.execute(text("""
            SELECT count(*) FROM pg_stat_activity
        """))
        active_connections = conn_result.scalar()
        
        return {
            "database_size": db_size,
            "table_count": table_count,
            "active_connections": active_connections,
        }
        
    except Exception as e:
        logger.error("Failed to get database stats", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
