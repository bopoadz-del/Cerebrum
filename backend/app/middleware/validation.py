"""
Request/Response Validation Middleware

Provides additional validation layer for requests and responses
beyond Pydantic's built-in validation.
"""

import json
from typing import Any, Callable, Optional

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger

logger = get_logger(__name__)


class ValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for request/response validation.
    
    Provides:
    - Request body size validation
    - Content-Type validation
    - Response format validation
    """
    
    # Maximum request body size (10MB)
    MAX_BODY_SIZE = 10 * 1024 * 1024
    
    # Allowed content types
    ALLOWED_CONTENT_TYPES = {
        "application/json",
        "application/x-www-form-urlencoded",
        "multipart/form-data",
        "text/plain",
    }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with validation.
        
        Args:
            request: HTTP request
            call_next: Next middleware/handler
            
        Returns:
            HTTP response
        """
        # Validate request
        validation_error = await self._validate_request(request)
        if validation_error:
            return validation_error
        
        # Process request
        response = await call_next(request)
        
        # Validate response
        await self._validate_response(response)
        
        return response
    
    async def _validate_request(self, request: Request) -> Optional[Response]:
        """
        Validate incoming request.
        
        Args:
            request: HTTP request
            
        Returns:
            Error response if validation fails, None otherwise
        """
        # Check Content-Type for requests with body
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")
            
            # Extract main content type (ignore charset, etc.)
            main_content_type = content_type.split(";")[0].strip()
            
            if main_content_type and main_content_type not in self.ALLOWED_CONTENT_TYPES:
                logger.warning(
                    "Invalid Content-Type",
                    content_type=content_type,
                    path=request.url.path,
                )
                return JSONResponse(
                    status_code=415,
                    content={
                        "error": "Unsupported Media Type",
                        "detail": f"Content-Type '{content_type}' is not supported",
                    },
                )
        
        # Check Content-Length
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                if length > self.MAX_BODY_SIZE:
                    logger.warning(
                        "Request body too large",
                        content_length=length,
                        max_size=self.MAX_BODY_SIZE,
                        path=request.url.path,
                    )
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": "Payload Too Large",
                            "detail": f"Request body exceeds maximum size of {self.MAX_BODY_SIZE} bytes",
                        },
                    )
            except ValueError:
                pass
        
        return None
    
    async def _validate_response(self, response: Response) -> None:
        """
        Validate outgoing response.
        
        Args:
            response: HTTP response
        """
        # Ensure JSON responses have proper content type
        if isinstance(response, JSONResponse):
            response.headers["content-type"] = "application/json"


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to limit request body size.
    
    Provides early rejection of oversized requests before
    they consume server resources.
    """
    
    def __init__(self, app, max_size: int = 10 * 1024 * 1024) -> None:
        """
        Initialize middleware.
        
        Args:
            app: ASGI application
            max_size: Maximum body size in bytes
        """
        super().__init__(app)
        self.max_size = max_size
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with size limit.
        
        Args:
            request: HTTP request
            call_next: Next middleware/handler
            
        Returns:
            HTTP response
        """
        # Check Content-Length header
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                if length > self.max_size:
                    logger.warning(
                        "Request body too large",
                        content_length=length,
                        max_size=self.max_size,
                    )
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": "Payload Too Large",
                            "detail": f"Maximum request size is {self.max_size} bytes",
                        },
                    )
            except ValueError:
                pass
        
        return await call_next(request)


class JSONValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate JSON request bodies.
    
    Ensures JSON payloads are well-formed before reaching handlers.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with JSON validation.
        
        Args:
            request: HTTP request
            call_next: Next middleware/handler
            
        Returns:
            HTTP response
        """
        content_type = request.headers.get("content-type", "")
        
        # Only validate JSON content
        if "application/json" in content_type:
            try:
                body = await request.body()
                if body:
                    json.loads(body)
            except json.JSONDecodeError as e:
                logger.warning(
                    "Invalid JSON in request body",
                    error=str(e),
                    path=request.url.path,
                )
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "Bad Request",
                        "detail": f"Invalid JSON: {str(e)}",
                    },
                )
            
            # Reset body for next middleware
            async def receive():
                return {"type": "http.request", "body": body}
            
            request = Request(request.scope, receive, request._send)
        
        return await call_next(request)
