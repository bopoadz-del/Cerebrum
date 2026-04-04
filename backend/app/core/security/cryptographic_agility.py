"""
Cryptographic Agility - Multiple JWT Algorithm Support
Implements algorithm negotiation and migration for JWT tokens.
"""
import jwt
import hashlib
import hmac
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class JWTAlgorithm(str, Enum):
    """Supported JWT algorithms."""
    HS256 = "HS256"  # HMAC with SHA-256
    HS384 = "HS384"  # HMAC with SHA-384
    HS512 = "HS512"  # HMAC with SHA-512
    RS256 = "RS256"  # RSA with SHA-256
    RS384 = "RS384"  # RSA with SHA-384
    RS512 = "RS512"  # RSA with SHA-512
    ES256 = "ES256"  # ECDSA with SHA-256
    ES384 = "ES384"  # ECDSA with SHA-384
    ES512 = "ES512"  # ECDSA with SHA-512
    PS256 = "PS256"  # RSA-PSS with SHA-256
    PS384 = "PS384"  # RSA-PSS with SHA-384
    PS512 = "PS512"  # RSA-PSS with SHA-512
    EdDSA = "EdDSA"  # EdDSA (Ed25519)


class AlgorithmPriority(str, Enum):
    """Algorithm priority levels."""
    DEPRECATED = "deprecated"      # Should not be used for new tokens
    LEGACY = "legacy"              # Supported for verification only
    CURRENT = "current"            # Currently recommended
    FUTURE = "future"              # Future default, opt-in


@dataclass
class AlgorithmConfig:
    """Configuration for a JWT algorithm."""
    algorithm: JWTAlgorithm
    priority: AlgorithmPriority
    min_key_size: int
    description: str
    use_for_signing: bool = True
    use_for_verification: bool = True


class AlgorithmRegistry:
    """Registry of supported JWT algorithms with their configurations."""
    
    DEFAULT_CONFIGS = {
        JWTAlgorithm.HS256: AlgorithmConfig(
            algorithm=JWTAlgorithm.HS256,
            priority=AlgorithmPriority.LEGACY,
            min_key_size=256,
            description="HMAC with SHA-256 (legacy, symmetric key)"
        ),
        JWTAlgorithm.HS384: AlgorithmConfig(
            algorithm=JWTAlgorithm.HS384,
            priority=AlgorithmPriority.LEGACY,
            min_key_size=384,
            description="HMAC with SHA-384 (legacy, symmetric key)"
        ),
        JWTAlgorithm.HS512: AlgorithmConfig(
            algorithm=JWTAlgorithm.HS512,
            priority=AlgorithmPriority.CURRENT,
            min_key_size=512,
            description="HMAC with SHA-512 (current, symmetric key)"
        ),
        JWTAlgorithm.RS256: AlgorithmConfig(
            algorithm=JWTAlgorithm.RS256,
            priority=AlgorithmPriority.CURRENT,
            min_key_size=2048,
            description="RSA with SHA-256 (current, asymmetric key)"
        ),
        JWTAlgorithm.RS384: AlgorithmConfig(
            algorithm=JWTAlgorithm.RS384,
            priority=AlgorithmPriority.CURRENT,
            min_key_size=2048,
            description="RSA with SHA-384 (current, asymmetric key)"
        ),
        JWTAlgorithm.RS512: AlgorithmConfig(
            algorithm=JWTAlgorithm.RS512,
            priority=AlgorithmPriority.CURRENT,
            min_key_size=2048,
            description="RSA with SHA-512 (current, asymmetric key)"
        ),
        JWTAlgorithm.ES256: AlgorithmConfig(
            algorithm=JWTAlgorithm.ES256,
            priority=AlgorithmPriority.FUTURE,
            min_key_size=256,
            description="ECDSA with P-256 and SHA-256 (future, asymmetric key)"
        ),
        JWTAlgorithm.ES384: AlgorithmConfig(
            algorithm=JWTAlgorithm.ES384,
            priority=AlgorithmPriority.FUTURE,
            min_key_size=384,
            description="ECDSA with P-384 and SHA-384 (future, asymmetric key)"
        ),
        JWTAlgorithm.EdDSA: AlgorithmConfig(
            algorithm=JWTAlgorithm.EdDSA,
            priority=AlgorithmPriority.FUTURE,
            min_key_size=256,
            description="EdDSA with Ed25519 (future, asymmetric key)"
        ),
    }
    
    def __init__(self):
        self.configs = self.DEFAULT_CONFIGS.copy()
        self._signing_algorithm: Optional[JWTAlgorithm] = None
    
    def register_algorithm(self, config: AlgorithmConfig):
        """Register or update an algorithm configuration."""
        self.configs[config.algorithm] = config
    
    def get_config(self, algorithm: JWTAlgorithm) -> Optional[AlgorithmConfig]:
        """Get configuration for an algorithm."""
        return self.configs.get(algorithm)
    
    def get_signing_algorithm(self) -> JWTAlgorithm:
        """Get the current signing algorithm."""
        if self._signing_algorithm:
            return self._signing_algorithm
        
        # Find highest priority algorithm that supports signing
        for priority in [AlgorithmPriority.CURRENT, AlgorithmPriority.FUTURE]:
            for alg, config in self.configs.items():
                if config.priority == priority and config.use_for_signing:
                    return alg
        
        # Fallback to HS256
        return JWTAlgorithm.HS256
    
    def set_signing_algorithm(self, algorithm: JWTAlgorithm):
        """Set the signing algorithm."""
        config = self.configs.get(algorithm)
        if not config or not config.use_for_signing:
            raise ValueError(f"Algorithm {algorithm.value} not available for signing")
        
        self._signing_algorithm = algorithm
        logger.info(f"Signing algorithm set to: {algorithm.value}")
    
    def get_verification_algorithms(self) -> List[JWTAlgorithm]:
        """Get list of algorithms allowed for verification."""
        return [
            alg for alg, config in self.configs.items()
            if config.use_for_verification
        ]
    
    def deprecate_algorithm(self, algorithm: JWTAlgorithm):
        """Mark an algorithm as deprecated."""
        if algorithm in self.configs:
            self.configs[algorithm].priority = AlgorithmPriority.DEPRECATED
            self.configs[algorithm].use_for_signing = False
            logger.warning(f"Algorithm {algorithm.value} deprecated")


class CryptographicAgilityManager:
    """Manages cryptographic agility for JWT tokens."""
    
    def __init__(self, algorithm_registry: AlgorithmRegistry = None):
        self.registry = algorithm_registry or AlgorithmRegistry()
        self._keys: Dict[JWTAlgorithm, Any] = {}
        self._key_versions: Dict[str, Any] = {}
        self._current_key_version: str = "v1"
    
    def add_key(self, algorithm: JWTAlgorithm, key: Any, version: str = "v1"):
        """Add a signing/verification key."""
        if algorithm not in self._keys:
            self._keys[algorithm] = {}
        
        self._keys[algorithm][version] = key
        self._key_versions[version] = {
            'algorithm': algorithm,
            'added_at': datetime.utcnow(),
            'key': key
        }
    
    def get_key(self, algorithm: JWTAlgorithm, version: str = None) -> Any:
        """Get key for algorithm and version."""
        version = version or self._current_key_version
        
        if algorithm in self._keys and version in self._keys[algorithm]:
            return self._keys[algorithm][version]
        
        raise KeyError(f"No key found for {algorithm.value}:{version}")
    
    def rotate_key(self, algorithm: JWTAlgorithm, new_key: Any):
        """Rotate to a new key version."""
        # Generate new version
        current_version_num = int(self._current_key_version.replace('v', ''))
        new_version = f"v{current_version_num + 1}"
        
        # Add new key
        self.add_key(algorithm, new_key, new_version)
        
        # Update current version
        old_version = self._current_key_version
        self._current_key_version = new_version
        
        logger.info(f"Key rotated: {old_version} -> {new_version}")
        
        return new_version
    
    def encode(self, payload: Dict[str, Any], 
               algorithm: JWTAlgorithm = None,
               headers: Dict[str, Any] = None,
               key_version: str = None) -> str:
        """Encode a JWT with algorithm agility."""
        algorithm = algorithm or self.registry.get_signing_algorithm()
        key_version = key_version or self._current_key_version
        
        key = self.get_key(algorithm, key_version)
        
        # Add algorithm and key version to headers
        jwt_headers = headers or {}
        jwt_headers['alg'] = algorithm.value
        jwt_headers['kid'] = key_version
        
        # Add issued at time
        if 'iat' not in payload:
            payload['iat'] = datetime.utcnow()
        
        # Add algorithm claim for verification
        payload['_alg'] = algorithm.value
        
        return jwt.encode(payload, key, algorithm=algorithm.value, headers=jwt_headers)
    
    def decode(self, token: str, verify: bool = True,
               algorithms: List[JWTAlgorithm] = None,
               options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Decode a JWT with algorithm agility."""
        # First decode without verification to get header
        unverified = jwt.decode(token, options={"verify_signature": False})
        header = jwt.get_unverified_header(token)
        
        token_alg = JWTAlgorithm(header.get('alg', 'HS256'))
        key_version = header.get('kid', 'v1')
        
        # Check if algorithm is allowed
        allowed_algorithms = algorithms or self.registry.get_verification_algorithms()
        if token_alg not in allowed_algorithms:
            raise jwt.InvalidAlgorithmError(
                f"Algorithm {token_alg.value} not allowed for verification"
            )
        
        if verify:
            key = self.get_key(token_alg, key_version)
            
            decode_options = options or {}
            decode_options.setdefault('verify_exp', True)
            decode_options.setdefault('verify_iat', True)
            decode_options.setdefault('verify_nbf', True)
            
            return jwt.decode(
                token,
                key,
                algorithms=[token_alg.value],
                options=decode_options
            )
        
        return unverified
    
    def migrate_token(self, token: str, new_algorithm: JWTAlgorithm = None) -> str:
        """Migrate a token to a new algorithm."""
        # Decode existing token
        payload = self.decode(token, verify=True)
        
        # Remove algorithm claim
        payload.pop('_alg', None)
        
        # Re-encode with new algorithm
        return self.encode(payload, algorithm=new_algorithm)


class TokenMigrationManager:
    """Manages token migration during algorithm transitions."""
    
    def __init__(self, crypto_manager: CryptographicAgilityManager):
        self.crypto = crypto_manager
        self._migration_stats = {
            'tokens_migrated': 0,
            'tokens_failed': 0,
            'start_time': None
        }
    
    def start_migration(self, old_algorithm: JWTAlgorithm, 
                       new_algorithm: JWTAlgorithm):
        """Start a token migration process."""
        logger.info(f"Starting token migration: {old_algorithm.value} -> {new_algorithm.value}")
        self._migration_stats['start_time'] = datetime.utcnow()
        
        # Mark old algorithm as legacy
        config = self.crypto.registry.get_config(old_algorithm)
        if config:
            config.priority = AlgorithmPriority.LEGACY
            config.use_for_signing = False
        
        # Set new algorithm as current
        self.crypto.registry.set_signing_algorithm(new_algorithm)
    
    def migrate_session_token(self, token: str) -> Optional[str]:
        """Migrate a single session token."""
        try:
            new_token = self.crypto.migrate_token(token)
            self._migration_stats['tokens_migrated'] += 1
            return new_token
        except Exception as e:
            logger.error(f"Token migration failed: {e}")
            self._migration_stats['tokens_failed'] += 1
            return None
    
    def get_migration_stats(self) -> Dict[str, Any]:
        """Get token migration statistics."""
        stats = self._migration_stats.copy()
        if stats['start_time']:
            stats['duration_seconds'] = (
                datetime.utcnow() - stats['start_time']
            ).total_seconds()
        return stats


class JWKSManager:
    """Manages JSON Web Key Set for public key distribution."""
    
    def __init__(self, crypto_manager: CryptographicAgilityManager):
        self.crypto = crypto_manager
        self._jwks: Dict[str, Any] = {'keys': []}
    
    def add_key(self, key_id: str, algorithm: JWTAlgorithm, 
                public_key: Any, use: str = "sig"):
        """Add a public key to the JWKS."""
        # Convert key to JWK format (simplified)
        jwk = {
            'kty': self._get_key_type(algorithm),
            'kid': key_id,
            'use': use,
            'alg': algorithm.value,
            'n': self._encode_key_component(public_key),
        }
        
        self._jwks['keys'].append(jwk)
    
    def get_jwks(self) -> Dict[str, Any]:
        """Get the JWKS for public distribution."""
        return self._jwks
    
    def _get_key_type(self, algorithm: JWTAlgorithm) -> str:
        """Get JWK key type for algorithm."""
        if algorithm in [JWTAlgorithm.RS256, JWTAlgorithm.RS384, JWTAlgorithm.RS512,
                        JWTAlgorithm.PS256, JWTAlgorithm.PS384, JWTAlgorithm.PS512]:
            return "RSA"
        elif algorithm in [JWTAlgorithm.ES256, JWTAlgorithm.ES384, JWTAlgorithm.ES512]:
            return "EC"
        elif algorithm == JWTAlgorithm.EdDSA:
            return "OKP"
        else:
            return "oct"  # Octet sequence (symmetric)
    
    def _encode_key_component(self, key: Any) -> str:
        """Encode key component for JWK (placeholder)."""
        import base64
        # This is a simplified implementation
        # Real implementation would properly extract and encode RSA/EC components
        return base64.urlsafe_b64encode(str(key).encode()).decode().rstrip('=')


# Convenience functions
def create_crypto_manager(secret_key: str) -> CryptographicAgilityManager:
    """Create a crypto manager with default configuration."""
    registry = AlgorithmRegistry()
    manager = CryptographicAgilityManager(registry)
    
    # Add default symmetric key for HMAC algorithms
    for alg in [JWTAlgorithm.HS256, JWTAlgorithm.HS384, JWTAlgorithm.HS512]:
        manager.add_key(alg, secret_key)
    
    return manager
