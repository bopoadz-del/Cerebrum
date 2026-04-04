"""
Wildcard SSL and Tenant Subdomain Routing
Enterprise-grade multi-tenant subdomain isolation
"""
import os
import re
import ssl
import logging
from typing import Optional, Dict, List, Callable, Any
from dataclasses import dataclass
from enum import Enum
import certbot.main
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from datetime import datetime, timedelta
import idna

logger = logging.getLogger(__name__)


class SubdomainPattern(Enum):
    """Subdomain routing patterns"""
    TENANT_SLUG = "{tenant}.cerebrum.ai"  # tenant.cerebrum.ai
    CUSTOM_DOMAIN = "{domain}"  # custom domain
    PROJECT_SUBDOMAIN = "{tenant}-{project}.cerebrum.ai"
    REGION_TENANT = "{tenant}.{region}.cerebrum.ai"


@dataclass
class TenantRoutingConfig:
    """Tenant routing configuration"""
    tenant_id: str
    subdomain: str
    custom_domain: Optional[str] = None
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None
    is_active: bool = True
    created_at: datetime = None
    settings: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.settings is None:
            self.settings = {}


class WildcardSSLManager:
    """Manages wildcard SSL certificates"""
    
    def __init__(self, base_domain: str = "cerebrum.ai",
                 cert_dir: str = "/etc/letsencrypt"):
        self.base_domain = base_domain
        self.cert_dir = cert_dir
        self.wildcard_domain = f"*.{base_domain}"
        self._cert_cache: Dict[str, Dict] = {}
    
    def generate_self_signed_wildcard(self, output_dir: str = "/tmp/certs") -> tuple:
        """Generate self-signed wildcard certificate for development"""
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        
        # Build subject
        subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Cerebrum AI"),
            x509.NameAttribute(NameOID.COMMON_NAME, self.wildcard_domain),
        ])
        
        # Build certificate
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            subject
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=365)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName(self.base_domain),
                x509.DNSName(self.wildcard_domain),
            ]),
            critical=False
        ).sign(private_key, hashes.SHA256())
        
        # Save certificate
        cert_path = os.path.join(output_dir, "wildcard.crt")
        key_path = os.path.join(output_dir, "wildcard.key")
        
        os.makedirs(output_dir, exist_ok=True)
        
        with open(cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        
        with open(key_path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        logger.info(f"Generated self-signed wildcard cert for {self.wildcard_domain}")
        return cert_path, key_path
    
    def request_letsencrypt_wildcard(self, email: str,
                                     staging: bool = False) -> tuple:
        """Request Let's Encrypt wildcard certificate"""
        domains = [self.base_domain, self.wildcard_domain]
        
        args = [
            'certonly',
            '--manual',
            '--preferred-challenges=dns',
            '--agree-tos',
            f'--email={email}',
        ]
        
        if staging:
            args.append('--staging')
        
        for domain in domains:
            args.extend(['-d', domain])
        
        try:
            certbot.main.main(args)
            
            cert_path = f"{self.cert_dir}/live/{self.base_domain}/fullchain.pem"
            key_path = f"{self.cert_dir}/live/{self.base_domain}/privkey.pem"
            
            logger.info(f"Obtained Let's Encrypt wildcard cert for {self.base_domain}")
            return cert_path, key_path
            
        except Exception as e:
            logger.error(f"Failed to obtain Let's Encrypt cert: {e}")
            raise
    
    def get_certificate_info(self, domain: str) -> Dict:
        """Get certificate information"""
        cert_path = f"{self.cert_dir}/live/{domain}/cert.pem"
        
        if not os.path.exists(cert_path):
            return {'exists': False}
        
        with open(cert_path, 'rb') as f:
            cert = x509.load_pem_x509_certificate(f.read())
        
        return {
            'exists': True,
            'subject': cert.subject.rfc4514_string(),
            'issuer': cert.issuer.rfc4514_string(),
            'not_before': cert.not_valid_before,
            'not_after': cert.not_valid_after,
            'serial_number': cert.serial_number,
            'days_until_expiry': (cert.not_valid_after - datetime.utcnow()).days
        }
    
    def should_renew(self, domain: str, days_before_expiry: int = 30) -> bool:
        """Check if certificate should be renewed"""
        info = self.get_certificate_info(domain)
        
        if not info['exists']:
            return True
        
        return info['days_until_expiry'] <= days_before_expiry


class SubdomainRouter:
    """Routes requests to tenant subdomains"""
    
    # Subdomain pattern regex
    SUBDOMAIN_PATTERN = re.compile(r'^(?:(?P<tenant>[a-z0-9-]+)\.)?(?P<domain>.+)$')
    
    def __init__(self, base_domain: str = "cerebrum.ai"):
        self.base_domain = base_domain
        self._tenant_routes: Dict[str, TenantRoutingConfig] = {}
        self._custom_domains: Dict[str, str] = {}  # domain -> tenant_id
        self._middleware_chain: List[Callable] = []
    
    def register_tenant(self, config: TenantRoutingConfig):
        """Register a tenant subdomain"""
        self._tenant_routes[config.tenant_id] = config
        
        if config.custom_domain:
            self._custom_domains[config.custom_domain] = config.tenant_id
        
        logger.info(f"Registered tenant: {config.tenant_id} -> {config.subdomain}")
    
    def unregister_tenant(self, tenant_id: str):
        """Unregister a tenant"""
        if tenant_id in self._tenant_routes:
            config = self._tenant_routes[tenant_id]
            if config.custom_domain:
                del self._custom_domains[config.custom_domain]
            del self._tenant_routes[tenant_id]
            logger.info(f"Unregistered tenant: {tenant_id}")
    
    def parse_subdomain(self, host: str) -> Dict[str, Optional[str]]:
        """Parse subdomain from host header"""
        # Remove port if present
        host = host.split(':')[0]
        
        # Handle punycode
        try:
            host = idna.decode(host)
        except (idna.core.IDNAError, UnicodeError):
            pass
        
        # Check custom domains first
        if host in self._custom_domains:
            return {
                'tenant_id': self._custom_domains[host],
                'subdomain': None,
                'is_custom_domain': True
            }
        
        # Parse subdomain pattern
        match = self.SUBDOMAIN_PATTERN.match(host)
        if not match:
            return {'tenant_id': None, 'subdomain': None, 'is_custom_domain': False}
        
        tenant = match.group('tenant')
        domain = match.group('domain')
        
        # Check if it's our base domain
        if domain != self.base_domain:
            return {'tenant_id': None, 'subdomain': None, 'is_custom_domain': False}
        
        # Find tenant by subdomain
        for tenant_id, config in self._tenant_routes.items():
            if config.subdomain == tenant:
                return {
                    'tenant_id': tenant_id,
                    'subdomain': tenant,
                    'is_custom_domain': False
                }
        
        return {'tenant_id': None, 'subdomain': tenant, 'is_custom_domain': False}
    
    def get_tenant_config(self, tenant_id: str) -> Optional[TenantRoutingConfig]:
        """Get tenant routing configuration"""
        return self._tenant_routes.get(tenant_id)
    
    def is_valid_subdomain(self, subdomain: str) -> bool:
        """Check if subdomain is valid"""
        # Valid subdomain: lowercase letters, numbers, hyphens
        # Cannot start or end with hyphen
        if not subdomain:
            return False
        
        if len(subdomain) < 3 or len(subdomain) > 63:
            return False
        
        if subdomain.startswith('-') or subdomain.endswith('-'):
            return False
        
        return bool(re.match(r'^[a-z0-9-]+$', subdomain))
    
    def generate_subdomain(self, tenant_name: str) -> str:
        """Generate valid subdomain from tenant name"""
        # Convert to lowercase, replace spaces with hyphens
        subdomain = tenant_name.lower().replace(' ', '-')
        
        # Remove invalid characters
        subdomain = re.sub(r'[^a-z0-9-]', '', subdomain)
        
        # Ensure valid length
        subdomain = subdomain[:63]
        
        # Remove leading/trailing hyphens
        subdomain = subdomain.strip('-')
        
        return subdomain
    
    def add_middleware(self, middleware: Callable):
        """Add middleware to request processing chain"""
        self._middleware_chain.append(middleware)
    
    async def process_request(self, request) -> Dict[str, Any]:
        """Process incoming request with middleware chain"""
        host = request.headers.get('host', '')
        routing_info = self.parse_subdomain(host)
        
        context = {
            'request': request,
            'routing_info': routing_info,
            'tenant_config': None
        }
        
        if routing_info['tenant_id']:
            context['tenant_config'] = self.get_tenant_config(
                routing_info['tenant_id'])
        
        # Run middleware chain
        for middleware in self._middleware_chain:
            context = await middleware(context)
        
        return context


class TenantIsolationMiddleware:
    """Middleware for tenant isolation"""
    
    def __init__(self, router: SubdomainRouter):
        self.router = router
    
    async def __call__(self, request, call_next):
        """Process request with tenant context"""
        host = request.headers.get('host', '')
        routing_info = self.router.parse_subdomain(host)
        
        # Set tenant context
        request.state.tenant_id = routing_info.get('tenant_id')
        request.state.subdomain = routing_info.get('subdomain')
        request.state.is_custom_domain = routing_info.get('is_custom_domain', False)
        
        # Add security headers for tenant isolation
        response = await call_next(request)
        
        response.headers['X-Tenant-ID'] = str(request.state.tenant_id or 'none')
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Content-Security-Policy'] = self._build_csp(
            request.state.tenant_id)
        
        return response
    
    def _build_csp(self, tenant_id: Optional[str]) -> str:
        """Build Content Security Policy for tenant"""
        base_csp = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline'",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: https:",
            "font-src 'self'",
            "connect-src 'self'",
            "frame-ancestors 'none'",
        ]
        
        if tenant_id:
            # Add tenant-specific sources
            base_csp.append(f"connect-src 'self' https://{tenant_id}.cerebrum.ai")
        
        return '; '.join(base_csp)


class SSLContextManager:
    """Manages SSL contexts for different tenants"""
    
    def __init__(self, ssl_dir: str = "/etc/ssl/cerebrum"):
        self.ssl_dir = ssl_dir
        self._contexts: Dict[str, ssl.SSLContext] = {}
    
    def get_context(self, domain: str, 
                    cert_path: str = None,
                    key_path: str = None) -> ssl.SSLContext:
        """Get or create SSL context for domain"""
        if domain in self._contexts:
            return self._contexts[domain]
        
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        
        if cert_path and key_path:
            context.load_cert_chain(cert_path, key_path)
        
        # Configure secure defaults
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS')
        
        self._contexts[domain] = context
        return context
    
    def get_sni_callback(self) -> Callable:
        """Get SNI callback for dynamic certificate selection"""
        def sni_callback(ssl_socket, server_name, ssl_context):
            """Handle SNI callback for certificate selection"""
            logger.debug(f"SNI callback for: {server_name}")
            
            # Find matching certificate
            for domain, context in self._contexts.items():
                if server_name.endswith(domain):
                    ssl_socket.context = context
                    return None
            
            # Use wildcard fallback
            wildcard_context = self._contexts.get('*.cerebrum.ai')
            if wildcard_context:
                ssl_socket.context = wildcard_context
            
            return None
        
        return sni_callback


class SubdomainSecurityPolicy:
    """Security policies for subdomain routing"""
    
    RESERVED_SUBDOMAINS = {
        'www', 'api', 'app', 'admin', 'mail', 'ftp', 'smtp', 'pop', 'imap',
        'blog', 'shop', 'store', 'support', 'help', 'docs', 'status',
        'cdn', 'static', 'assets', 'media', 'files', 'download',
        'dev', 'staging', 'test', 'demo', 'sandbox', 'beta',
        'auth', 'login', 'signup', 'register', 'account', 'user',
        'security', 'ssl', 'cert', 'verify', 'validate',
        'localhost', '127', '0', '255',
    }
    
    @staticmethod
    def is_reserved(subdomain: str) -> bool:
        """Check if subdomain is reserved"""
        return subdomain.lower() in SubdomainSecurityPolicy.RESERVED_SUBDOMAINS
    
    @staticmethod
    def validate_custom_domain(domain: str) -> tuple:
        """Validate custom domain configuration"""
        errors = []
        
        # Check domain format
        if not re.match(r'^[a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z0-9][-a-zA-Z0-9.]*$', domain):
            errors.append("Invalid domain format")
        
        # Check for reserved domains
        parts = domain.lower().split('.')
        if parts[0] in SubdomainSecurityPolicy.RESERVED_SUBDOMAINS:
            errors.append(f"Reserved subdomain: {parts[0]}")
        
        return len(errors) == 0, errors


# Rate limiting per subdomain
class SubdomainRateLimiter:
    """Rate limiting for tenant subdomains"""
    
    def __init__(self):
        self._requests: Dict[str, List[datetime]] = {}
    
    def is_allowed(self, subdomain: str, limit: int = 1000, 
                   window_seconds: int = 3600) -> bool:
        """Check if subdomain is within rate limit"""
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=window_seconds)
        
        requests = self._requests.get(subdomain, [])
        requests = [r for r in requests if r > window_start]
        
        if len(requests) >= limit:
            return False
        
        requests.append(now)
        self._requests[subdomain] = requests
        
        return True


# Global instances
ssl_manager = WildcardSSLManager()
subdomain_router = SubdomainRouter()
ssl_context_manager = SSLContextManager()