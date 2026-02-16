"""
Field-Level Encryption

Provides encryption for sensitive data (PII) at the application level.
Uses AES-256-GCM for authenticated encryption.
"""

import base64
import hashlib
import os
from typing import Optional, Union

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EncryptionError(Exception):
    """Encryption-related error."""
    pass


class EncryptionManager:
    """
    Field-level encryption manager.
    
    Provides encryption and decryption for sensitive fields
    using AES-256-GCM via Fernet.
    
    Note: The encryption key should be stored securely (e.g., in Vault)
    and rotated periodically.
    """
    
    def __init__(self, key: Optional[str] = None) -> None:
        """
        Initialize encryption manager.
        
        Args:
            key: Encryption key (base64-encoded), uses settings if not provided
        """
        key = key or settings.ENCRYPTION_KEY
        
        if not key:
            logger.warning("No encryption key configured - encryption disabled")
            self._fernet = None
            return
        
        try:
            self._fernet = Fernet(key.encode())
            logger.info("Encryption manager initialized")
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            raise EncryptionError(f"Invalid encryption key: {e}") from e
    
    def encrypt(self, plaintext: Union[str, bytes]) -> str:
        """
        Encrypt plaintext data.
        
        Args:
            plaintext: Data to encrypt
            
        Returns:
            Base64-encoded ciphertext
            
        Raises:
            EncryptionError: If encryption fails
        """
        if self._fernet is None:
            raise EncryptionError("Encryption not configured")
        
        try:
            if isinstance(plaintext, str):
                plaintext = plaintext.encode("utf-8")
            
            ciphertext = self._fernet.encrypt(plaintext)
            return base64.urlsafe_b64encode(ciphertext).decode("ascii")
            
        except Exception as e:
            logger.error("Encryption failed", error=str(e))
            raise EncryptionError(f"Encryption failed: {e}") from e
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt ciphertext data.
        
        Args:
            ciphertext: Base64-encoded ciphertext
            
        Returns:
            Decrypted plaintext
            
        Raises:
            EncryptionError: If decryption fails
        """
        if self._fernet is None:
            raise EncryptionError("Encryption not configured")
        
        try:
            # Decode from base64
            encrypted_data = base64.urlsafe_b64decode(ciphertext.encode("ascii"))
            
            # Decrypt
            plaintext = self._fernet.decrypt(encrypted_data)
            
            return plaintext.decode("utf-8")
            
        except Exception as e:
            logger.error("Decryption failed", error=str(e))
            raise EncryptionError(f"Decryption failed: {e}") from e
    
    def encrypt_optional(self, plaintext: Optional[str]) -> Optional[str]:
        """
        Encrypt plaintext if not None.
        
        Args:
            plaintext: Data to encrypt or None
            
        Returns:
            Encrypted data or None
        """
        if plaintext is None:
            return None
        return self.encrypt(plaintext)
    
    def decrypt_optional(self, ciphertext: Optional[str]) -> Optional[str]:
        """
        Decrypt ciphertext if not None.
        
        Args:
            ciphertext: Data to decrypt or None
            
        Returns:
            Decrypted data or None
        """
        if ciphertext is None:
            return None
        return self.decrypt(ciphertext)
    
    @staticmethod
    def generate_key() -> str:
        """
        Generate a new encryption key.
        
        Returns:
            Base64-encoded encryption key
        """
        key = Fernet.generate_key()
        return key.decode("ascii")
    
    @staticmethod
    def derive_key(password: str, salt: Optional[bytes] = None) -> tuple[str, bytes]:
        """
        Derive encryption key from password.
        
        Args:
            password: Password to derive key from
            salt: Optional salt (generated if not provided)
            
        Returns:
            Tuple of (base64-encoded key, salt)
        """
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key.decode("ascii"), salt


# Global encryption manager instance
encryption_manager = EncryptionManager()


def encrypt(plaintext: str) -> str:
    """Encrypt data convenience function."""
    return encryption_manager.encrypt(plaintext)


def decrypt(ciphertext: str) -> str:
    """Decrypt data convenience function."""
    return encryption_manager.decrypt(ciphertext)


class EncryptedField:
    """
    Descriptor for encrypted model fields.
    
    Usage:
        class User(Base):
            _ssn = Column("ssn", String(255))
            ssn = EncryptedField("_ssn")
    """
    
    def __init__(self, column_name: str) -> None:
        """
        Initialize encrypted field.
        
        Args:
            column_name: Name of the database column
        """
        self.column_name = column_name
    
    def __get__(self, instance, owner):
        """Get decrypted value."""
        if instance is None:
            return self
        
        ciphertext = getattr(instance, self.column_name)
        if ciphertext is None:
            return None
        
        try:
            return encryption_manager.decrypt(ciphertext)
        except EncryptionError:
            # Return raw value if decryption fails (might be unencrypted)
            return ciphertext
    
    def __set__(self, instance, value):
        """Set encrypted value."""
        if value is None:
            setattr(instance, self.column_name, None)
            return
        
        try:
            # Try to decrypt to check if already encrypted
            encryption_manager.decrypt(value)
            # If successful, value is already encrypted
            setattr(instance, self.column_name, value)
        except EncryptionError:
            # Encrypt the value
            encrypted = encryption_manager.encrypt(value)
            setattr(instance, self.column_name, encrypted)
