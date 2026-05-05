"""
Transparent Fernet encryption for SQLAlchemy Text columns (H-1 fix).

Usage in a model:
    from app.core.security.encrypted_field import EncryptedText

    access_token: Mapped[str] = mapped_column(EncryptedText, nullable=False)

The column type stays Text in the database; values are encrypted at rest
using a key derived from settings.SECRET_KEY via PBKDF2-HMAC-SHA256.

MIGRATION NOTE: existing plaintext rows must be re-encrypted via a one-off
script before the model change is deployed. See docs/MIGRATION_ENCRYPT_TOKENS.md.
"""
import base64
import hashlib
import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import Text, types


def _derive_key(secret: str) -> bytes:
    """Derive a 32-byte Fernet key from the application secret key."""
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        secret.encode(),
        b"cerebrum-token-encryption-salt-v1",
        iterations=100_000,
    )
    return base64.urlsafe_b64encode(dk)


def _get_fernet() -> Fernet:
    secret = os.environ.get("SECRET_KEY", "")
    if not secret or len(secret) < 32:
        raise RuntimeError(
            "SECRET_KEY must be at least 32 chars for field-level encryption."
        )
    return Fernet(_derive_key(secret))


class EncryptedText(types.TypeDecorator):
    """SQLAlchemy TypeDecorator that stores text encrypted with Fernet."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Optional[str], dialect) -> Optional[str]:
        """Encrypt before writing to DB."""
        if value is None:
            return None
        fernet = _get_fernet()
        return fernet.encrypt(value.encode()).decode()

    def process_result_value(self, value: Optional[str], dialect) -> Optional[str]:
        """Decrypt after reading from DB."""
        if value is None:
            return None
        fernet = _get_fernet()
        try:
            return fernet.decrypt(value.encode()).decode()
        except InvalidToken:
            # Return raw value if decryption fails (e.g., pre-migration plaintext row)
            # Log a warning in production so you know a migration is needed.
            import warnings
            warnings.warn(
                "EncryptedText: decryption failed — value may be plaintext (pre-migration). "
                "Run the token re-encryption migration script.",
                RuntimeWarning,
                stacklevel=2,
            )
            return value
