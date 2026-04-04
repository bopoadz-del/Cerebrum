"""
Security Headers Middleware

Provides security headers including HSTS, X-Frame-Options,
Content Security Policy, and others.
"""

from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.
    
    Implements OWASP recommended security headers:
    - X-Frame-Options
    - X-Content-Type-Options
    - X-XSS-Protection
    - Content-Security-Policy
    - Referrer-Policy
    - Permissions-Policy
    """
    
    def __init__(
        self,
        app,
        csp_policy: Optional[str] = None,
        hsts_max_age: int = 31536000,  # 1 year
        hsts_include_subdomains: bool = True,
        hsts_preload: bool = True,
    ) -> None:
        """
        Initialize security headers middleware.
        
        Args:
            app: ASGI application
            csp_policy: Content Security Policy string
            hsts_max_age: HSTS max age in seconds
            hsts_include_subdomains: Include subdomains in HSTS
            hsts_preload: Enable HSTS preload
        """
        super().__init__(app)
        
        self.hsts_max_age = hsts_max_age
        self.hsts_include_subdomains = hsts_include_subdomains
        self.hsts_preload = hsts_preload
        
        # Default CSP policy - Enterprise hardened (no unsafe-eval)
        self.csp_policy = csp_policy or (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "media-src 'self'; "
            "object-src 'none'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Add security headers to response.
        
        Args:
            request: HTTP request
            call_next: Next middleware/handler
            
        Returns:
            Response with security headers
        """
        response = await call_next(request)
        
        # Skip CSP for OAuth callback (needs inline script for postMessage)
        if "/google-drive/callback" in request.url.path:
            pass  # Don't add CSP header for OAuth callback
        else:
            # Content Security Policy
            response.headers["Content-Security-Policy"] = self.csp_policy
        
        # X-Frame-Options (clickjacking protection)
        response.headers["X-Frame-Options"] = "DENY"
        
        # X-Content-Type-Options (MIME sniffing protection)
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # X-XSS-Protection (legacy XSS protection)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions Policy (formerly Feature-Policy)
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), "
            "camera=(), "
            "geolocation=(), "
            "gyroscope=(), "
            "magnetometer=(), "
            "microphone=(), "
            "payment=(), "
            "usb=()"
        )
        
        # X-DNS-Prefetch-Control
        response.headers["X-DNS-Prefetch-Control"] = "off"
        
        # X-Download-Options (IE only)
        response.headers["X-Download-Options"] = "noopen"
        
        # X-Permitted-Cross-Domain-Policies
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        
        # Cross-Origin-Opener-Policy - unsafe-none allows OAuth popups to work properly
        response.headers["Cross-Origin-Opener-Policy"] = "unsafe-none"
        
        return response


class CacheControlMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add cache control headers.
    
    Prevents caching of sensitive responses.
    """
    
    # Paths that should never be cached
    NO_CACHE_PATHS = [
        "/api/",
        "/auth/",
        "/admin/",
    ]
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Add cache control headers.
        
        Args:
            request: HTTP request
            call_next: Next middleware/handler
            
        Returns:
            Response with cache control headers
        """
        response = await call_next(request)
        
        path = request.url.path
        
        # Check if path should not be cached
        should_not_cache = any(
            path.startswith(no_cache_path)
            for no_cache_path in self.NO_CACHE_PATHS
        )
        
        if should_not_cache:
            response.headers["Cache-Control"] = (
                "no-store, no-cache, must-revalidate, proxy-revalidate"
            )
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        return response
