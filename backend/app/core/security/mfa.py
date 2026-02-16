"""
Multi-Factor Authentication (MFA)

Provides TOTP-based MFA using pyotp with QR code generation
and backup codes.
"""

import base64
import secrets
from dataclasses import dataclass
from typing import List, Optional, Tuple

import pyotp
import qrcode
from io import BytesIO

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class MFASecret:
    """MFA secret data."""
    secret: str
    uri: str
    backup_codes: List[str]


@dataclass
class MFAVerificationResult:
    """MFA verification result."""
    valid: bool
    remaining_attempts: Optional[int] = None
    error_message: Optional[str] = None


class MFAError(Exception):
    """MFA-related error."""
    pass


class MFASetupError(MFAError):
    """MFA setup error."""
    pass


class MFAManager:
    """
    Multi-Factor Authentication manager.
    
    Provides TOTP-based MFA with:
    - Secret generation
    - QR code generation for authenticator apps
    - Token verification
    - Backup codes
    """
    
    # Number of backup codes to generate
    BACKUP_CODE_COUNT = 10
    # Backup code length
    BACKUP_CODE_LENGTH = 8
    # TOTP digits
    TOTP_DIGITS = 6
    # TOTP interval (seconds)
    TOTP_INTERVAL = 30
    # Verification window (intervals before/after)
    TOTP_WINDOW = 1
    
    def __init__(self) -> None:
        """Initialize MFA manager."""
        self.issuer_name = settings.MFA_ISSUER_NAME
    
    def generate_secret(self, user_id: str, email: str) -> MFASecret:
        """
        Generate new MFA secret for user.
        
        Args:
            user_id: User ID
            email: User email
            
        Returns:
            MFA secret with backup codes
        """
        try:
            # Generate TOTP secret
            secret = pyotp.random_base32()
            
            # Create provisioning URI for QR code
            totp = pyotp.TOTP(secret)
            uri = totp.provisioning_uri(
                name=email,
                issuer_name=self.issuer_name,
            )
            
            # Generate backup codes
            backup_codes = self._generate_backup_codes()
            
            logger.info(
                f"Generated MFA secret",
                user_id=user_id,
                backup_codes_generated=len(backup_codes),
            )
            
            return MFASecret(
                secret=secret,
                uri=uri,
                backup_codes=backup_codes,
            )
            
        except Exception as e:
            logger.error(f"Failed to generate MFA secret: {e}", user_id=user_id)
            raise MFASetupError(f"Failed to generate MFA secret: {e}") from e
    
    def _generate_backup_codes(self) -> List[str]:
        """
        Generate backup codes for account recovery.
        
        Returns:
            List of backup codes
        """
        codes = []
        for _ in range(self.BACKUP_CODE_COUNT):
            # Generate random code
            code = "".join(
                secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789")
                for _ in range(self.BACKUP_CODE_LENGTH)
            )
            codes.append(code)
        return codes
    
    def generate_qr_code(self, provisioning_uri: str) -> str:
        """
        Generate QR code for authenticator app.
        
        Args:
            provisioning_uri: TOTP provisioning URI
            
        Returns:
            Base64-encoded PNG image
        """
        try:
            # Create QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=4,
            )
            qr.add_data(provisioning_uri)
            qr.make(fit=True)
            
            # Generate image
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to base64
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            img_str = base64.b64encode(buffer.getvalue()).decode()
            
            return f"data:image/png;base64,{img_str}"
            
        except Exception as e:
            logger.error(f"Failed to generate QR code: {e}")
            raise MFASetupError(f"Failed to generate QR code: {e}") from e
    
    def verify_token(
        self,
        secret: str,
        token: str,
        backup_codes: Optional[List[str]] = None,
        used_backup_codes: Optional[List[str]] = None,
    ) -> MFAVerificationResult:
        """
        Verify TOTP token or backup code.
        
        Args:
            secret: TOTP secret
            token: Token to verify
            backup_codes: List of valid backup codes
            used_backup_codes: List of already used backup codes
            
        Returns:
            Verification result
        """
        # Check if token is a backup code
        if backup_codes and len(token) == self.BACKUP_CODE_LENGTH:
            if token in backup_codes:
                if used_backup_codes and token in used_backup_codes:
                    return MFAVerificationResult(
                        valid=False,
                        error_message="Backup code already used",
                    )
                return MFAVerificationResult(valid=True)
        
        # Verify TOTP token
        try:
            totp = pyotp.TOTP(
                secret,
                digits=self.TOTP_DIGITS,
                interval=self.TOTP_INTERVAL,
            )
            
            valid = totp.verify(token, valid_window=self.TOTP_WINDOW)
            
            if valid:
                return MFAVerificationResult(valid=True)
            else:
                return MFAVerificationResult(
                    valid=False,
                    error_message="Invalid verification code",
                )
                
        except Exception as e:
            logger.warning(f"Token verification failed: {e}")
            return MFAVerificationResult(
                valid=False,
                error_message="Invalid verification code format",
            )
    
    def get_current_token(self, secret: str) -> str:
        """
        Get current TOTP token (for testing).
        
        Args:
            secret: TOTP secret
            
        Returns:
            Current TOTP token
        """
        totp = pyotp.TOTP(secret, digits=self.TOTP_DIGITS, interval=self.TOTP_INTERVAL)
        return totp.now()
    
    def validate_secret(self, secret: str) -> bool:
        """
        Validate MFA secret format.
        
        Args:
            secret: Secret to validate
            
        Returns:
            True if valid format
        """
        try:
            # Base32 secrets should be 16+ characters
            if len(secret) < 16:
                return False
            
            # Try to create TOTP instance
            pyotp.TOTP(secret)
            return True
            
        except Exception:
            return False
    
    def hash_backup_code(self, code: str) -> str:
        """
        Hash backup code for storage.
        
        Args:
            code: Backup code
            
        Returns:
            Hashed code
        """
        import hashlib
        return hashlib.sha256(code.encode()).hexdigest()
    
    def verify_backup_code(self, code: str, hashed_codes: List[str]) -> bool:
        """
        Verify backup code against hashed codes.
        
        Args:
            code: Backup code to verify
            hashed_codes: List of hashed backup codes
            
        Returns:
            True if code is valid
        """
        hashed = self.hash_backup_code(code)
        return hashed in hashed_codes


# Global MFA manager instance
mfa_manager = MFAManager()


def generate_mfa_secret(user_id: str, email: str) -> MFASecret:
    """Generate MFA secret convenience function."""
    return mfa_manager.generate_secret(user_id, email)


def verify_mfa_token(
    secret: str,
    token: str,
    backup_codes: Optional[List[str]] = None,
) -> MFAVerificationResult:
    """Verify MFA token convenience function."""
    return mfa_manager.verify_token(secret, token, backup_codes)
