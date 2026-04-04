"""
Database Index Strategy

Defines and manages database indexes for optimal query performance.
Includes composite indexes for common query patterns.
"""

from dataclasses import dataclass
from typing import List, Optional, Any

from sqlalchemy import Index, text
from sqlalchemy.schema import CreateIndex, DropIndex

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class IndexDefinition:
    """Definition of a database index."""
    
    name: str
    table: str
    columns: List[str]
    unique: bool = False
    concurrently: bool = True
    where: Optional[str] = None
    using: str = "btree"
    
    def to_sql(self) -> str:
        """Generate CREATE INDEX SQL statement."""
        columns_str = ", ".join(self.columns)
        unique_str = "UNIQUE " if self.unique else ""
        concurrently_str = "CONCURRENTLY " if self.concurrently else ""
        where_str = f" WHERE {self.where}" if self.where else ""
        
        return (
            f"CREATE {unique_str}INDEX {concurrently_str}{self.name} "
            f"ON {self.table} USING {self.using} ({columns_str}){where_str};"
        )
    
    def to_drop_sql(self) -> str:
        """Generate DROP INDEX SQL statement."""
        concurrently_str = "CONCURRENTLY " if self.concurrently else ""
        return f"DROP INDEX {concurrently_str}IF EXISTS {self.name};"


# Index definitions for common query patterns
INDEX_DEFINITIONS: List[IndexDefinition] = [
    # User indexes
    IndexDefinition(
        name="idx_users_email_active",
        table="users",
        columns=["email"],
        unique=True,
        where="deleted_at IS NULL",
    ),
    IndexDefinition(
        name="idx_users_tenant_role",
        table="users",
        columns=["tenant_id", "role"],
        where="deleted_at IS NULL",
    ),
    IndexDefinition(
        name="idx_users_created_at",
        table="users",
        columns=["created_at DESC"],
    ),
    
    # Session indexes
    IndexDefinition(
        name="idx_sessions_user_id",
        table="sessions",
        columns=["user_id"],
    ),
    IndexDefinition(
        name="idx_sessions_expires_at",
        table="sessions",
        columns=["expires_at"],
        where="expires_at > NOW()",
    ),
    
    # Audit log indexes
    IndexDefinition(
        name="idx_audit_logs_user_id",
        table="audit_logs",
        columns=["user_id"],
    ),
    IndexDefinition(
        name="idx_audit_logs_tenant_timestamp",
        table="audit_logs",
        columns=["tenant_id", "created_at DESC"],
    ),
    IndexDefinition(
        name="idx_audit_logs_action",
        table="audit_logs",
        columns=["action"],
    ),
    IndexDefinition(
        name="idx_audit_logs_resource",
        table="audit_logs",
        columns=["resource_type", "resource_id"],
    ),
    
    # Token blacklist indexes
    IndexDefinition(
        name="idx_token_blacklist_jti",
        table="token_blacklist",
        columns=["jti"],
        unique=True,
    ),
    IndexDefinition(
        name="idx_token_blacklist_expires",
        table="token_blacklist",
        columns=["expires_at"],
        where="expires_at > NOW()",
    ),
    
    # Project indexes (example entity)
    IndexDefinition(
        name="idx_projects_tenant_status",
        table="projects",
        columns=["tenant_id", "status"],
        where="deleted_at IS NULL",
    ),
    IndexDefinition(
        name="idx_projects_owner",
        table="projects",
        columns=["owner_id"],
        where="deleted_at IS NULL",
    ),
    
    # Full-text search indexes (using GIN)
    IndexDefinition(
        name="idx_users_name_trgm",
        table="users",
        columns=["name gin_trgm_ops"],
        using="gin",
    ),
]


class IndexManager:
    """
    Manages database index creation and maintenance.
    
    Provides utilities for creating indexes with zero-downtime
    using CONCURRENTLY option.
    """
    
    def __init__(self, index_definitions: Optional[List[IndexDefinition]] = None) -> None:
        """
        Initialize index manager.
        
        Args:
            index_definitions: List of index definitions, uses defaults if None
        """
        self.indexes = index_definitions or INDEX_DEFINITIONS
    
    def get_create_statements(self) -> List[str]:
        """
        Get all CREATE INDEX statements.
        
        Returns:
            List of SQL CREATE INDEX statements
        """
        return [idx.to_sql() for idx in self.indexes]
    
    def get_drop_statements(self) -> List[str]:
        """
        Get all DROP INDEX statements.
        
        Returns:
            List of SQL DROP INDEX statements
        """
        return [idx.to_drop_sql() for idx in self.indexes]
    
    def get_index_for_table(self, table: str) -> List[IndexDefinition]:
        """
        Get all index definitions for a specific table.
        
        Args:
            table: Table name
            
        Returns:
            List of index definitions for the table
        """
        return [idx for idx in self.indexes if idx.table == table]
    
    async def create_indexes(self, session) -> None:
        """
        Create all defined indexes.
        
        Args:
            session: Database session
        """
        logger.info("Creating database indexes")
        
        for idx in self.indexes:
            try:
                await session.execute(text(idx.to_sql()))
                logger.info(f"Created index", index=idx.name, table=idx.table)
            except Exception as e:
                if "already exists" in str(e).lower():
                    logger.debug(f"Index already exists", index=idx.name)
                else:
                    logger.error(f"Failed to create index", index=idx.name, error=str(e))
                    raise
        
        await session.commit()
        logger.info("Database indexes created successfully")
    
    async def drop_indexes(self, session) -> None:
        """
        Drop all defined indexes.
        
        Args:
            session: Database session
        """
        logger.info("Dropping database indexes")
        
        for idx in self.indexes:
            try:
                await session.execute(text(idx.to_drop_sql()))
                logger.info(f"Dropped index", index=idx.name)
            except Exception as e:
                logger.warning(f"Failed to drop index", index=idx.name, error=str(e))
        
        await session.commit()
        logger.info("Database indexes dropped")
    
    def analyze_table(self, table: str) -> str:
        """
        Generate ANALYZE statement for table.
        
        Args:
            table: Table name
            
        Returns:
            ANALYZE SQL statement
        """
        return f"ANALYZE {table};"


def create_sqlalchemy_index(
    name: str,
    table_name: str,
    columns: List[str],
    unique: bool = False,
    postgresql_where: Optional[Any] = None,
) -> Index:
    """
    Create SQLAlchemy Index object.
    
    Args:
        name: Index name
        table_name: Table name
        columns: Column names
        unique: Whether index is unique
        postgresql_where: WHERE clause for partial index
        
    Returns:
        SQLAlchemy Index object
    """
    return Index(
        name,
        *columns,
        unique=unique,
        postgresql_where=postgresql_where,
    )


# Common index patterns
COMMON_INDEX_PATTERNS = {
    "tenant_isolation": ["tenant_id"],
    "user_lookup": ["email"],
    "timestamp_range": ["created_at DESC"],
    "status_filter": ["status"],
    "soft_delete_filter": ["deleted_at"],
    "composite_tenant_status": ["tenant_id", "status"],
    "composite_user_timestamp": ["user_id", "created_at DESC"],
}


def suggest_indexes(table_name: str, query_patterns: List[str]) -> List[IndexDefinition]:
    """
    Suggest indexes based on query patterns.
    
    Args:
        table_name: Name of the table
        query_patterns: List of query pattern types
        
    Returns:
        List of suggested index definitions
    """
    suggestions = []
    
    for pattern in query_patterns:
        if pattern in COMMON_INDEX_PATTERNS:
            columns = COMMON_INDEX_PATTERNS[pattern]
            idx_name = f"idx_{table_name}_{'_'.join(c.replace(' ', '_').replace('DESC', 'desc') for c in columns)}"
            
            suggestions.append(IndexDefinition(
                name=idx_name,
                table=table_name,
                columns=columns,
            ))
    
    return suggestions


# Global index manager instance
index_manager = IndexManager()
