"""
Global Exception Handlers

Provides centralized exception handling for the application
with proper error responses and logging.
"""

import traceback
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from app.core.config import settings
from app.core.logging import get_logger
from app.core.sentry import capture_exception

logger = get_logger(__name__)


class AppException(Exception):
    """Base application exception."""
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Initialize exception.
        
        Args:
            message: Error message
            status_code: HTTP status code
            error_code: Application error code
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or f"ERR_{status_code}"
        self.details = details or {}


class NotFoundException(AppException):
    """Resource not found exception."""
    
    def __init__(self, resource: str, resource_id: Optional[str] = None) -> None:
        """Initialize not found exception."""
        message = f"{resource} not found"
        if resource_id:
            message = f"{resource} with id '{resource_id}' not found"
        
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="ERR_NOT_FOUND",
            details={"resource": resource, "resource_id": resource_id},
        )


class ConflictException(AppException):
    """Resource conflict exception."""
    
    def __init__(self, message: str) -> None:
        """Initialize conflict exception."""
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code="ERR_CONFLICT",
        )


class UnauthorizedException(AppException):
    """Unauthorized access exception."""
    
    def __init__(self, message: str = "Unauthorized") -> None:
        """Initialize unauthorized exception."""
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="ERR_UNAUTHORIZED",
        )


class ForbiddenException(AppException):
    """Forbidden access exception."""
    
    def __init__(self, message: str = "Forbidden") -> None:
        """Initialize forbidden exception."""
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="ERR_FORBIDDEN",
        )


class ValidationException(AppException):
    """Validation error exception."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Initialize validation exception."""
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="ERR_VALIDATION",
            details=details,
        )


def setup_exception_handlers(app: FastAPI) -> None:
    """
    Set up global exception handlers for the application.
    
    Args:
        app: FastAPI application instance
    """
    
    @app.exception_handler(AppException)
    async def handle_app_exception(request: Request, exc: AppException) -> JSONResponse:
        """Handle application exceptions."""
        logger.warning(
            f"Application exception: {exc.message}",
            error_code=exc.error_code,
            status_code=exc.status_code,
            path=request.url.path,
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.error_code,
                "message": exc.message,
                "details": exc.details,
            },
        )
    
    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        """Handle request validation errors."""
        logger.warning(
            "Request validation error",
            errors=exc.errors(),
            path=request.url.path,
        )
        
        # Format validation errors
        errors = []
        for error in exc.errors():
            errors.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            })
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "ERR_VALIDATION",
                "message": "Request validation failed",
                "details": {"errors": errors},
            },
        )
    
    @app.exception_handler(ValidationError)
    async def handle_pydantic_validation_error(
        request: Request,
        exc: ValidationError,
    ) -> JSONResponse:
        """Handle Pydantic validation errors."""
        logger.warning(
            "Pydantic validation error",
            errors=exc.errors(),
            path=request.url.path,
        )
        
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "ERR_VALIDATION",
                "message": "Validation failed",
                "details": {"errors": exc.errors()},
            },
        )
    
    @app.exception_handler(SQLAlchemyError)
    async def handle_database_error(
        request: Request,
        exc: SQLAlchemyError,
    ) -> JSONResponse:
        """Handle database errors."""
        logger.error(
            "Database error",
            error=str(exc),
            path=request.url.path,
        )
        
        # Capture in Sentry
        capture_exception(exc, path=request.url.path)
        
        # Don't expose database details in production
        message = "Database error"
        if settings.is_development:
            message = str(exc)
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "ERR_DATABASE", "detail": str(exc),
                "detail": str(exc),
                "message": message,
            },
        )
    
    @app.exception_handler(IntegrityError)
    async def handle_integrity_error(
        request: Request,
        exc: IntegrityError,
    ) -> JSONResponse:
        """Handle database integrity errors."""
        logger.warning(
            "Database integrity error",
            error=str(exc),
            path=request.url.path,
        )
        
        # Parse common integrity errors
        error_str = str(exc).lower()
        
        if "unique constraint" in error_str or "duplicate" in error_str:
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "error": "ERR_DUPLICATE",
                    "message": "Resource already exists",
                },
            )
        
        if "foreign key constraint" in error_str:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": "ERR_REFERENCE",
                    "message": "Referenced resource does not exist",
                },
            )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "ERR_DATABASE", "detail": str(exc),
                "detail": str(exc),
                "message": "Database constraint violation",
            },
        )
    
    @app.exception_handler(Exception)
    async def handle_generic_exception(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """Handle all unhandled exceptions."""
        logger.error(
            "Unhandled exception",
            error=str(exc),
            traceback=traceback.format_exc(),
            path=request.url.path,
        )
        
        # Capture in Sentry
        capture_exception(exc, path=request.url.path)
        
        # Don't expose internal details in production
        message = "Internal server error"
        if settings.is_development:
            message = str(exc)
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "ERR_INTERNAL",
                "message": message,
            },
        )
