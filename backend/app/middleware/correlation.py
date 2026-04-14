"""
Correlation ID middleware for distributed tracing.
"""

import uuid
from fastapi import Request


async def add_correlation_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response
