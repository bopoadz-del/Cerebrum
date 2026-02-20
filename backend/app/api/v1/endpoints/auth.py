"""
Authentication Endpoints

Provides login, registration, token refresh, and MFA endpoints.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security.jwt import jwt_manager, TokenPair, TokenPayload
from app.core.security.password import password_manager
from app.core.security.mfa import mfa_manager, MFAVerificationResult
from app.core.security.token_blacklist import token_blacklist
from app.core.security.session import session_manager
from app.core.security.rbac import Role
from app.db.session import get_db_session
from app.models.user import User

logger = get_logger(__name__)
router = APIRouter(prefix="/auth")
security = HTTPBearer()


# =============================================================================
# Schemas
# =============================================================================

class RegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    tenant_id: Optional[str] = None


class LoginRequest(BaseModel):
    """User login request."""
    email: EmailStr
    password: str
    mfa_code: Optional[str] = None


class TokenResponse(BaseModel):
    """Token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    mfa_required: bool = False


class MFASetupRequest(BaseModel):
    """MFA setup request."""
    enable: bool = True


class MFASetupResponse(BaseModel):
    """MFA setup response."""
    secret: str
    qr_code: str
    backup_codes: list[str]


class MFAVerifyRequest(BaseModel):
    """MFA verification request."""
    code: str


class RefreshRequest(BaseModel):
    """Token refresh request."""
    refresh_token: str


class UserResponse(BaseModel):
    """User response."""
    id: str
    email: str
    full_name: Optional[str]
    role: str
    tenant_id: str
    is_active: bool
    mfa_enabled: bool
    
    @field_validator('id', 'tenant_id', mode='before')
    @classmethod
    def uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v


class LogoutRequest(BaseModel):
    """Logout request."""
    all_devices: bool = False


# =============================================================================
# Helper Functions
# =============================================================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """
    Get current authenticated user from token.
    
    Args:
        credentials: HTTP Authorization credentials
        db: Database session
        
    Returns:
        Current user
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials
    
    try:
        # Decode and validate token
        payload = jwt_manager.decode_token(token, token_type="access")
        
        # Check blacklist
        is_blacklisted = await token_blacklist.is_blacklisted(payload.jti)
        if is_blacklisted:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
            )
        
        # Get user
        result = await db.execute(
            select(User).where(User.id == payload.sub)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        
        if not user.can_login:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is disabled or locked",
            )
        
        return user
        
    except Exception as e:
        logger.warning(f"Authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db_session),
) -> Optional[User]:
    """Get optional current user (for endpoints that work with or without auth)."""
    if not credentials:
        return None
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: Request,
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """
    Register a new user.
    
    Args:
        request: HTTP request
        data: Registration data
        db: Database session
        
    Returns:
        Created user
    """
    # Check if email already exists
    result = await db.execute(
        select(User).where(User.email == data.email)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    # Validate password
    is_valid, errors = password_manager.validate(data.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid password: {', '.join(errors)}",
        )
    
    # Create user
    import uuid
    user = User(
        id=uuid.uuid4(),
        email=data.email,
        hashed_password=password_manager.hash(data.password),
        full_name=data.full_name,
        role=Role.USER.value,
        tenant_id=uuid.UUID(data.tenant_id) if data.tenant_id else uuid.uuid4(),
        is_active=True,
        is_verified=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    logger.info(
        f"User registered",
        user_id=str(user.id),
        email=user.email,
        ip=request.client.host if request.client else None,
    )
    
    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    data: LoginRequest,
    db: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """
    Login with email and password.
    
    Args:
        request: HTTP request
        data: Login credentials
        db: Database session
        
    Returns:
        Token pair or MFA challenge
    """
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == data.email)
    )
    user = result.scalar_one_or_none()
    
    # Verify password (always check to prevent timing attacks)
    password_valid = False
    if user:
        password_valid = password_manager.verify(data.password, user.hashed_password)
    
    if not user or not password_valid:
        # Record failed attempt if user exists
        if user:
            user.record_failed_login()
            await db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    # Check if account can login
    if not user.can_login:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is disabled or locked",
        )
    
    # Check MFA if enabled
    if user.mfa_enabled:
        if not data.mfa_code:
            # Return MFA required response
            return TokenResponse(
                access_token="",
                refresh_token="",
                expires_in=0,
                mfa_required=True,
            )
        
        # Verify MFA code
        mfa_result = mfa_manager.verify_token(
            user.mfa_secret,
            data.mfa_code,
            user.mfa_backup_codes,
        )
        
        if not mfa_result.valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=mfa_result.error_message or "Invalid MFA code",
            )
    
    # Record successful login
    user.record_login(request.client.host if request.client else None)
    await db.commit()
    
    # Create session
    await session_manager.create_session(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        roles=[user.role],
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        mfa_verified=user.mfa_enabled,
    )
    
    # Generate tokens
    tokens = jwt_manager.create_token_pair(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        roles=[user.role],
    )
    
    logger.info(
        f"User logged in",
        user_id=str(user.id),
        email=user.email,
        ip=request.client.host if request.client else None,
    )
    
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
        mfa_required=False,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    data: RefreshRequest,
    db: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """
    Refresh access token using refresh token.
    
    Args:
        request: HTTP request
        data: Refresh request
        db: Database session
        
    Returns:
        New token pair
    """
    try:
        # Decode refresh token
        payload = jwt_manager.decode_token(data.refresh_token, token_type="refresh")
        
        # Check blacklist
        is_blacklisted = await token_blacklist.is_blacklisted(payload.jti)
        if is_blacklisted:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
            )
        
        # Get user
        result = await db.execute(
            select(User).where(User.id == payload.sub)
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.can_login:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or account disabled",
            )
        
        # Generate new tokens
        tokens = jwt_manager.create_token_pair(
            user_id=str(user.id),
            tenant_id=str(user.tenant_id),
            roles=[user.role],
        )
        
        # Blacklist old refresh token
        await token_blacklist.blacklist(
            jti=payload.jti,
            expires_at=payload.exp,
            user_id=str(user.id),
            reason="token_refresh",
        )
        
        logger.info(
            f"Token refreshed",
            user_id=str(user.id),
        )
        
        return TokenResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            expires_in=tokens.expires_in,
        )
        
    except Exception as e:
        logger.warning(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )


@router.post("/logout")
async def logout(
    request: Request,
    data: LogoutRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Logout user and invalidate tokens.
    
    Args:
        request: HTTP request
        data: Logout options
        credentials: Authorization credentials
        db: Database session
        
    Returns:
        Success message
    """
    try:
        # Get token payload
        token = credentials.credentials
        payload = jwt_manager.decode_token(token, token_type="access")
        
        # Blacklist access token
        await token_blacklist.blacklist(
            jti=payload.jti,
            expires_at=payload.exp,
            user_id=payload.sub,
            reason="logout",
        )
        
        # Invalidate all user sessions if requested
        if data.all_devices:
            await session_manager.invalidate_user_sessions(payload.sub)
        
        logger.info(
            f"User logged out",
            user_id=payload.sub,
            all_devices=data.all_devices,
        )
        
        return {"message": "Successfully logged out"}
        
    except Exception as e:
        logger.warning(f"Logout failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


@router.post("/mfa/setup", response_model=MFASetupResponse)
async def setup_mfa(
    request: Request,
    data: MFASetupRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> MFASetupResponse:
    """
    Setup MFA for current user.
    
    Args:
        request: HTTP request
        data: MFA setup request
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        MFA setup data
    """
    if not settings.FEATURE_MFA_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not enabled",
        )
    
    # Generate MFA secret
    mfa_data = mfa_manager.generate_secret(
        user_id=str(current_user.id),
        email=current_user.email,
    )
    
    # Generate QR code
    qr_code = mfa_manager.generate_qr_code(mfa_data.uri)
    
    # Store secret (but don't enable MFA yet - need verification)
    current_user.mfa_secret = mfa_data.secret
    current_user.mfa_backup_codes = [
        mfa_manager.hash_backup_code(code)
        for code in mfa_data.backup_codes
    ]
    await db.commit()
    
    logger.info(
        f"MFA setup initiated",
        user_id=str(current_user.id),
    )
    
    return MFASetupResponse(
        secret=mfa_data.secret,
        qr_code=qr_code,
        backup_codes=mfa_data.backup_codes,
    )


@router.post("/mfa/verify")
async def verify_mfa_setup(
    request: Request,
    data: MFAVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Verify MFA setup and enable MFA.
    
    Args:
        request: HTTP request
        data: MFA verification request
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Success message
    """
    if not current_user.mfa_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA setup not initiated",
        )
    
    # Verify code
    result = mfa_manager.verify_token(
        current_user.mfa_secret,
        data.code,
    )
    
    if not result.valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code",
        )
    
    # Enable MFA
    current_user.mfa_enabled = True
    current_user.mfa_verified_at = datetime.utcnow()
    await db.commit()
    
    logger.info(
        f"MFA enabled",
        user_id=str(current_user.id),
    )
    
    return {"message": "MFA enabled successfully"}


@router.post("/mfa/disable")
async def disable_mfa(
    request: Request,
    data: MFAVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Disable MFA for current user.
    
    Args:
        request: HTTP request
        data: MFA verification request (to confirm)
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Success message
    """
    if not current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not enabled",
        )
    
    # Verify code before disabling
    result = mfa_manager.verify_token(
        current_user.mfa_secret,
        data.code,
        [code for code in (current_user.mfa_backup_codes or [])],
    )
    
    if not result.valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code",
        )
    
    # Disable MFA
    current_user.mfa_enabled = False
    current_user.mfa_secret = None
    current_user.mfa_backup_codes = None
    current_user.mfa_verified_at = None
    await db.commit()
    
    logger.info(
        f"MFA disabled",
        user_id=str(current_user.id),
    )
    
    return {"message": "MFA disabled successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current user profile.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current user
    """
    return current_user
