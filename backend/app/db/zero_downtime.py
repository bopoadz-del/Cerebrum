"""
Zero-Downtime Migration Utilities

Provides utilities for performing database migrations without downtime,
including online index creation, table renaming, and column additions.
"""

from enum import Enum
from typing import List, Optional, Callable, Any
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger

logger = get_logger(__name__)


class MigrationPhase(str, Enum):
    """Migration phase enumeration."""
    PRE_DEPLOY = "pre_deploy"
    DEPLOY = "deploy"
    POST_DEPLOY = "post_deploy"
    CLEANUP = "cleanup"


@dataclass
class MigrationStep:
    """Single migration step definition."""
    name: str
    phase: MigrationPhase
    sql: str
    rollback_sql: Optional[str] = None
    description: str = ""


class ZeroDowntimeMigration:
    """
    Zero-downtime migration manager.
    
    Implements the expand-contract pattern for safe migrations:
    1. PRE_DEPLOY: Add new columns/tables (backward compatible)
    2. DEPLOY: Deploy new code that uses new schema
    3. POST_DEPLOY: Backfill data, enable constraints
    4. CLEANUP: Remove old columns/tables
    """
    
    def __init__(self, name: str) -> None:
        """
        Initialize migration.
        
        Args:
            name: Migration name
        """
        self.name = name
        self.steps: List[MigrationStep] = []
        self._completed_steps: List[str] = []
    
    def add_step(
        self,
        name: str,
        phase: MigrationPhase,
        sql: str,
        rollback_sql: Optional[str] = None,
        description: str = "",
    ) -> "ZeroDowntimeMigration":
        """
        Add migration step.
        
        Args:
            name: Step name
            phase: Migration phase
            sql: SQL to execute
            rollback_sql: SQL to rollback this step
            description: Step description
            
        Returns:
            Self for chaining
        """
        self.steps.append(MigrationStep(
            name=name,
            phase=phase,
            sql=sql,
            rollback_sql=rollback_sql,
            description=description,
        ))
        return self
    
    async def execute_phase(
        self,
        session: AsyncSession,
        phase: MigrationPhase,
    ) -> List[str]:
        """
        Execute all steps for a phase.
        
        Args:
            session: Database session
            phase: Phase to execute
            
        Returns:
            List of executed step names
        """
        phase_steps = [s for s in self.steps if s.phase == phase]
        executed = []
        
        logger.info(
            f"Executing {phase} phase of migration {self.name}",
            migration=self.name,
            phase=phase,
            step_count=len(phase_steps),
        )
        
        for step in phase_steps:
            try:
                logger.info(
                    f"Executing step: {step.name}",
                    step=step.name,
                    description=step.description,
                )
                
                await session.execute(text(step.sql))
                executed.append(step.name)
                self._completed_steps.append(step.name)
                
                logger.info(f"Step completed: {step.name}")
                
            except Exception as e:
                logger.error(
                    f"Step failed: {step.name}",
                    step=step.name,
                    error=str(e),
                )
                raise
        
        await session.commit()
        
        logger.info(
            f"Phase {phase} completed",
            migration=self.name,
            phase=phase,
            executed=len(executed),
        )
        
        return executed
    
    async def rollback_step(
        self,
        session: AsyncSession,
        step_name: str,
    ) -> bool:
        """
        Rollback a specific step.
        
        Args:
            session: Database session
            step_name: Name of step to rollback
            
        Returns:
            True if rollback was successful
        """
        step = next((s for s in self.steps if s.name == step_name), None)
        
        if not step:
            logger.warning(f"Step not found: {step_name}")
            return False
        
        if not step.rollback_sql:
            logger.warning(f"No rollback SQL for step: {step_name}")
            return False
        
        try:
            logger.info(f"Rolling back step: {step_name}")
            await session.execute(text(step.rollback_sql))
            await session.commit()
            
            if step_name in self._completed_steps:
                self._completed_steps.remove(step_name)
            
            logger.info(f"Rollback completed: {step_name}")
            return True
            
        except Exception as e:
            logger.error(
                f"Rollback failed: {step_name}",
                step=step_name,
                error=str(e),
            )
            await session.rollback()
            return False


class IndexManager:
    """
    Online index creation manager.
    
    Creates indexes without locking tables using CONCURRENTLY option.
    """
    
    @staticmethod
    async def create_index_online(
        session: AsyncSession,
        index_name: str,
        table_name: str,
        columns: List[str],
        unique: bool = False,
        where: Optional[str] = None,
    ) -> None:
        """
        Create index online (without locking).
        
        Args:
            session: Database session
            index_name: Name of index
            table_name: Table to index
            columns: Columns to include
            unique: Whether index is unique
            where: WHERE clause for partial index
        """
        columns_str = ", ".join(columns)
        unique_str = "UNIQUE " if unique else ""
        where_str = f" WHERE {where}" if where else ""
        
        # Use CONCURRENTLY to avoid locking
        sql = (
            f"CREATE {unique_str}INDEX CONCURRENTLY IF NOT EXISTS {index_name} "
            f"ON {table_name} ({columns_str}){where_str}"
        )
        
        logger.info(
            "Creating index online",
            index=index_name,
            table=table_name,
        )
        
        # CONCURRENTLY cannot run in a transaction block
        await session.execute(text("COMMIT"))
        await session.execute(text(sql))
        
        logger.info(f"Index created: {index_name}")
    
    @staticmethod
    async def drop_index_online(
        session: AsyncSession,
        index_name: str,
    ) -> None:
        """
        Drop index online (without locking).
        
        Args:
            session: Database session
            index_name: Name of index to drop
        """
        sql = f"DROP INDEX CONCURRENTLY IF EXISTS {index_name}"
        
        logger.info(f"Dropping index online: {index_name}")
        
        await session.execute(text("COMMIT"))
        await session.execute(text(sql))
        
        logger.info(f"Index dropped: {index_name}")


class ColumnManager:
    """
    Safe column operations manager.
    
    Provides safe ways to add, rename, and drop columns.
    """
    
    @staticmethod
    async def add_column_safe(
        session: AsyncSession,
        table_name: str,
        column_name: str,
        column_type: str,
        nullable: bool = True,
        default: Optional[Any] = None,
    ) -> None:
        """
        Add column safely (backward compatible).
        
        Args:
            session: Database session
            table_name: Table name
            column_name: Column name
            column_type: Column type (e.g., VARCHAR(255))
            nullable: Whether column is nullable
            default: Default value
        """
        # Always add as nullable first for backward compatibility
        sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
        
        if default is not None:
            sql += f" DEFAULT {default}"
        
        if not nullable and default is None:
            # Add as nullable first, then set NOT NULL after backfill
            logger.warning(
                f"Adding column {column_name} as nullable first. "
                "Set NOT NULL after data backfill."
            )
        else:
            sql += " NOT NULL" if not nullable else ""
        
        logger.info(
            "Adding column",
            table=table_name,
            column=column_name,
        )
        
        await session.execute(text(sql))
        await session.commit()
        
        logger.info(f"Column added: {table_name}.{column_name}")
    
    @staticmethod
    async def rename_column(
        session: AsyncSession,
        table_name: str,
        old_name: str,
        new_name: str,
    ) -> None:
        """
        Rename column.
        
        Note: This requires a brief lock. Consider using views for true zero-downtime.
        
        Args:
            session: Database session
            table_name: Table name
            old_name: Current column name
            new_name: New column name
        """
        sql = (
            f"ALTER TABLE {table_name} "
            f"RENAME COLUMN {old_name} TO {new_name}"
        )
        
        logger.info(
            "Renaming column",
            table=table_name,
            old_name=old_name,
            new_name=new_name,
        )
        
        await session.execute(text(sql))
        await session.commit()
    
    @staticmethod
    async def set_column_not_null(
        session: AsyncSession,
        table_name: str,
        column_name: str,
    ) -> None:
        """
        Set column to NOT NULL after data backfill.
        
        Args:
            session: Database session
            table_name: Table name
            column_name: Column name
        """
        sql = (
            f"ALTER TABLE {table_name} "
            f"ALTER COLUMN {column_name} SET NOT NULL"
        )
        
        logger.info(
            "Setting column NOT NULL",
            table=table_name,
            column=column_name,
        )
        
        await session.execute(text(sql))
        await session.commit()


class TableManager:
    """
    Safe table operations manager.
    """
    
    @staticmethod
    async def create_table_like(
        session: AsyncSession,
        new_table: str,
        existing_table: str,
    ) -> None:
        """
        Create new table with same structure as existing.
        
        Args:
            session: Database session
            new_table: New table name
            existing_table: Existing table to copy structure from
        """
        sql = (
            f"CREATE TABLE {new_table} (LIKE {existing_table} "
            f"INCLUDING ALL)"
        )
        
        logger.info(
            "Creating table like existing",
            new_table=new_table,
            existing_table=existing_table,
        )
        
        await session.execute(text(sql))
        await session.commit()
    
    @staticmethod
    async def create_view_alias(
        session: AsyncSession,
        view_name: str,
        table_name: str,
    ) -> None:
        """
        Create view as alias for table (for column renames).
        
        Args:
            session: Database session
            view_name: View name
            table_name: Table to alias
        """
        sql = f"CREATE OR REPLACE VIEW {view_name} AS SELECT * FROM {table_name}"
        
        logger.info(
            "Creating view alias",
            view=view_name,
            table=table_name,
        )
        
        await session.execute(text(sql))
        await session.commit()


# Migration helpers
def create_expand_contract_migration(
    table_name: str,
    column_name: str,
    column_type: str,
) -> ZeroDowntimeMigration:
    """
    Create expand-contract migration for adding a column.
    
    Args:
        table_name: Table name
        column_name: Column name
        column_type: Column type
        
    Returns:
        ZeroDowntimeMigration instance
    """
    migration = ZeroDowntimeMigration(f"add_{column_name}_to_{table_name}")
    
    # Phase 1: Add column as nullable
    migration.add_step(
        name="add_column",
        phase=MigrationPhase.PRE_DEPLOY,
        sql=f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}",
        rollback_sql=f"ALTER TABLE {table_name} DROP COLUMN IF EXISTS {column_name}",
        description=f"Add {column_name} column to {table_name}",
    )
    
    # Phase 3: Backfill data (if needed)
    # This would be customized based on requirements
    
    # Phase 4: Set NOT NULL (if needed)
    # migration.add_step(
    #     name="set_not_null",
    #     phase=MigrationPhase.CLEANUP,
    #     sql=f"ALTER TABLE {table_name} ALTER COLUMN {column_name} SET NOT NULL",
    #     rollback_sql=f"ALTER TABLE {table_name} ALTER COLUMN {column_name} DROP NOT NULL",
    # )
    
    return migration
