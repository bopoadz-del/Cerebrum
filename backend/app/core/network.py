"""
Network Security Configurations

Provides network security settings including allowed hosts,
trusted proxies, and IP filtering.
"""

import ipaddress
from typing import List, Optional, Set

from fastapi import HTTPException, Request, status

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class NetworkSecurity:
    """
    Network security manager.
    
    Provides IP filtering, allowed hosts validation, and
    trusted proxy handling.
    """
    
    def __init__(self) -> None:
        """Initialize network security."""
        # Allowed hosts (for Host header validation)
        self.allowed_hosts: Set[str] = self._load_allowed_hosts()
        
        # Trusted proxy IPs
        self.trusted_proxies: Set[ipaddress.IPv4Network | ipaddress.IPv6Network] = (
            self._load_trusted_proxies()
        )
        
        # Blocked IP ranges
        self.blocked_ranges: Set[ipaddress.IPv4Network | ipaddress.IPv6Network] = (
            self._load_blocked_ranges()
        )
    
    def _load_allowed_hosts(self) -> Set[str]:
        """Load allowed hosts from configuration."""
        hosts = {
            "localhost",
            "127.0.0.1",
            "0.0.0.0",
            "[::1]",
        }
        
        # Add configured hosts
        if hasattr(settings, "ALLOWED_HOSTS"):
            hosts.update(settings.ALLOWED_HOSTS)
        
        return hosts
    
    def _load_trusted_proxies(self) -> Set[ipaddress.IPv4Network | ipaddress.IPv6Network]:
        """Load trusted proxy IP ranges."""
        proxies = set()
        
        # Common private networks
        proxy_ranges = [
            "10.0.0.0/8",
            "172.16.0.0/12",
            "192.168.0.0/16",
            "127.0.0.0/8",
            "::1/128",
        ]
        
        for range_str in proxy_ranges:
            try:
                proxies.add(ipaddress.ip_network(range_str))
            except ValueError:
                logger.warning(f"Invalid proxy range: {range_str}")
        
        return proxies
    
    def _load_blocked_ranges(self) -> Set[ipaddress.IPv4Network | ipaddress.IPv6Network]:
        """Load blocked IP ranges."""
        blocked = set()
        
        # Add configured blocked ranges
        if hasattr(settings, "BLOCKED_IP_RANGES"):
            for range_str in settings.BLOCKED_IP_RANGES:
                try:
                    blocked.add(ipaddress.ip_network(range_str))
                except ValueError:
                    logger.warning(f"Invalid blocked range: {range_str}")
        
        return blocked
    
    def is_host_allowed(self, host: str) -> bool:
        """
        Check if host is allowed.
        
        Args:
            host: Host header value
            
        Returns:
            True if host is allowed
        """
        # Remove port if present
        if ":" in host:
            host = host.split(":")[0]
        
        # Check exact match
        if host in self.allowed_hosts:
            return True
        
        # Check wildcard domains
        for allowed in self.allowed_hosts:
            if allowed.startswith("*."):
                domain = allowed[2:]
                if host.endswith(domain):
                    return True
        
        return False
    
    def is_ip_blocked(self, ip: str) -> bool:
        """
        Check if IP address is blocked.
        
        Args:
            ip: IP address string
            
        Returns:
            True if IP is blocked
        """
        try:
            addr = ipaddress.ip_address(ip)
            
            for blocked_range in self.blocked_ranges:
                if addr in blocked_range:
                    return True
            
            return False
            
        except ValueError:
            logger.warning(f"Invalid IP address: {ip}")
            return False
    
    def get_client_ip(self, request: Request) -> str:
        """
        Get client IP address from request.
        
        Handles X-Forwarded-For and X-Real-IP headers from trusted proxies.
        
        Args:
            request: HTTP request
            
        Returns:
            Client IP address
        """
        # Get direct connection IP
        client_ip = request.client.host if request.client else "127.0.0.1"
        
        # Check for forwarded headers
        forwarded_for = request.headers.get("x-forwarded-for")
        real_ip = request.headers.get("x-real-ip")
        
        # If request comes from trusted proxy, use forwarded IP
        if self._is_trusted_proxy(client_ip):
            if forwarded_for:
                # X-Forwarded-For can contain multiple IPs, use the first (client)
                forwarded_ips = [ip.strip() for ip in forwarded_for.split(",")]
                if forwarded_ips:
                    return forwarded_ips[0]
            
            if real_ip:
                return real_ip
        
        return client_ip
    
    def _is_trusted_proxy(self, ip: str) -> bool:
        """
        Check if IP is a trusted proxy.
        
        Args:
            ip: IP address
            
        Returns:
            True if IP is a trusted proxy
        """
        try:
            addr = ipaddress.ip_address(ip)
            
            for proxy_range in self.trusted_proxies:
                if addr in proxy_range:
                    return True
            
            return False
            
        except ValueError:
            return False
    
    def validate_request(self, request: Request) -> None:
        """
        Validate incoming request for network security.
        
        Args:
            request: HTTP request
            
        Raises:
            HTTPException: If request is not allowed
        """
        # Get client IP
        client_ip = self.get_client_ip(request)
        
        # Check if IP is blocked
        if self.is_ip_blocked(client_ip):
            logger.warning(
                "Blocked IP attempted access",
                ip=client_ip,
                path=request.url.path,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )
        
        # Validate Host header in production
        if settings.is_production:
            host = request.headers.get("host", "")
            if not self.is_host_allowed(host):
                logger.warning(
                    "Invalid Host header",
                    host=host,
                    ip=client_ip,
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid Host header",
                )


# Global network security instance
network_security = NetworkSecurity()


def get_client_ip(request: Request) -> str:
    """Get client IP convenience function."""
    return network_security.get_client_ip(request)


def is_ip_blocked(ip: str) -> bool:
    """Check if IP is blocked convenience function."""
    return network_security.is_ip_blocked(ip)
