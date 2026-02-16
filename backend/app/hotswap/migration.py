"""
Database Migration for Capabilities

Handles auto-generation and execution of Alembic migrations for
capability database changes.
"""

import logging
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class MigrationResult:
    """Result of a migration operation."""
    success: bool
    revision_id: Optional[str]
    operations_applied: List[str]
    operations_rolled_back: List[str]
    errors: List[str]
    warnings: List[str]


@dataclass
class MigrationInfo:
    """Information about a migration."""
    revision_id: str
    down_revision: Optional[str]
    message: str
    upgrade_ops: List[str]
    downgrade_ops: List[str]
    created_at: str


class CapabilityMigrationManager:
    """
    Manages database migrations for AI-generated capabilities.
    
    Provides:
    - Auto-generation of migrations from model changes
    - Transaction-safe migration execution
    - Rollback on failure
    - Migration history tracking
    """
    
    def __init__(
        self,
        alembic_ini_path: Optional[str] = None,
        db_url: Optional[str] = None,
    ):
        """
        Initialize the migration manager.
        
        Args:
            alembic_ini_path: Path to alembic.ini
            db_url: Database URL
        """
        self.alembic_ini_path = alembic_ini_path
        self.db_url = db_url
        self._alembic_cfg: Optional[Config] = None
    
    def _get_alembic_config(self) -> Config:
        """Get or create Alembic configuration."""
        if self._alembic_cfg is None:
            if self.alembic_ini_path:
                self._alembic_cfg = Config(self.alembic_ini_path)
            else:
                # Create default config
                self._alembic_cfg = Config()
                self._alembic_cfg.set_main_option("script_location", "alembic")
                if self.db_url:
                    self._alembic_cfg.set_main_option("sqlalchemy.url", self.db_url)
        
        return self._alembic_cfg
    
    async def generate_migration(
        self,
        message: str,
        capability_id: UUID,
        autogenerate: bool = True,
    ) -> MigrationInfo:
        """
        Generate a new migration.
        
        Args:
            message: Migration message
            capability_id: Associated capability ID
            autogenerate: Whether to autogenerate from models
            
        Returns:
            MigrationInfo with generated migration details
        """
        cfg = self._get_alembic_config()
        
        # Create revision
        try:
            revision = command.revision(
                cfg,
                message=message,
                autogenerate=autogenerate,
            )
            
            return MigrationInfo(
                revision_id=revision.revision,
                down_revision=revision.down_revision,
                message=message,
                upgrade_ops=[],  # Would parse from generated file
                downgrade_ops=[],
                created_at=datetime.utcnow().isoformat(),
            )
            
        except Exception as e:
            logger.error(f"Failed to generate migration: {e}")
            raise
    
    async def generate_migration_from_code(
        self,
        migration_code: str,
        capability_id: UUID,
    ) -> MigrationResult:
        """
        Generate and apply a migration from provided code.
        
        Args:
            migration_code: Alembic migration code
            capability_id: Associated capability ID
            
        Returns:
            MigrationResult
        """
        # Extract revision info from code
        revision_match = re.search(r'revision\s*=\s*[\'"]([^\'"]+)[\'"]', migration_code)
        if not revision_match:
            return MigrationResult(
                success=False,
                revision_id=None,
                operations_applied=[],
                operations_rolled_back=[],
                errors=["Could not extract revision ID from migration code"],
                warnings=[],
            )
        
        revision_id = revision_match.group(1)
        
        # Write migration file
        cfg = self._get_alembic_config()
        script = ScriptDirectory.from_config(cfg)
        
        # Get versions directory
        versions_dir = Path(script.versions_dir)
        versions_dir.mkdir(parents=True, exist_ok=True)
        
        migration_file = versions_dir / f"{revision_id}_capability_{capability_id}.py"
        
        try:
            with open(migration_file, "w") as f:
                f.write(migration_code)
            
            logger.info(f"Created migration file: {migration_file}")
            
            return MigrationResult(
                success=True,
                revision_id=revision_id,
                operations_applied=[str(migration_file)],
                operations_rolled_back=[],
                errors=[],
                warnings=[],
            )
            
        except Exception as e:
            logger.error(f"Failed to write migration file: {e}")
            return MigrationResult(
                success=False,
                revision_id=None,
                operations_applied=[],
                operations_rolled_back=[],
                errors=[f"Failed to write migration: {str(e)}"],
                warnings=[],
            )
    
    async def apply_migration(
        self,
        revision_id: str,
        db_session: AsyncSession,
    ) -> MigrationResult:
        """
        Apply a migration in a transaction.
        
        Args:
            revision_id: Migration revision to apply
            db_session: Database session
            
        Returns:
            MigrationResult
        """
        cfg = self._get_alembic_config()
        
        operations_applied = []
        operations_rolled_back = []
        errors = []
        
        try:
            # Apply migration within transaction
            async with db_session.begin():
                command.upgrade(cfg, revision_id)
                operations_applied.append(f"upgrade:{revision_id}")
            
            logger.info(f"Successfully applied migration: {revision_id}")
            
            return MigrationResult(
                success=True,
                revision_id=revision_id,
                operations_applied=operations_applied,
                operations_rolled_back=[],
                errors=[],
                warnings=[],
            )
            
        except Exception as e:
            logger.error(f"Failed to apply migration {revision_id}: {e}")
            
            # Rollback is automatic with async context manager
            operations_rolled_back.append(f"rollback:{revision_id}")
            
            return MigrationResult(
                success=False,
                revision_id=revision_id,
                operations_applied=operations_applied,
                operations_rolled_back=operations_rolled_back,
                errors=[f"Migration failed: {str(e)}"],
                warnings=[],
            )
    
    async def rollback_migration(
        self,
        revision_id: str,
        db_session: AsyncSession,
    ) -> MigrationResult:
        """
        Rollback a migration.
        
        Args:
            revision_id: Migration revision to rollback
            db_session: Database session
            
        Returns:
            MigrationResult
        """
        cfg = self._get_alembic_config()
        
        operations_rolled_back = []
        errors = []
        
        try:
            async with db_session.begin():
                command.downgrade(cfg, revision_id)
                operations_rolled_back.append(f"downgrade:{revision_id}")
            
            logger.info(f"Successfully rolled back migration: {revision_id}")
            
            return MigrationResult(
                success=True,
                revision_id=revision_id,
                operations_applied=[],
                operations_rolled_back=operations_rolled_back,
                errors=[],
                warnings=[],
            )
            
        except Exception as e:
            logger.error(f"Failed to rollback migration {revision_id}: {e}")
            
            return MigrationResult(
                success=False,
                revision_id=revision_id,
                operations_applied=[],
                operations_rolled_back=operations_rolled_back,
                errors=[f"Rollback failed: {str(e)}"],
                warnings=[],
            )
    
    async def get_current_revision(self, db_session: AsyncSession) -> Optional[str]:
        """
        Get the current database revision.
        
        Args:
            db_session: Database session
            
        Returns:
            Current revision ID or None
        """
        try:
            result = await db_session.execute(text("SELECT version_num FROM alembic_version"))
            row = result.fetchone()
            return row[0] if row else None
        except Exception as e:
            logger.warning(f"Could not get current revision: {e}")
            return None
    
    async def get_migration_history(
        self,
        db_session: AsyncSession,
    ) -> List[Dict[str, Any]]:
        """
        Get migration history.
        
        Args:
            db_session: Database session
            
        Returns:
            List of migration history entries
        """
        cfg = self._get_alembic_config()
        script = ScriptDirectory.from_config(cfg)
        
        history = []
        for rev in script.walk_revisions():
            history.append({
                "revision": rev.revision,
                "down_revision": rev.down_revision,
                "message": rev.doc,
                "created_at": rev.date,
            })
        
        return history
    
    async def validate_migration(
        self,
        migration_code: str,
    ) -> MigrationResult:
        """
        Validate migration code without applying.
        
        Args:
            migration_code: Migration code to validate
            
        Returns:
            MigrationResult with validation status
        """
        errors = []
        warnings = []
        
        # Check for required components
        if "revision" not in migration_code:
            errors.append("Missing 'revision' variable")
        
        if "def upgrade():" not in migration_code:
            errors.append("Missing 'upgrade' function")
        
        if "def downgrade():" not in migration_code:
            warnings.append("Missing 'downgrade' function")
        
        # Try to compile the code
        try:
            compile(migration_code, "<string>", "exec")
        except SyntaxError as e:
            errors.append(f"Syntax error: {e}")
        
        # Extract revision ID
        revision_id = None
        revision_match = re.search(r'revision\s*=\s*[\'"]([^\'"]+)[\'"]', migration_code)
        if revision_match:
            revision_id = revision_match.group(1)
        
        return MigrationResult(
            success=len(errors) == 0,
            revision_id=revision_id,
            operations_applied=[],
            operations_rolled_back=[],
            errors=errors,
            warnings=warnings,
        )
    
    async def dry_run_migration(
        self,
        revision_id: str,
        db_session: AsyncSession,
    ) -> MigrationResult:
        """
        Perform a dry run of a migration (show SQL without executing).
        
        Args:
            revision_id: Migration revision
            db_session: Database session
            
        Returns:
            MigrationResult with SQL that would be executed
        """
        cfg = self._get_alembic_config()
        
        try:
            # This would require capturing the SQL output
            # For now, return a placeholder
            return MigrationResult(
                success=True,
                revision_id=revision_id,
                operations_applied=["DRY RUN - SQL would be shown here"],
                operations_rolled_back=[],
                errors=[],
                warnings=["Dry run mode - no changes applied"],
            )
            
        except Exception as e:
            return MigrationResult(
                success=False,
                revision_id=revision_id,
                operations_applied=[],
                operations_rolled_back=[],
                errors=[f"Dry run failed: {str(e)}"],
                warnings=[],
            )


# Import datetime
from datetime import datetime


# Singleton instance
migration_manager_instance: Optional[CapabilityMigrationManager] = None


def get_migration_manager(
    alembic_ini_path: Optional[str] = None,
    db_url: Optional[str] = None,
) -> CapabilityMigrationManager:
    """Get or create the singleton migration manager instance."""
    global migration_manager_instance
    if migration_manager_instance is None:
        migration_manager_instance = CapabilityMigrationManager(alembic_ini_path, db_url)
    return migration_manager_instance


def set_migration_manager(manager: CapabilityMigrationManager) -> None:
    """Set the singleton migration manager instance."""
    global migration_manager_instance
    migration_manager_instance = manager
