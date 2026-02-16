"""
AES-256 Column Encryption for PII (Personally Identifiable Information)
Implements transparent column-level encryption for sensitive data.
"""
import os
import base64
import hashlib
import secrets
from typing import Optional, Union, Any, Dict
from dataclasses import dataclass
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class EncryptionConfig:
    """Configuration for column encryption."""
    algorithm: str = "AES-256-GCM"
    key_rotation_days: int = 90
    salt_length: int = 32
    nonce_length: int = 12
    tag_length: int = 16


class ColumnEncryptionManager:
    """Manages AES-256 encryption for database columns."""
    
    def __init__(self, master_key: Optional[str] = None):
        self.master_key = master_key or os.getenv('ENCRYPTION_MASTER_KEY')
        if not self.master_key:
            raise ValueError("Encryption master key is required")
        
        self.config = EncryptionConfig()
        self._keys: Dict[str, bytes] = {}
        self._init_keys()
    
    def _init_keys(self):
        """Initialize encryption keys from master key."""
        # Derive data encryption key from master key
        master_bytes = self.master_key.encode('utf-8')
        
        # Derive column-specific keys
        for column in ['ssn', 'email', 'phone', 'address', 'dob', 'financial']:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=f"cerebrum_{column}".encode(),
                iterations=100000,
                backend=default_backend()
            )
            self._keys[column] = kdf.derive(master_bytes)
    
    def _get_key(self, key_type: str) -> bytes:
        """Get encryption key for specific data type."""
        return self._keys.get(key_type, self._keys.get('ssn'))
    
    def encrypt(self, plaintext: Union[str, bytes], 
                key_type: str = 'ssn') -> str:
        """Encrypt plaintext using AES-256-GCM."""
        if plaintext is None:
            return None
        
        if isinstance(plaintext, str):
            plaintext = plaintext.encode('utf-8')
        
        key = self._get_key(key_type)
        nonce = secrets.token_bytes(self.config.nonce_length)
        aesgcm = AESGCM(key)
        
        # Encrypt with associated data for integrity
        associated_data = json.dumps({
            'key_type': key_type,
            'alg': self.config.algorithm
        }).encode()
        
        ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data)
        
        # Format: base64(nonce + ciphertext + tag)
        encrypted = base64.urlsafe_b64encode(nonce + ciphertext).decode('utf-8')
        
        return f"enc:{self.config.algorithm}:{key_type}:{encrypted}"
    
    def decrypt(self, ciphertext: str) -> Optional[str]:
        """Decrypt ciphertext using AES-256-GCM."""
        if ciphertext is None:
            return None
        
        if not ciphertext.startswith('enc:'):
            # Not encrypted, return as-is
            return ciphertext
        
        try:
            parts = ciphertext.split(':', 3)
            if len(parts) != 4:
                raise ValueError("Invalid encrypted format")
            
            _, algorithm, key_type, encrypted_data = parts
            
            if algorithm != self.config.algorithm:
                raise ValueError(f"Unsupported algorithm: {algorithm}")
            
            key = self._get_key(key_type)
            data = base64.urlsafe_b64decode(encrypted_data.encode())
            
            nonce = data[:self.config.nonce_length]
            ciphertext_bytes = data[self.config.nonce_length:]
            
            associated_data = json.dumps({
                'key_type': key_type,
                'alg': algorithm
            }).encode()
            
            aesgcm = AESGCM(key)
            plaintext = aesgcm.decrypt(nonce, ciphertext_bytes, associated_data)
            
            return plaintext.decode('utf-8')
        
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError("Failed to decrypt data") from e
    
    def encrypt_deterministic(self, plaintext: str, key_type: str = 'ssn') -> str:
        """Deterministic encryption for searchable encrypted fields."""
        if plaintext is None:
            return None
        
        key = self._get_key(key_type)
        # Use fixed nonce for deterministic encryption
        nonce = hashlib.sha256(plaintext.encode()).digest()[:self.config.nonce_length]
        
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
        
        encrypted = base64.urlsafe_b64encode(nonce + ciphertext).decode('utf-8')
        return f"encd:{self.config.algorithm}:{key_type}:{encrypted}"
    
    def hash_for_search(self, plaintext: str, key_type: str = 'ssn') -> str:
        """Create searchable hash (blind index) for encrypted fields."""
        if plaintext is None:
            return None
        
        key = self._get_key(key_type)
        data = f"{plaintext}:{key_type}".encode()
        
        # HMAC-SHA256 for blind index
        import hmac
        hash_value = hmac.new(key, data, hashlib.sha256).hexdigest()[:32]
        return f"idx:{hash_value}"
    
    def rotate_key(self, old_ciphertext: str, old_key: bytes, 
                   new_key: bytes) -> str:
        """Re-encrypt data with new key (key rotation)."""
        plaintext = self._decrypt_with_key(old_ciphertext, old_key)
        return self._encrypt_with_key(plaintext, new_key)
    
    def _decrypt_with_key(self, ciphertext: str, key: bytes) -> str:
        """Decrypt with specific key."""
        parts = ciphertext.split(':', 3)
        encrypted_data = parts[-1]
        data = base64.urlsafe_b64decode(encrypted_data.encode())
        
        nonce = data[:self.config.nonce_length]
        ciphertext_bytes = data[self.config.nonce_length:]
        
        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext_bytes, None)
        return plaintext.decode('utf-8')
    
    def _encrypt_with_key(self, plaintext: str, key: bytes) -> str:
        """Encrypt with specific key."""
        nonce = secrets.token_bytes(self.config.nonce_length)
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
        encrypted = base64.urlsafe_b64encode(nonce + ciphertext).decode('utf-8')
        return f"enc:{self.config.algorithm}:rotated:{encrypted}"


class EncryptedColumn:
    """Descriptor for encrypted model columns."""
    
    def __init__(self, key_type: str = 'ssn', searchable: bool = False,
                 deterministic: bool = False):
        self.key_type = key_type
        self.searchable = searchable
        self.deterministic = deterministic
        self.name = None
        self._encryption_manager = None
    
    def __set_name__(self, owner, name):
        self.name = name
    
    @property
    def encryption_manager(self) -> ColumnEncryptionManager:
        if self._encryption_manager is None:
            self._encryption_manager = ColumnEncryptionManager()
        return self._encryption_manager
    
    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        
        encrypted_value = obj.__dict__.get(f"_{self.name}_encrypted")
        if encrypted_value is None:
            return None
        
        return self.encryption_manager.decrypt(encrypted_value)
    
    def __set__(self, obj, value):
        if value is None:
            obj.__dict__[f"_{self.name}_encrypted"] = None
            if self.searchable:
                obj.__dict__[f"_{self.name}_index"] = None
            return
        
        if self.deterministic:
            encrypted = self.encryption_manager.encrypt_deterministic(value, self.key_type)
        else:
            encrypted = self.encryption_manager.encrypt(value, self.key_type)
        
        obj.__dict__[f"_{self.name}_encrypted"] = encrypted
        
        if self.searchable:
            obj.__dict__[f"_{self.name}_index"] = self.encryption_manager.hash_for_search(
                value, self.key_type
            )


# Convenience functions for direct encryption/decryption
_encryption_manager: Optional[ColumnEncryptionManager] = None


def get_encryption_manager() -> ColumnEncryptionManager:
    """Get singleton encryption manager instance."""
    global _encryption_manager
    if _encryption_manager is None:
        _encryption_manager = ColumnEncryptionManager()
    return _encryption_manager


def encrypt_pii(plaintext: str, key_type: str = 'ssn') -> str:
    """Encrypt PII data."""
    return get_encryption_manager().encrypt(plaintext, key_type)


def decrypt_pii(ciphertext: str) -> Optional[str]:
    """Decrypt PII data."""
    return get_encryption_manager().decrypt(ciphertext)


def create_search_index(plaintext: str, key_type: str = 'ssn') -> str:
    """Create searchable index for encrypted field."""
    return get_encryption_manager().hash_for_search(plaintext, key_type)
