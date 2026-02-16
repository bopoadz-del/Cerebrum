"""
Advanced Security Module - IP Allowlisting, 2FA, Password Policy
Item 297: Advanced security features
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import uuid
from app.db.base_class import Base
import ipaddress
import re

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET, CIDR
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, validator
from fastapi import HTTPException, Request
from enum import Enum
import pyotp
import bcrypt


class TwoFactorMethod(str, Enum):
    """2FA methods"""
    TOTP = "totp"  # Time-based OTP
    SMS = "sms"
    EMAIL = "email"
    HARDWARE = "hardware"  # Security keys
    BACKUP = "backup"  # Backup codes


class SecurityPolicyLevel(str, Enum):
    """Security policy levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CUSTOM = "custom"


# Database Models

class SecurityPolicy(Base):
    """Tenant security policy"""
    __tablename__ = 'security_policies'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, unique=True)
    
    # Policy level
    policy_level = Column(String(50), default=SecurityPolicyLevel.MEDIUM.value)
    
    # Password policy
    password_min_length = Column(Integer, default=8)
    password_require_uppercase = Column(Boolean, default=True)
    password_require_lowercase = Column(Boolean, default=True)
    password_require_numbers = Column(Boolean, default=True)
    password_require_special = Column(Boolean, default=False)
    password_expiry_days = Column(Integer, nullable=True)
    password_history_count = Column(Integer, default=5)
    prevent_common_passwords = Column(Boolean, default=True)
    
    # 2FA settings
    mfa_required = Column(Boolean, default=False)
    mfa_methods_allowed = Column(JSONB, default=lambda: ['totp', 'sms', 'email'])
    mfa_grace_period_days = Column(Integer, default=7)
    
    # Session settings
    session_timeout_minutes = Column(Integer, default=480)  # 8 hours
    idle_timeout_minutes = Column(Integer, default=30)
    max_concurrent_sessions = Column(Integer, default=5)
    
    # IP restrictions
    ip_allowlist_enabled = Column(Boolean, default=False)
    ip_blocklist_enabled = Column(Boolean, default=False)
    
    # Login security
    max_login_attempts = Column(Integer, default=5)
    lockout_duration_minutes = Column(Integer, default=30)
    require_captcha_after_failures = Column(Integer, default=3)
    
    # Device trust
    device_trust_required = Column(Boolean, default=False)
    new_device_verification = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)


class IPAllowlistEntry(Base):
    """IP allowlist entries"""
    __tablename__ = 'ip_allowlist_entries'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    
    # IP range
    ip_address = Column(INET, nullable=True)
    ip_range = Column(CIDR, nullable=True)
    
    # Description
    description = Column(String(500), nullable=True)
    
    # Access control
    allowed_actions = Column(JSONB, default=lambda: ['login', 'api'])
    
    # Status
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=True)
    
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class IPBlocklistEntry(Base):
    """IP blocklist entries"""
    __tablename__ = 'ip_blocklist_entries'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True)
    
    # IP
    ip_address = Column(INET, nullable=False)
    
    # Reason
    reason = Column(String(500), nullable=True)
    source = Column(String(50), default='manual')  # manual, auto, threat_intel
    
    # Status
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class UserTwoFactorAuth(Base):
    """User 2FA configuration"""
    __tablename__ = 'user_two_factor_auth'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    
    # TOTP
    totp_secret = Column(String(255), nullable=True)
    totp_enabled = Column(Boolean, default=False)
    totp_verified_at = Column(DateTime, nullable=True)
    
    # SMS
    sms_phone = Column(String(50), nullable=True)
    sms_enabled = Column(Boolean, default=False)
    sms_verified_at = Column(DateTime, nullable=True)
    
    # Email
    email_enabled = Column(Boolean, default=False)
    
    # Backup codes
    backup_codes = Column(JSONB, nullable=True)  # Hashed codes
    backup_codes_used = Column(JSONB, default=list)
    
    # Preferred method
    preferred_method = Column(String(50), default=TwoFactorMethod.TOTP.value)
    
    # Status
    is_active = Column(Boolean, default=False)
    enabled_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserPasswordHistory(Base):
    """User password history"""
    __tablename__ = 'user_password_history'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class LoginAttempt(Base):
    """Track login attempts"""
    __tablename__ = 'login_attempts'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True)
    
    username = Column(String(255), nullable=False)
    ip_address = Column(INET, nullable=False)
    
    success = Column(Boolean, default=False)
    failure_reason = Column(String(255), nullable=True)
    
    user_agent = Column(String(500), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_login_attempts_ip_time', 'ip_address', 'created_at'),
        Index('ix_login_attempts_user_time', 'username', 'created_at'),
    )


# Pydantic Schemas

class SecurityPolicyConfig(BaseModel):
    """Security policy configuration"""
    policy_level: SecurityPolicyLevel = SecurityPolicyLevel.MEDIUM
    password_min_length: int = 8
    password_require_uppercase: bool = True
    password_require_lowercase: bool = True
    password_require_numbers: bool = True
    password_require_special: bool = False
    password_expiry_days: Optional[int] = None
    mfa_required: bool = False
    session_timeout_minutes: int = 480
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 30


class IPAllowlistEntryRequest(BaseModel):
    """Add IP to allowlist"""
    ip_address: Optional[str] = None
    cidr_range: Optional[str] = None
    description: Optional[str] = None
    allowed_actions: List[str] = Field(default_factory=lambda: ['login', 'api'])
    expires_days: Optional[int] = None
    
    @validator('ip_address', 'cidr_range')
    def validate_ip(cls, v):
        if v:
            try:
                ipaddress.ip_network(v, strict=False)
            except ValueError:
                raise ValueError("Invalid IP address or CIDR range")
        return v


class TwoFactorSetupRequest(BaseModel):
    """Setup 2FA request"""
    method: TwoFactorMethod
    phone_number: Optional[str] = None


class TwoFactorVerifyRequest(BaseModel):
    """Verify 2FA code"""
    code: str
    method: TwoFactorMethod


class PasswordChangeRequest(BaseModel):
    """Change password request"""
    current_password: str
    new_password: str = Field(..., min_length=8)
    
    @validator('new_password')
    def validate_password_strength(cls, v):
        # Check password complexity
        if not re.search(r'[A-Z]', v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r'[a-z]', v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r'\d', v):
            raise ValueError("Password must contain at least one number")
        return v


# Service Classes

class SecurityPolicyService:
    """Service for security policy management"""
    
    POLICY_PRESETS = {
        SecurityPolicyLevel.LOW: {
            'password_min_length': 6,
            'password_require_uppercase': False,
            'password_require_lowercase': True,
            'password_require_numbers': False,
            'password_require_special': False,
            'mfa_required': False,
            'session_timeout_minutes': 1440,
            'max_login_attempts': 10
        },
        SecurityPolicyLevel.MEDIUM: {
            'password_min_length': 8,
            'password_require_uppercase': True,
            'password_require_lowercase': True,
            'password_require_numbers': True,
            'password_require_special': False,
            'mfa_required': False,
            'session_timeout_minutes': 480,
            'max_login_attempts': 5
        },
        SecurityPolicyLevel.HIGH: {
            'password_min_length': 12,
            'password_require_uppercase': True,
            'password_require_lowercase': True,
            'password_require_numbers': True,
            'password_require_special': True,
            'mfa_required': True,
            'session_timeout_minutes': 240,
            'max_login_attempts': 3
        }
    }
    
    COMMON_PASSWORDS = [
        'password', '123456', 'qwerty', 'admin', 'welcome',
        'password123', '12345678', 'abc123', 'letmein', 'monkey'
    ]
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_or_create_policy(self, tenant_id: str) -> SecurityPolicy:
        """Get or create security policy"""
        
        policy = self.db.query(SecurityPolicy).filter(
            SecurityPolicy.tenant_id == tenant_id
        ).first()
        
        if not policy:
            policy = SecurityPolicy(tenant_id=tenant_id)
            self.db.add(policy)
            self.db.commit()
            self.db.refresh(policy)
        
        return policy
    
    def update_policy(
        self,
        tenant_id: str,
        config: SecurityPolicyConfig,
        updated_by: Optional[str] = None
    ) -> SecurityPolicy:
        """Update security policy"""
        
        policy = self.get_or_create_policy(tenant_id)
        
        # Apply preset if specified
        if config.policy_level != SecurityPolicyLevel.CUSTOM:
            preset = self.POLICY_PRESETS.get(config.policy_level, {})
            for key, value in preset.items():
                setattr(policy, key, value)
        
        policy.policy_level = config.policy_level.value
        policy.password_min_length = config.password_min_length
        policy.password_require_uppercase = config.password_require_uppercase
        policy.password_require_lowercase = config.password_require_lowercase
        policy.password_require_numbers = config.password_require_numbers
        policy.password_require_special = config.password_require_special
        policy.password_expiry_days = config.password_expiry_days
        policy.mfa_required = config.mfa_required
        policy.session_timeout_minutes = config.session_timeout_minutes
        policy.max_login_attempts = config.max_login_attempts
        policy.lockout_duration_minutes = config.lockout_duration_minutes
        policy.updated_by = updated_by
        
        self.db.commit()
        self.db.refresh(policy)
        
        return policy
    
    def validate_password(
        self,
        tenant_id: str,
        password: str
    ) -> List[str]:
        """Validate password against policy"""
        
        policy = self.get_or_create_policy(tenant_id)
        errors = []
        
        if len(password) < policy.password_min_length:
            errors.append(f"Password must be at least {policy.password_min_length} characters")
        
        if policy.password_require_uppercase and not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        
        if policy.password_require_lowercase and not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        
        if policy.password_require_numbers and not re.search(r'\d', password):
            errors.append("Password must contain at least one number")
        
        if policy.password_require_special and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character")
        
        if policy.prevent_common_passwords and password.lower() in self.COMMON_PASSWORDS:
            errors.append("Password is too common")
        
        return errors


class IPAllowlistService:
    """Service for IP allowlist management"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def add_entry(
        self,
        tenant_id: str,
        request: IPAllowlistEntryRequest,
        created_by: Optional[str] = None
    ) -> IPAllowlistEntry:
        """Add IP to allowlist"""
        
        expires_at = None
        if request.expires_days:
            expires_at = datetime.utcnow() + timedelta(days=request.expires_days)
        
        entry = IPAllowlistEntry(
            tenant_id=tenant_id,
            ip_address=request.ip_address,
            ip_range=request.cidr_range,
            description=request.description,
            allowed_actions=request.allowed_actions,
            expires_at=expires_at,
            created_by=created_by
        )
        
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        
        return entry
    
    def check_ip_allowed(
        self,
        tenant_id: str,
        ip_address: str,
        action: str = 'login'
    ) -> bool:
        """Check if IP is allowed"""
        
        policy = self.db.query(SecurityPolicy).filter(
            SecurityPolicy.tenant_id == tenant_id
        ).first()
        
        # If allowlist not enabled, allow all
        if not policy or not policy.ip_allowlist_enabled:
            return True
        
        # Check if IP is in allowlist
        entries = self.db.query(IPAllowlistEntry).filter(
            IPAllowlistEntry.tenant_id == tenant_id,
            IPAllowlistEntry.is_active == True,
            (IPAllowlistEntry.expires_at.is_(None) | (IPAllowlistEntry.expires_at > datetime.utcnow()))
        ).all()
        
        client_ip = ipaddress.ip_address(ip_address)
        
        for entry in entries:
            # Check if action is allowed
            if action not in (entry.allowed_actions or []):
                continue
            
            # Check IP match
            if entry.ip_address:
                if client_ip == ipaddress.ip_address(str(entry.ip_address)):
                    return True
            
            if entry.ip_range:
                if client_ip in ipaddress.ip_network(str(entry.ip_range), strict=False):
                    return True
        
        return False
    
    def block_ip(
        self,
        ip_address: str,
        reason: Optional[str] = None,
        tenant_id: Optional[str] = None,
        expires_hours: Optional[int] = None
    ):
        """Block an IP address"""
        
        expires_at = None
        if expires_hours:
            expires_at = datetime.utcnow() + timedelta(hours=expires_hours)
        
        entry = IPBlocklistEntry(
            tenant_id=tenant_id,
            ip_address=ip_address,
            reason=reason,
            expires_at=expires_at
        )
        
        self.db.add(entry)
        self.db.commit()
    
    def is_ip_blocked(self, ip_address: str, tenant_id: Optional[str] = None) -> bool:
        """Check if IP is blocked"""
        
        query = self.db.query(IPBlocklistEntry).filter(
            IPBlocklistEntry.ip_address == ip_address,
            IPBlocklistEntry.is_active == True,
            (IPBlocklistEntry.expires_at.is_(None) | (IPBlocklistEntry.expires_at > datetime.utcnow()))
        )
        
        if tenant_id:
            query = query.filter(
                (IPBlocklistEntry.tenant_id == tenant_id) | (IPBlocklistEntry.tenant_id.is_(None))
            )
        
        return query.first() is not None


class TwoFactorAuthService:
    """Service for 2FA management"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_2fa_config(self, user_id: str) -> Optional[UserTwoFactorAuth]:
        """Get user's 2FA configuration"""
        return self.db.query(UserTwoFactorAuth).filter(
            UserTwoFactorAuth.user_id == user_id
        ).first()
    
    def setup_totp(self, user_id: str) -> Dict[str, str]:
        """Setup TOTP for user"""
        
        config = self.get_2fa_config(user_id)
        
        if not config:
            config = UserTwoFactorAuth(user_id=user_id)
            self.db.add(config)
        
        # Generate TOTP secret
        secret = pyotp.random_base32()
        config.totp_secret = secret
        
        self.db.commit()
        
        # Generate provisioning URI
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=user_id,  # Should be user's email
            issuer_name="Cerebrum AI"
        )
        
        return {
            'secret': secret,
            'provisioning_uri': provisioning_uri
        }
    
    def verify_totp_setup(self, user_id: str, code: str) -> bool:
        """Verify TOTP setup"""
        
        config = self.get_2fa_config(user_id)
        
        if not config or not config.totp_secret:
            return False
        
        totp = pyotp.TOTP(config.totp_secret)
        
        if totp.verify(code):
            config.totp_enabled = True
            config.totp_verified_at = datetime.utcnow()
            config.is_active = True
            config.enabled_at = datetime.utcnow()
            
            # Generate backup codes
            config.backup_codes = self._generate_backup_codes()
            
            self.db.commit()
            return True
        
        return False
    
    def verify_totp(self, user_id: str, code: str) -> bool:
        """Verify TOTP code"""
        
        config = self.get_2fa_config(user_id)
        
        if not config or not config.totp_secret:
            return False
        
        totp = pyotp.TOTP(config.totp_secret)
        return totp.verify(code)
    
    def verify_backup_code(self, user_id: str, code: str) -> bool:
        """Verify backup code"""
        
        config = self.get_2fa_config(user_id)
        
        if not config or not config.backup_codes:
            return False
        
        # Hash the provided code
        code_hash = bcrypt.hashpw(code.encode(), bcrypt.gensalt()).decode()
        
        # Check against stored hashes
        for stored_hash in config.backup_codes:
            if bcrypt.checkpw(code.encode(), stored_hash.encode()):
                # Mark as used
                used_codes = config.backup_codes_used or []
                used_codes.append(code)
                config.backup_codes_used = used_codes
                self.db.commit()
                return True
        
        return False
    
    def _generate_backup_codes(self, count: int = 10) -> List[str]:
        """Generate backup codes"""
        
        import secrets
        codes = []
        
        for _ in range(count):
            code = secrets.token_hex(4).upper()
            # Hash for storage
            hashed = bcrypt.hashpw(code.encode(), bcrypt.gensalt()).decode()
            codes.append(hashed)
        
        return codes
    
    def disable_2fa(self, user_id: str):
        """Disable 2FA for user"""
        
        config = self.get_2fa_config(user_id)
        
        if config:
            config.is_active = False
            config.totp_enabled = False
            config.sms_enabled = False
            config.email_enabled = False
            self.db.commit()


class LoginSecurityService:
    """Service for login security"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def record_login_attempt(
        self,
        username: str,
        ip_address: str,
        success: bool,
        failure_reason: Optional[str] = None,
        tenant_id: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Record login attempt"""
        
        attempt = LoginAttempt(
            tenant_id=tenant_id,
            username=username,
            ip_address=ip_address,
            success=success,
            failure_reason=failure_reason,
            user_agent=user_agent
        )
        
        self.db.add(attempt)
        self.db.commit()
    
    def is_account_locked(
        self,
        username: str,
        tenant_id: str
    ) -> tuple:
        """Check if account is locked due to failed attempts"""
        
        policy = self.db.query(SecurityPolicy).filter(
            SecurityPolicy.tenant_id == tenant_id
        ).first()
        
        if not policy:
            return False, 0
        
        # Count recent failed attempts
        since = datetime.utcnow() - timedelta(minutes=policy.lockout_duration_minutes)
        
        failed_attempts = self.db.query(func.count(LoginAttempt.id)).filter(
            LoginAttempt.username == username,
            LoginAttempt.success == False,
            LoginAttempt.created_at >= since
        ).scalar()
        
        if failed_attempts >= policy.max_login_attempts:
            # Calculate remaining lockout time
            last_attempt = self.db.query(LoginAttempt).filter(
                LoginAttempt.username == username,
                LoginAttempt.success == False
            ).order_by(LoginAttempt.created_at.desc()).first()
            
            if last_attempt:
                remaining = policy.lockout_duration_minutes - (
                    datetime.utcnow() - last_attempt.created_at
                ).total_seconds() / 60
                return True, max(0, int(remaining))
        
        return False, 0
    
    def should_require_captcha(
        self,
        username: str,
        ip_address: str,
        tenant_id: str
    ) -> bool:
        """Check if CAPTCHA should be required"""
        
        policy = self.db.query(SecurityPolicy).filter(
            SecurityPolicy.tenant_id == tenant_id
        ).first()
        
        if not policy:
            return False
        
        since = datetime.utcnow() - timedelta(hours=1)
        
        # Count failures from IP or username
        failures = self.db.query(func.count(LoginAttempt.id)).filter(
            ((LoginAttempt.username == username) | (LoginAttempt.ip_address == ip_address)),
            LoginAttempt.success == False,
            LoginAttempt.created_at >= since
        ).scalar()
        
        return failures >= policy.require_captcha_after_failures


# Export
__all__ = [
    'TwoFactorMethod',
    'SecurityPolicyLevel',
    'SecurityPolicy',
    'IPAllowlistEntry',
    'IPBlocklistEntry',
    'UserTwoFactorAuth',
    'UserPasswordHistory',
    'LoginAttempt',
    'SecurityPolicyConfig',
    'IPAllowlistEntryRequest',
    'TwoFactorSetupRequest',
    'TwoFactorVerifyRequest',
    'PasswordChangeRequest',
    'SecurityPolicyService',
    'IPAllowlistService',
    'TwoFactorAuthService',
    'LoginSecurityService'
]
