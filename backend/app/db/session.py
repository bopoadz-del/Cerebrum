"""
PostgreSQL Database Session Management

This module provides SQLAlchemy database session management with connection pooling,
async support, and proper lifecycle handling for the Cerebrum AI platform.
"""

from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Connection pool configuration
# pool_size: Number of persistent connections
# max_overflow: Additional connections allowed beyond pool_size
# pool_recycle: Seconds after which connections are recycled
# pool_pre_ping: Verify connection validity before use
POOL_CONFIG = {
    "pool_size": 20,
    "max_overflow": 0,
    "pool_recycle": 3600,
    "pool_pre_ping": True,
    "echo": settings.DEBUG,
}


class DatabaseManager:
    """
    Manages database connections and sessions.
    
    Provides both sync and async session factories with proper
    connection pooling and lifecycle management.
    """
    
    def __init__(self) -> None:
        """Initialize database manager with connection pool."""
        self._async_engine: Optional[object] = None
        self._async_session_factory: Optional[async_sessionmaker] = None
        self._sync_engine: Optional[object] = None
        self._sync_session_factory: Optional[sessionmaker] = None
        
    def initialize(self, database_url: Optional[str] = None) -> None:
        """
        Initialize database engines and session factories.
        
        Args:
            database_url: Optional database URL override
        """
        db_url = database_url or settings.DATABASE_URL
        
        if not db_url:
            raise ValueError("Database URL not configured")
        
        # Convert to async URL if needed
        async_url = self._make_async_url(db_url)
        sync_url = self._make_sync_url(db_url)
        
        logger.info(
            "Initializing database connection pool",
            pool_size=POOL_CONFIG["pool_size"],
            max_overflow=POOL_CONFIG["max_overflow"],
        )
        
        # Create async engine with connection pooling
        self._async_engine = create_async_engine(
            async_url,
            **POOL_CONFIG,
            future=True,
        )
        
        # Create async session factory
        self._async_session_factory = async_sessionmaker(
            self._async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
        
        # Create sync engine for synchronous operations
        self._sync_engine = create_engine(
            sync_url,
            **POOL_CONFIG,
            future=True,
        )
        
        # Create sync session factory
        self._sync_session_factory = sessionmaker(
            self._sync_engine,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
        
        logger.info("Database connection pool initialized successfully")
    
    def _make_async_url(self, url: str) -> str:
        """
        Convert PostgreSQL URL to async version.
        
        Args:
            url: Database URL
            
        Returns:
            Async-compatible database URL
        """
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url
    
    def _make_sync_url(self, url: str) -> str:
        """
        Convert PostgreSQL URL to sync version.
        
        Args:
            url: Database URL
            
        Returns:
            Sync-compatible database URL
        """
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        # Remove asyncpg if present
        if url.startswith("postgresql+asyncpg://"):
            url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
        return url
    
    @property
    def async_engine(self) -> object:
        """Get async engine instance."""
        if self._async_engine is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._async_engine
    
    @property
    def async_session_factory(self) -> async_sessionmaker:
        """Get async session factory."""
        if self._async_session_factory is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._async_session_factory
    
    @property
    def sync_engine(self) -> object:
        """Get sync engine instance."""
        if self._sync_engine is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._sync_engine
    
    @property
    def sync_session_factory(self) -> sessionmaker:
        """Get sync session factory."""
        if self._sync_session_factory is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._sync_session_factory
    
    async def close(self) -> None:
        """Close all database connections."""
        if self._async_engine:
            logger.info("Closing async database connection pool")
            await self._async_engine.dispose()
            self._async_engine = None
            self._async_session_factory = None
        if self._sync_engine:
            logger.info("Closing sync database connection pool")
            self._sync_engine.dispose()
            self._sync_engine = None
            self._sync_session_factory = None
        logger.info("Database connection pool closed")


# Global database manager instance
db_manager = DatabaseManager()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session for dependency injection.
    
    Yields:
        AsyncSession: Database session
        
    Example:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db_session)):
            return await db.execute(select(Item))
    """
    if db_manager.async_session_factory is None:
        raise RuntimeError("Database not initialized")
    
    async with db_manager.async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database sessions.
    
    Use this for operations outside of FastAPI dependency injection.
    
    Yields:
        AsyncSession: Database session
        
    Example:
        async with get_db_context() as db:
            result = await db.execute(select(Item))
    """
    if db_manager.async_session_factory is None:
        raise RuntimeError("Database not initialized")
    
    async with db_manager.async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@contextmanager
def get_sync_db_context() -> Generator[Session, None, None]:
    """
    Synchronous context manager for database sessions.
    
    Use this for synchronous operations outside of FastAPI.
    
    Yields:
        Session: Database session
        
    Example:
        with get_sync_db_context() as db:
            result = db.execute(select(Item))
    """
    if db_manager.sync_session_factory is None:
        raise RuntimeError("Database not initialized")
    
    session = db_manager.sync_session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


async def init_db() -> None:
    """Initialize database connection pool."""
    db_manager.initialize()


async def close_db() -> None:
    """Close database connection pool."""
    await db_manager.close()
