"""
Request logging middleware.
"""

import time
from fastapi import Request

from app.core.logging import get_logger

logger = get_logger(__name__)


async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = (time.time() - start) * 1000
    logger.info(
        "Request completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=f"{duration:.2f}",
        client_host=request.client.host if request.client else None,
    )
    return response
