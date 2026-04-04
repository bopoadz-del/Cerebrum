"""
CORS Middleware Configuration

Provides Cross-Origin Resource Sharing configuration with
specific origin allowlisting for security.
"""

from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def setup_cors_middleware(app) -> None:
    """
    Configure and add CORS middleware to FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    # Log CORS configuration
    logger.info(
        "Configuring CORS middleware",
        origins=settings.cors_origins_list,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.cors_methods_list,
        allow_headers=settings.cors_headers_list,
        expose_headers=[
            "X-Request-ID",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
        ],
        max_age=600,  # 10 minutes
    )
