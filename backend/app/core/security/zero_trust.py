"""
Zero Trust Security - mTLS Between Services
Implements mutual TLS authentication for service-to-service communication.
"""
import ssl
import socket
import hashlib
import tempfile
import os
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class Certificate:
    """Represents an X.509 certificate."""
    cert_pem: str
    key_pem: str
    ca_cert_pem: Optional[str] = None
    subject: str = ""
    issuer: str = ""
    not_before: datetime = None
    not_after: datetime = None
    serial_number: str = ""
    fingerprint: str = ""
    
    def __post_init__(self):
        if self.not_before is None:
            self.not_before = datetime.utcnow()
        if self.not_after is None:
            self.not_after = datetime.utcnow() + timedelta(days=365)
        if not self.fingerprint:
            self.fingerprint = hashlib.sha256(self.cert_pem.encode()).hexdigest()[:32]
    
    def is_valid(self) -> bool:
        """Check if certificate is currently valid."""
        now = datetime.utcnow()
        return self.not_before <= now <= self.not_after
    
    def days_until_expiry(self) -> int:
        """Get days until certificate expires."""
        return (self.not_after - datetime.utcnow()).days
    
    def write_to_files(self, cert_path: str, key_path: str, 
                       ca_path: Optional[str] = None):
        """Write certificate to files."""
        Path(cert_path).write_text(self.cert_pem)
        Path(key_path).write_text(self.key_pem)
        if ca_path and self.ca_cert_pem:
            Path(ca_path).write_text(self.ca_cert_pem)
        
        # Set secure permissions
        os.chmod(key_path, 0o600)


class CertificateManager:
    """Manages mTLS certificates for services."""
    
    def __init__(self, ca_cert: Optional[Certificate] = None):
        self.ca_cert = ca_cert
        self._cert_cache: Dict[str, Certificate] = {}
        self._temp_dir = tempfile.mkdtemp(prefix='cerebrum_certs_')
    
    def generate_ca_certificate(self, 
                                organization: str = "Cerebrum AI",
                                validity_days: int = 3650) -> Certificate:
        """Generate a self-signed CA certificate."""
        # This is a placeholder - in production, use proper PKI
        # or integrate with cert-manager, Vault, etc.
        cert_pem = f"""-----BEGIN CERTIFICATE-----
MIICpDCCAYwCCQDU+pQ4nEHXqzANBgkqhkiG9w0BAQsFADAUMRIwEAYDVQQDDAlD
erZWJydW0gQ0EwHhcNMjQwMTAxMDAwMDAwWhcNMzQwMTAxMDAwMDAwWjAUMRIwEA
YDVQQDDAlDZXJlYnJ1bSBDQTCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCgg
EBALplaceholderCAcertdata
-----END CERTIFICATE-----"""
        
        key_pem = f"""-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCplaceholderCAkey
-----END PRIVATE KEY-----"""
        
        self.ca_cert = Certificate(
            cert_pem=cert_pem,
            key_pem=key_pem,
            subject=f"O={organization},CN=Cerebrum CA",
            issuer=f"O={organization},CN=Cerebrum CA",
            not_after=datetime.utcnow() + timedelta(days=validity_days)
        )
        
        return self.ca_cert
    
    def generate_service_certificate(self, service_name: str,
                                     namespace: str = "default",
                                     validity_days: int = 90,
                                     dns_names: Optional[List[str]] = None,
                                     ip_addresses: Optional[List[str]] = None) -> Certificate:
        """Generate a service certificate signed by the CA."""
        if not self.ca_cert:
            raise ValueError("CA certificate not configured")
        
        # Generate certificate with SANs
        san_list = []
        if dns_names:
            for dns in dns_names:
                san_list.append(f"DNS:{dns}")
        if ip_addresses:
            for ip in ip_addresses:
                san_list.append(f"IP:{ip}")
        
        # Default service DNS names
        service_dns = [
            f"{service_name}",
            f"{service_name}.{namespace}",
            f"{service_name}.{namespace}.svc.cluster.local"
        ]
        for dns in service_dns:
            san_list.append(f"DNS:{dns}")
        
        # Placeholder - in production, use proper certificate generation
        cert_pem = f"""-----BEGIN CERTIFICATE-----
MIICpDCCAYwCCQDU+pQ4nEHXqzANBgkqhkiG9w0BAQsFADAUMRIwEAYDVQQDDAlD
erZWJydW0gQ0EwHhcNMjQwMTAxMDAwMDAwWhcNMjQwNDAxMDAwMDAwWjAeMRwwGg
YDVQQDDBNjZXJlYnJ1bS17c2VydmljZV9uYW1lfTCCASIwDQYJKoZIhvcNAQEBBQ
ADggEPADCCAQoCggEBALplaceholderServiceCert
-----END CERTIFICATE-----"""
        
        key_pem = f"""-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCplaceholderServiceKey
-----END PRIVATE KEY-----"""
        
        cert = Certificate(
            cert_pem=cert_pem,
            key_pem=key_pem,
            ca_cert_pem=self.ca_cert.cert_pem,
            subject=f"CN={service_name}.{namespace}.svc.cluster.local",
            issuer=self.ca_cert.subject,
            not_after=datetime.utcnow() + timedelta(days=validity_days)
        )
        
        self._cert_cache[service_name] = cert
        return cert
    
    def get_certificate(self, service_name: str) -> Optional[Certificate]:
        """Get cached certificate for a service."""
        return self._cert_cache.get(service_name)
    
    def renew_certificate(self, service_name: str) -> Certificate:
        """Renew a service certificate."""
        old_cert = self._cert_cache.get(service_name)
        if old_cert:
            # Extract DNS names from old cert
            return self.generate_service_certificate(
                service_name=service_name,
                validity_days=90
            )
        raise ValueError(f"No certificate found for {service_name}")
    
    def cleanup(self):
        """Clean up temporary certificate files."""
        import shutil
        if os.path.exists(self._temp_dir):
            shutil.rmtree(self._temp_dir)


class MTLSConfig:
    """mTLS configuration for services."""
    
    def __init__(self, 
                 cert_manager: CertificateManager,
                 verify_mode: int = ssl.CERT_REQUIRED,
                 check_hostname: bool = True,
                 minimum_version: int = ssl.TLSVersion.TLSv1_3):
        self.cert_manager = cert_manager
        self.verify_mode = verify_mode
        self.check_hostname = check_hostname
        self.minimum_version = minimum_version
    
    def create_client_ssl_context(self, service_name: str) -> ssl.SSLContext:
        """Create SSL context for client connections."""
        cert = self.cert_manager.get_certificate(service_name)
        if not cert:
            cert = self.cert_manager.generate_service_certificate(service_name)
        
        # Write certs to temp files
        cert_path = os.path.join(self.cert_manager._temp_dir, f"{service_name}.crt")
        key_path = os.path.join(self.cert_manager._temp_dir, f"{service_name}.key")
        ca_path = os.path.join(self.cert_manager._temp_dir, "ca.crt")
        
        cert.write_to_files(cert_path, key_path, ca_path)
        
        # Create SSL context
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=ca_path)
        context.load_cert_chain(cert_path, key_path)
        context.minimum_version = self.minimum_version
        context.verify_mode = self.verify_mode
        context.check_hostname = self.check_hostname
        
        return context
    
    def create_server_ssl_context(self, service_name: str) -> ssl.SSLContext:
        """Create SSL context for server."""
        cert = self.cert_manager.get_certificate(service_name)
        if not cert:
            cert = self.cert_manager.generate_service_certificate(service_name)
        
        # Write certs to temp files
        cert_path = os.path.join(self.cert_manager._temp_dir, f"{service_name}.crt")
        key_path = os.path.join(self.cert_manager._temp_dir, f"{service_name}.key")
        ca_path = os.path.join(self.cert_manager._temp_dir, "ca.crt")
        
        cert.write_to_files(cert_path, key_path, ca_path)
        
        # Create SSL context
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH, cafile=ca_path)
        context.load_cert_chain(cert_path, key_path)
        context.minimum_version = self.minimum_version
        context.verify_mode = self.verify_mode
        
        return context


class ZeroTrustMiddleware:
    """Middleware for zero-trust service authentication."""
    
    def __init__(self, cert_manager: CertificateManager):
        self.cert_manager = cert_manager
        self.allowed_services: Dict[str, List[str]] = {}  # service -> allowed endpoints
    
    def register_service(self, service_name: str, allowed_endpoints: List[str]):
        """Register a service with allowed endpoints."""
        self.allowed_services[service_name] = allowed_endpoints
    
    def verify_client_certificate(self, cert_dict: Dict[str, Any]) -> Optional[str]:
        """Verify client certificate and return service name."""
        subject = cert_dict.get('subject', ())
        for item in subject:
            if item[0][0] == 'commonName':
                cn = item[0][1]
                # Extract service name from CN
                if '.svc.cluster.local' in cn:
                    return cn.split('.')[0]
        return None
    
    def is_endpoint_allowed(self, service_name: str, endpoint: str) -> bool:
        """Check if service is allowed to access endpoint."""
        allowed = self.allowed_services.get(service_name, [])
        
        for pattern in allowed:
            if self._match_pattern(endpoint, pattern):
                return True
        return False
    
    def _match_pattern(self, endpoint: str, pattern: str) -> bool:
        """Match endpoint against pattern (supports wildcards)."""
        import fnmatch
        return fnmatch.fnmatch(endpoint, pattern)


class ServiceMeshConfig:
    """Configuration for service mesh (Istio/Linkerd) integration."""
    
    def __init__(self, mesh_type: str = "istio"):
        self.mesh_type = mesh_type
    
    def generate_destination_rule(self, service_name: str, 
                                   namespace: str = "default") -> Dict[str, Any]:
        """Generate Istio DestinationRule for mTLS."""
        return {
            'apiVersion': 'networking.istio.io/v1beta1',
            'kind': 'DestinationRule',
            'metadata': {
                'name': f'{service_name}-mtls',
                'namespace': namespace
            },
            'spec': {
                'host': f'{service_name}.{namespace}.svc.cluster.local',
                'trafficPolicy': {
                    'tls': {
                        'mode': 'ISTIO_MUTUAL'
                    }
                }
            }
        }
    
    def generate_peer_authentication(self, namespace: str = "default",
                                      mode: str = "STRICT") -> Dict[str, Any]:
        """Generate Istio PeerAuthentication for mTLS enforcement."""
        return {
            'apiVersion': 'security.istio.io/v1beta1',
            'kind': 'PeerAuthentication',
            'metadata': {
                'name': 'default',
                'namespace': namespace
            },
            'spec': {
                'mtls': {
                    'mode': mode  # STRICT, PERMISSIVE, DISABLE
                }
            }
        }
    
    def generate_authorization_policy(self, namespace: str = "default",
                                       rules: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Generate Istio AuthorizationPolicy for access control."""
        return {
            'apiVersion': 'security.istio.io/v1beta1',
            'kind': 'AuthorizationPolicy',
            'metadata': {
                'name': 'default',
                'namespace': namespace
            },
            'spec': {
                'rules': rules or [
                    {
                        'from': [
                            {
                                'source': {
                                    'principals': ['cluster.local/ns/default/sa/cerebrum-api']
                                }
                            }
                        ],
                        'to': [
                            {
                                'operation': {
                                    'methods': ['GET', 'POST', 'PUT', 'DELETE'],
                                    'paths': ['/api/*']
                                }
                            }
                        ]
                    }
                ]
            }
        }


# Convenience functions
def create_mtls_context(service_name: str, 
                        ca_cert_path: Optional[str] = None) -> ssl.SSLContext:
    """Create mTLS SSL context for a service."""
    cert_manager = CertificateManager()
    
    if ca_cert_path:
        ca_cert = Certificate(
            cert_pem=Path(ca_cert_path).read_text(),
            key_pem=""  # CA key not needed for client
        )
        cert_manager.ca_cert = ca_cert
    else:
        cert_manager.generate_ca_certificate()
    
    config = MTLSConfig(cert_manager)
    return config.create_client_ssl_context(service_name)
