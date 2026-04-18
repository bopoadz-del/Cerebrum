"""
Multi-Factor Authentication (MFA) System

Provides TOTP-based and SMS-based MFA for enhanced security.
Supports authenticator apps (Google Authenticator, Authy, etc.)
and backup codes for account recovery.
"""

import uuid
import secrets
import base64
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

import pyotp
import qrcode
import qrcode.image.svg
from io import BytesIO
import bcrypt

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.config import settings
from app.models.user import User

logger = get_logger(__name__)


class MFAType(str, Enum):
    """MFA method types."""
    TOTP = "totp"  # Time-based One-Time Password
    SMS = "sms"    # SMS-based OTP
    BACKUP = "backup"  # Backup codes


class MFAStatus(str, Enum):
    """MFA enrollment status."""
    DISABLED = "disabled"
    PENDING = "pending"  # Enrollment in progress
    ENABLED = "enabled"
    REQUIRED = "required"  # MFA is mandatory


@dataclass
class MFAEnrollment:
    """MFA enrollment data."""
    user_id: uuid.UUID
    mfa_type: MFAType
    secret: str
    status: MFAStatus
    verified_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    backup_codes: List[str] = field(default_factory=list)


@dataclass
class MFAVerificationResult:
    """MFA verification result."""
    success: bool
    mfa_type: Optional[MFAType] = None
    message: str = ""
    remaining_attempts: int = 0
    locked_until: Optional[datetime] = None


class MFAManager:
    """
    Multi-Factor Authentication Manager.
    
    Handles TOTP setup, verification, backup codes, and SMS MFA.
    """
    
    # Configuration
    TOTP_ISSUER = settings.MFA_ISSUER_NAME
    TOTP_DIGITS = 6
    TOTP_INTERVAL = 30  # 30-second TOTP window
    BACKUP_CODE_COUNT = 10
    BACKUP_CODE_LENGTH = 10
    MAX_VERIFY_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 30
    VERIFY_WINDOW_PAST = 1  # Allow 1 interval in the past
    VERIFY_WINDOW_FUTURE = 1  # Allow 1 interval in the future
    
    def __init__(self):
        self._enrollment_cache: Dict[uuid.UUID, MFAEnrollment] = {}
    
    def generate_totp_secret(self) -> str:
        """
        Generate a new TOTP secret.
        
        Returns:
            Base32-encoded secret string
        """
        return pyotp.random_base32()
    
    def create_totp(self, secret: str) -> pyotp.TOTP:
        """
        Create TOTP instance from secret.
        
        Args:
            secret: Base32-encoded secret
            
        Returns:
            pyotp.TOTP instance
        """
        return pyotp.TOTP(
            secret,
            digits=self.TOTP_DIGITS,
            interval=self.TOTP_INTERVAL,
            issuer=self.TOTP_ISSUER,
        )
    
    def generate_provisioning_uri(
        self,
        secret: str,
        user_email: str,
        user_id: uuid.UUID,
    ) -> str:
        """
        Generate provisioning URI for authenticator apps.
        
        Args:
            secret: TOTP secret
            user_email: User's email
            user_id: User's UUID
            
        Returns:
            otpauth:// URI for QR code
        """
        totp = self.create_totp(secret)
        return totp.provisioning_uri(
            name=user_email,
            issuer_name=self.TOTP_ISSUER,
        )
    
    def generate_qr_code(self, provisioning_uri: str) -> str:
        """
        Generate QR code as base64-encoded SVG.
        
        Args:
            provisioning_uri: otpauth:// URI
            
        Returns:
            Base64-encoded SVG string
        """
        factory = qrcode.image.svg.SvgImage
        qr = qrcode.make(provisioning_uri, image_factory=factory)
        
        buffer = BytesIO()
        qr.save(buffer)
        svg_data = buffer.getvalue().decode()
        
        return base64.b64encode(svg_data.encode()).decode()
    
    def generate_backup_codes(self, count: int = BACKUP_CODE_COUNT) -> List[str]:
        """
        Generate backup codes for account recovery.
        
        Args:
            count: Number of codes to generate
            
        Returns:
            List of backup codes (plain text)
        """
        codes = []
        for _ in range(count):
            # Generate random code
            code = secrets.token_urlsafe(self.BACKUP_CODE_LENGTH)[:self.BACKUP_CODE_LENGTH]
            codes.append(code.upper())
        return codes
    
    def hash_backup_code(self, code: str) -> str:
        """
        Hash a backup code for secure storage.
        
        Args:
            code: Plain text backup code
            
        Returns:
            Hashed code string
        """
        return bcrypt.hashpw(code.encode(), bcrypt.gensalt(rounds=12)).decode()
    
    def verify_backup_code(self, code: str, hashed_code: str) -> bool:
        """
        Verify a backup code against its hash.
        
        Args:
            code: Plain text code
            hashed_code: Stored hash
            
        Returns:
            True if code matches
        """
        try:
            return bcrypt.checkpw(code.encode(), hashed_code.encode())
        except Exception:
            return False
    
    async def initiate_totp_setup(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Initiate TOTP MFA setup for a user.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Dictionary with secret, QR code, and recovery codes
        """
        # Get user
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise ValueError(f"User not found: {user_id}")
        
        # Generate TOTP secret
        secret = self.generate_totp_secret()
        
        # Generate provisioning URI
        provisioning_uri = self.generate_provisioning_uri(
            secret=secret,
            user_email=user.email,
            user_id=user.id,
        )
        
        # Generate QR code
        qr_code_b64 = self.generate_qr_code(provisioning_uri)
        
        # Generate backup codes
        backup_codes = self.generate_backup_codes()
        hashed_backup_codes = [self.hash_backup_code(code) for code in backup_codes]
        
        # Store pending enrollment
        enrollment = MFAEnrollment(
            user_id=user_id,
            mfa_type=MFAType.TOTP,
            secret=secret,
            status=MFAStatus.PENDING,
            backup_codes=hashed_backup_codes,
        )
        self._enrollment_cache[user_id] = enrollment
        
        # Update user
        user.mfa_secret = secret
        user.mfa_enabled = False  # Not enabled until verified
        user.mfa_backup_codes = hashed_backup_codes
        user.mfa_verified_at = None
        
        logger.info(
            f"Initiated TOTP MFA setup",
            user_id=str(user_id),
        )
        
        return {
            "secret": secret,  # Show once for manual entry
            "qr_code_svg_base64": qr_code_b64,
            "backup_codes": backup_codes,  # Show once
            "provisioning_uri": provisioning_uri,
        }
    
    async def verify_totp_setup(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        code: str,
    ) -> bool:
        """
        Verify TOTP setup by validating initial code.
        
        Args:
            db: Database session
            user_id: User ID
            code: TOTP code to verify
            
        Returns:
            True if verification successful
        """
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user or not user.mfa_secret:
            raise ValueError("MFA setup not initiated")
        
        # Verify code
        totp = self.create_totp(user.mfa_secret)
        
        if totp.verify(code, valid_window=self.VERIFY_WINDOW_PAST):
            # Enable MFA
            user.mfa_enabled = True
            user.mfa_verified_at = datetime.utcnow()
            
            # Update enrollment cache
            if user_id in self._enrollment_cache:
                self._enrollment_cache[user_id].status = MFAStatus.ENABLED
                self._enrollment_cache[user_id].verified_at = datetime.utcnow()
            
            logger.info(
                f"TOTP MFA enabled",
                user_id=str(user_id),
            )
            return True
        
        return False
    
    async def verify_totp(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        code: str,
    ) -> MFAVerificationResult:
        """
        Verify a TOTP code during login.
        
        Args:
            db: Database session
            user_id: User ID
            code: TOTP code
            
        Returns:
            MFAVerificationResult
        """
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            return MFAVerificationResult(
                success=False,
                message="User not found",
            )
        
        if not user.mfa_enabled or not user.mfa_secret:
            return MFAVerificationResult(
                success=False,
                message="MFA not enabled",
            )
        
        # Check account lock
        if user.locked_until and user.locked_until > datetime.utcnow():
            return MFAVerificationResult(
                success=False,
                message="Account temporarily locked",
                locked_until=user.locked_until,
            )
        
        # Verify TOTP
        totp = self.create_totp(user.mfa_secret)
        
        if totp.verify(
            code,
            valid_window=self.VERIFY_WINDOW_PAST + self.VERIFY_WINDOW_FUTURE,
        ):
            # Reset failed attempts
            user.failed_login_attempts = 0
            
            logger.info(
                f"TOTP verified successfully",
                user_id=str(user_id),
            )
            
            return MFAVerificationResult(
                success=True,
                mfa_type=MFAType.TOTP,
                message="Verification successful",
            )
        
        # Increment failed attempts
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        remaining = max(0, self.MAX_VERIFY_ATTEMPTS - user.failed_login_attempts)
        
        # Lock account if too many failures
        if user.failed_login_attempts >= self.MAX_VERIFY_ATTEMPTS:
            user.locked_until = datetime.utcnow() + timedelta(
                minutes=self.LOCKOUT_DURATION_MINUTES
            )
            logger.warning(
                f"Account locked due to MFA failures",
                user_id=str(user_id),
                locked_until=user.locked_until.isoformat(),
            )
        
        return MFAVerificationResult(
            success=False,
            message="Invalid verification code",
            remaining_attempts=remaining,
            locked_until=user.locked_until if user.failed_login_attempts >= self.MAX_VERIFY_ATTEMPTS else None,
        )
    
    async def verify_backup_code(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        code: str,
    ) -> MFAVerificationResult:
        """
        Verify a backup code.
        
        Args:
            db: Database session
            user_id: User ID
            code: Backup code
            
        Returns:
            MFAVerificationResult
        """
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user or not user.mfa_backup_codes:
            return MFAVerificationResult(
                success=False,
                message="No backup codes available",
            )
        
        # Check each backup code
        remaining_codes = []
        for hashed_code in user.mfa_backup_codes:
            if self.verify_backup_code(code.upper(), hashed_code):
                # Code matched - remove it (one-time use)
                logger.info(
                    f"Backup code used successfully",
                    user_id=str(user_id),
                )
                continue
            remaining_codes.append(hashed_code)
        
        # Check if any code was used
        if len(remaining_codes) < len(user.mfa_backup_codes):
            # Update backup codes
            user.mfa_backup_codes = remaining_codes
            
            # Reset failed attempts
            user.failed_login_attempts = 0
            
            return MFAVerificationResult(
                success=True,
                mfa_type=MFAType.BACKUP,
                message="Backup code accepted",
            )
        
        # Code didn't match
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        remaining = max(0, self.MAX_VERIFY_ATTEMPTS - user.failed_login_attempts)
        
        return MFAVerificationResult(
            success=False,
            message="Invalid backup code",
            remaining_attempts=remaining,
        )
    
    async def disable_mfa(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        verification_code: str,
    ) -> bool:
        """
        Disable MFA for a user.
        
        Args:
            db: Database session
            user_id: User ID
            verification_code: Current TOTP code or backup code for verification
            
        Returns:
            True if MFA disabled successfully
        """
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user or not user.mfa_enabled:
            return False
        
        # Verify with TOTP first
        totp_result = await self.verify_totp(db, user_id, verification_code)
        if totp_result.success:
            # Disable MFA
            user.mfa_enabled = False
            user.mfa_secret = None
            user.mfa_backup_codes = None
            user.mfa_verified_at = None
            
            # Clear cache
            self._enrollment_cache.pop(user_id, None)
            
            logger.info(
                f"MFA disabled",
                user_id=str(user_id),
            )
            return True
        
        # Try backup code
        backup_result = await self.verify_backup_code(db, user_id, verification_code)
        if backup_result.success:
            # Disable MFA
            user.mfa_enabled = False
            user.mfa_secret = None
            user.mfa_backup_codes = None
            user.mfa_verified_at = None
            
            # Clear cache
            self._enrollment_cache.pop(user_id, None)
            
            logger.info(
                f"MFA disabled using backup code",
                user_id=str(user_id),
            )
            return True
        
        return False
    
    async def regenerate_backup_codes(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        verification_code: str,
    ) -> Optional[List[str]]:
        """
        Generate new backup codes.
        
        Args:
            db: Database session
            user_id: User ID
            verification_code: TOTP code for verification
            
        Returns:
            List of new backup codes or None if verification failed
        """
        # First verify TOTP
        totp_result = await self.verify_totp(db, user_id, verification_code)
        if not totp_result.success:
            return None
        
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        # Generate new codes
        new_codes = self.generate_backup_codes()
        hashed_codes = [self.hash_backup_code(code) for code in new_codes]
        
        user.mfa_backup_codes = hashed_codes
        
        logger.info(
            f"Backup codes regenerated",
            user_id=str(user_id),
        )
        
        return new_codes
    
    async def get_mfa_status(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Get MFA status for a user.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            MFA status dictionary
        """
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            return {"status": MFAStatus.DISABLED}
        
        status = MFAStatus.DISABLED
        if user.mfa_enabled:
            status = MFAStatus.ENABLED
        elif user.mfa_secret:
            status = MFAStatus.PENDING
        
        return {
            "status": status,
            "enabled": user.mfa_enabled,
            "type": MFAType.TOTP if user.mfa_secret else None,
            "verified_at": user.mfa_verified_at.isoformat() if user.mfa_verified_at else None,
            "backup_codes_remaining": len(user.mfa_backup_codes) if user.mfa_backup_codes else 0,
        }
    
    def generate_sms_code(self) -> str:
        """
        Generate SMS OTP code.
        
        Returns:
            6-digit SMS code
        """
        return secrets.randbelow(1000000).zfill(6)
    
    async def require_mfa_for_user(self, db: AsyncSession, user_id: uuid.UUID) -> bool:
        """
        Check if MFA is required for a user.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            True if MFA is enabled and required
        """
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            return False
        
        return user.mfa_enabled and user.mfa_secret is not None


# Global MFA manager instance
mfa_manager = MFAManager()

# Alias for E2E compatibility
MFAService = MFAManager


async def verify_mfa(
    db: AsyncSession,
    user_id: uuid.UUID,
    code: str,
    allow_backup: bool = True,
) -> MFAVerificationResult:
    """
    Verify MFA code (TOTP or backup) - convenience function.
    
    Args:
        db: Database session
        user_id: User ID
        code: MFA code to verify
        allow_backup: Whether to allow backup codes
        
    Returns:
        MFAVerificationResult
    """
    # Try TOTP first
    result = await mfa_manager.verify_totp(db, user_id, code)
    if result.success:
        return result
    
    # Try backup code if allowed
    if allow_backup:
        result = await mfa_manager.verify_backup_code(db, user_id, code)
    
    return result
