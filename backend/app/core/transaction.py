"""
Transaction Management

Provides decorators and context managers for database transactions
with automatic rollback on errors and proper session lifecycle management.
"""

import functools
from contextlib import asynccontextmanager
from typing import Any, Callable, TypeVar, cast, AsyncGenerator

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class TransactionError(Exception):
    """Custom exception for transaction errors."""
    
    def __init__(self, message: str, original_error: Exception = None) -> None:
        super().__init__(message)
        self.original_error = original_error
        self.message = message


def transactional(func: F) -> F:
    """
    Decorator for transactional database operations.
    
    Automatically manages session lifecycle with commit on success
    and rollback on error. The decorated function must accept a 'db'
    parameter of type AsyncSession.
    
    Args:
        func: Async function to wrap
        
    Returns:
        Wrapped function with transaction management
        
    Example:
        @transactional
        async def create_user(db: AsyncSession, user_data: dict) -> User:
            user = User(**user_data)
            db.add(user)
            return user
    """
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Find db session in arguments
        db = None
        for arg in args:
            if isinstance(arg, AsyncSession):
                db = arg
                break
        
        if db is None:
            db = kwargs.get('db')
        
        if db is None:
            raise TransactionError(
                "No database session found. Function must have 'db: AsyncSession' parameter."
            )
        
        # Check if already in transaction
        if db.in_transaction():
            # Already in transaction, just execute
            return await func(*args, **kwargs)
        
        # Start new transaction
        async with db.begin():
            try:
                logger.debug(
                    f"Starting transaction for {func.__name__}",
                    function=func.__name__,
                )
                result = await func(*args, **kwargs)
                logger.debug(
                    f"Transaction committed for {func.__name__}",
                    function=func.__name__,
                )
                return result
            except SQLAlchemyError as e:
                logger.error(
                    f"Transaction failed for {func.__name__}",
                    function=func.__name__,
                    error=str(e),
                )
                raise TransactionError(
                    f"Database transaction failed: {str(e)}",
                    original_error=e,
                ) from e
            except Exception as e:
                logger.error(
                    f"Unexpected error in transaction {func.__name__}",
                    function=func.__name__,
                    error=str(e),
                )
                raise
    
    return cast(F, wrapper)


@asynccontextmanager
async def transaction_scope(
    db: AsyncSession,
    readonly: bool = False,
) -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for transaction scope.
    
    Provides explicit transaction boundaries with automatic
    commit/rollback handling.
    
    Args:
        db: Database session
        readonly: Whether this is a read-only transaction
        
    Yields:
        Database session within transaction scope
        
    Example:
        async with transaction_scope(db) as tx:
            user = await tx.get(User, user_id)
            user.name = "New Name"
            # Auto-committed on exit
    """
    if db.in_transaction():
        # Already in transaction, yield as-is
        yield db
        return
    
    async with db.begin():
        try:
            logger.debug(
                "Starting transaction scope",
                readonly=readonly,
            )
            yield db
            
            if not readonly:
                logger.debug("Transaction committed")
            
        except SQLAlchemyError as e:
            logger.error(
                "Transaction failed, rolling back",
                error=str(e),
            )
            raise TransactionError(
                f"Database transaction failed: {str(e)}",
                original_error=e,
            ) from e
        except Exception as e:
            logger.error(
                "Unexpected error in transaction scope",
                error=str(e),
            )
            raise


class TransactionManager:
    """
    Manages database transactions with retry logic.
    
    Provides utilities for handling transactions with automatic
    retry on transient failures.
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 0.1,
    ) -> None:
        """
        Initialize transaction manager.
        
        Args:
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    async def execute(
        self,
        db: AsyncSession,
        operation: Callable[[AsyncSession], Any],
        readonly: bool = False,
    ) -> Any:
        """
        Execute operation with transaction and retry logic.
        
        Args:
            db: Database session
            operation: Async function to execute
            readonly: Whether this is read-only
            
        Returns:
            Result of operation
            
        Raises:
            TransactionError: If all retries fail
        """
        import asyncio
        
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                async with transaction_scope(db, readonly=readonly):
                    return await operation(db)
                    
            except SQLAlchemyError as e:
                last_error = e
                
                # Check if error is retryable
                if not self._is_retryable_error(e):
                    raise
                
                if attempt < self.max_retries - 1:
                    logger.warning(
                        f"Transaction failed, retrying ({attempt + 1}/{self.max_retries})",
                        error=str(e),
                    )
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                
        raise TransactionError(
            f"Transaction failed after {self.max_retries} attempts",
            original_error=last_error,
        )
    
    def _is_retryable_error(self, error: SQLAlchemyError) -> bool:
        """
        Check if error is retryable.
        
        Args:
            error: SQLAlchemy error
            
        Returns:
            True if error is transient and can be retried
        """
        error_str = str(error).lower()
        retryable_patterns = [
            "deadlock",
            "lock timeout",
            "connection reset",
            "connection closed",
            "temporary",
            "try again",
        ]
        return any(pattern in error_str for pattern in retryable_patterns)


# Global transaction manager instance
transaction_manager = TransactionManager()


async def run_in_transaction(
    db: AsyncSession,
    operation: Callable[[AsyncSession], Any],
    readonly: bool = False,
) -> Any:
    """
    Run operation in transaction with retry logic.
    
    Convenience function using global transaction manager.
    
    Args:
        db: Database session
        operation: Async function to execute
        readonly: Whether this is read-only
        
    Returns:
        Result of operation
    """
    return await transaction_manager.execute(db, operation, readonly)
