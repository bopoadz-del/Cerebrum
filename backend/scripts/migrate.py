"""
Migration Health Checks and Management

Provides utilities for running migrations with health checks,
rollback capabilities, and migration status reporting.
"""

import asyncio
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import typer
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import db_manager, get_db_context

logger = get_logger(__name__)
app = typer.Typer(help="Migration management utility")

# Alembic configuration
ALEMBIC_INI = Path(__file__).parent.parent / "app" / "db" / "migrations" / "alembic.ini"


def get_alembic_config() -> Config:
    """Get Alembic configuration."""
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("sqlalchemy.url", settings.sync_database_url)
    return config


class MigrationHealthChecker:
    """Migration health checker."""
    
    def __init__(self) -> None:
        """Initialize health checker."""
        self.alembic_cfg = get_alembic_config()
    
    async def check_database_connection(self) -> dict:
        """
        Check database connectivity.
        
        Returns:
            Health check result
        """
        try:
            async with get_db_context() as db:
                result = await db.execute(text("SELECT 1"))
                await result.scalar()
                
                return {
                    "status": "healthy",
                    "message": "Database connection successful",
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Database connection failed: {str(e)}",
            }
    
    async def check_migration_status(self) -> dict:
        """
        Check current migration status.
        
        Returns:
            Migration status information
        """
        try:
            async with get_db_context() as db:
                # Get current revision
                result = await db.execute(
                    text("SELECT version_num FROM alembic_version")
                )
                current_revision = result.scalar()
                
                # Get all available revisions
                script = ScriptDirectory.from_config(self.alembic_cfg)
                heads = script.get_heads()
                
                # Check if current is head
                is_current = current_revision in heads if current_revision else False
                
                return {
                    "status": "up_to_date" if is_current else "pending",
                    "current_revision": current_revision,
                    "head_revisions": heads,
                    "is_current": is_current,
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to check migration status: {str(e)}",
            }
    
    async def check_pending_migrations(self) -> List[dict]:
        """
        Get list of pending migrations.
        
        Returns:
            List of pending migration information
        """
        try:
            async with get_db_context() as db:
                # Get current revision
                result = await db.execute(
                    text("SELECT version_num FROM alembic_version")
                )
                current_revision = result.scalar()
                
                # Get all revisions
                script = ScriptDirectory.from_config(self.alembic_cfg)
                
                pending = []
                if current_revision:
                    # Get revisions after current
                    for rev in script.walk_revisions():
                        if rev.revision == current_revision:
                            break
                        pending.append({
                            "revision": rev.revision,
                            "down_revision": rev.down_revision,
                            "description": rev.doc,
                            "path": str(rev.path) if rev.path else None,
                        })
                
                return pending
        except Exception as e:
            logger.error(f"Failed to get pending migrations: {e}")
            return []
    
    async def run_health_checks(self) -> dict:
        """
        Run all health checks.
        
        Returns:
            Complete health check results
        """
        logger.info("Running migration health checks")
        
        db_health = await self.check_database_connection()
        migration_status = await self.check_migration_status()
        pending = await self.check_pending_migrations()
        
        overall_status = "healthy"
        if db_health["status"] != "healthy":
            overall_status = "unhealthy"
        elif migration_status.get("status") == "pending":
            overall_status = "warning"
        elif migration_status.get("status") == "error":
            overall_status = "unhealthy"
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "database": db_health,
            "migration": migration_status,
            "pending_migrations": pending,
            "pending_count": len(pending),
        }


@app.command()
def status() -> None:
    """Show current migration status."""
    async def run():
        db_manager.initialize()
        
        checker = MigrationHealthChecker()
        health = await checker.run_health_checks()
        
        # Print results
        typer.echo(f"\n{'='*60}")
        typer.echo(f"Migration Status: {health['status'].upper()}")
        typer.echo(f"{'='*60}")
        
        typer.echo(f"\nDatabase: {health['database']['status']}")
        if health['database'].get('message'):
            typer.echo(f"  {health['database']['message']}")
        
        migration = health['migration']
        typer.echo(f"\nMigration Status: {migration.get('status', 'unknown')}")
        typer.echo(f"  Current Revision: {migration.get('current_revision', 'None')}")
        typer.echo(f"  Head Revisions: {', '.join(migration.get('head_revisions', []))}")
        
        if health['pending_count'] > 0:
            typer.echo(f"\nPending Migrations ({health['pending_count']}):")
            for pending in health['pending_migrations']:
                typer.echo(f"  - {pending['revision']}: {pending['description']}")
        else:
            typer.echo("\nNo pending migrations")
        
        await db_manager.close()
    
    asyncio.run(run())


@app.command()
def upgrade(
    revision: str = typer.Argument("head", help="Target revision"),
    sql: bool = typer.Option(False, "--sql", help="Show SQL only"),
) -> None:
    """
    Run database migrations.
    
    Args:
        revision: Target revision (default: head)
        sql: Show SQL without executing
    """
    logger.info(f"Running migration upgrade to {revision}")
    
    alembic_cfg = get_alembic_config()
    
    try:
        if sql:
            command.upgrade(alembic_cfg, revision, sql=True)
        else:
            command.upgrade(alembic_cfg, revision)
            typer.echo(f"Migration to {revision} completed successfully")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        typer.echo(f"Migration failed: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def downgrade(
    revision: str = typer.Argument(..., help="Target revision"),
    sql: bool = typer.Option(False, "--sql", help="Show SQL only"),
) -> None:
    """
    Rollback database migrations.
    
    Args:
        revision: Target revision
        sql: Show SQL without executing
    """
    logger.info(f"Running migration downgrade to {revision}")
    
    alembic_cfg = get_alembic_config()
    
    try:
        if sql:
            command.downgrade(alembic_cfg, revision, sql=True)
        else:
            command.downgrade(alembic_cfg, revision)
            typer.echo(f"Migration rollback to {revision} completed successfully")
    except Exception as e:
        logger.error(f"Migration rollback failed: {e}")
        typer.echo(f"Migration rollback failed: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def revision(
    message: str = typer.Option(..., "--message", "-m", help="Migration message"),
    autogenerate: bool = typer.Option(True, "--autogenerate/--no-autogenerate", help="Autogenerate migration"),
) -> None:
    """
    Create new migration revision.
    
    Args:
        message: Migration description
        autogenerate: Automatically detect changes
    """
    logger.info(f"Creating new migration: {message}")
    
    alembic_cfg = get_alembic_config()
    
    try:
        command.revision(
            alembic_cfg,
            message=message,
            autogenerate=autogenerate,
        )
        typer.echo(f"Migration created: {message}")
    except Exception as e:
        logger.error(f"Failed to create migration: {e}")
        typer.echo(f"Failed to create migration: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def history(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show verbose output"),
) -> None:
    """Show migration history."""
    alembic_cfg = get_alembic_config()
    
    try:
        command.history(alembic_cfg, verbose=verbose)
    except Exception as e:
        typer.echo(f"Failed to show history: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def health() -> None:
    """Run migration health checks."""
    async def run():
        db_manager.initialize()
        
        checker = MigrationHealthChecker()
        health = await checker.run_health_checks()
        
        # Exit with appropriate code
        if health['status'] == 'healthy':
            typer.echo("Health check passed")
            sys.exit(0)
        elif health['status'] == 'warning':
            typer.echo(f"Health check warning: {health['pending_count']} pending migrations")
            sys.exit(0)  # Warning is not a failure
        else:
            typer.echo(f"Health check failed: {health['database'].get('message', 'Unknown error')}")
            sys.exit(1)
        
        await db_manager.close()
    
    asyncio.run(run())


if __name__ == "__main__":
    app()
