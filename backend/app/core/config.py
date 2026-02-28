"""
Application Configuration

Pydantic-based configuration management with environment variable support.
Provides type-safe access to all application settings.
"""

import secrets
from enum import Enum
from pathlib import Path
from typing import List, Optional, Union

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Application environment enumeration."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class LogLevel(str, Enum):
    """Logging level enumeration."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    """
    Application settings with environment variable support.
    
    All settings can be overridden via environment variables.
    Sensitive values should be loaded from secrets in production.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )
    
    # =================================================================
    # Application Settings
    # =================================================================
    APP_NAME: str = Field(default="Cerebrum AI Platform", description="Application name")
    APP_VERSION: str = Field(default="1.0.0", description="Application version")
    APP_DESCRIPTION: str = Field(
        default="AI-powered knowledge management platform",
        description="Application description",
    )
    DEBUG: bool = Field(default=False, description="Enable debug mode")
    ENVIRONMENT: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Application environment",
    )
    
    # =================================================================
    # Server Settings
    # =================================================================
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port")
    WORKERS: int = Field(default=4, description="Number of worker processes")
    RELOAD: bool = Field(default=False, description="Enable auto-reload")
    
    # =================================================================
    # Security Settings
    # =================================================================
    SECRET_KEY: str = Field(
        default="",
        description="Secret key for encryption (must be set via environment)",
    )
    PASSWORD_PEPPER: str = Field(
        default="",
        description="Pepper for password hashing",
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=15,
        description="Access token expiration in minutes",
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7,
        description="Refresh token expiration in days",
    )
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    MFA_ISSUER_NAME: str = Field(
        default="Cerebrum AI",
        description="TOTP issuer name",
    )
    
    # =================================================================
    # Database Settings
    # =================================================================
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://user:pass@localhost/cerebrum",
        description="Database connection URL",
    )
    DB_HOST: str = Field(default="localhost", description="Database host")
    DB_PORT: int = Field(default=5432, description="Database port")
    DB_NAME: str = Field(default="cerebrum", description="Database name")
    DB_USER: str = Field(default="user", description="Database user")
    DB_PASSWORD: str = Field(default="pass", description="Database password")
    
    # PgBouncer Settings
    PGBOUNCER_HOST: Optional[str] = Field(
        default=None,
        description="PgBouncer host",
    )
    PGBOUNCER_PORT: Optional[int] = Field(
        default=6432,
        description="PgBouncer port",
    )
    USE_PGBOUNCER: bool = Field(
        default=False,
        description="Use PgBouncer for connection pooling",
    )
    
    # =================================================================
    # Redis Settings
    # =================================================================
    REDIS_URL: Optional[str] = Field(
        default=None,
        description="Redis connection URL (overrides individual settings)",
    )
    REDIS_HOST: str = Field(default="localhost", description="Redis host")
    REDIS_PORT: int = Field(default=6379, description="Redis port")
    REDIS_PASSWORD: Optional[str] = Field(
        default=None,
        description="Redis password",
    )
    REDIS_DB_CACHE: int = Field(default=0, description="Redis cache database")
    REDIS_DB_QUEUE: int = Field(default=1, description="Redis queue database")
    REDIS_DB_SESSIONS: int = Field(default=2, description="Redis sessions database")
    REDIS_DB_RATE_LIMIT: int = Field(default=3, description="Redis rate limit database")
    
    # =================================================================
    # Vault Settings
    # =================================================================
    VAULT_ENABLED: bool = Field(default=False, description="Enable HashiCorp Vault")
    VAULT_ADDR: str = Field(default="http://localhost:8200", description="Vault address")
    VAULT_TOKEN: Optional[str] = Field(default=None, description="Vault token")
    VAULT_ROLE_ID: Optional[str] = Field(default=None, description="Vault AppRole ID")
    VAULT_SECRET_ID: Optional[str] = Field(default=None, description="Vault AppRole secret ID")
    VAULT_MOUNT_POINT: str = Field(default="secret", description="Vault mount point")
    VAULT_DB_PATH: str = Field(default="database/creds/app", description="Vault DB credentials path")
    
    # =================================================================
    # CORS Settings
    # =================================================================
    # Note: CORS_ORIGINS is a comma-separated string in env vars
    # It gets parsed into a list by the cors_origins_list property
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,https://cerebrum-frontend.onrender.com",
        description="Allowed CORS origins (comma-separated)",
    )
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True, description="Allow CORS credentials")
    CORS_ALLOW_METHODS: str = Field(
        default="*",
        description="Allowed CORS methods (comma-separated)",
    )
    CORS_ALLOW_HEADERS: str = Field(
        default="*",
        description="Allowed CORS headers (comma-separated)",
    )
    
    # =================================================================
    # Rate Limiting Settings
    # =================================================================
    RATE_LIMIT_ENABLED: bool = Field(default=True, description="Enable rate limiting")
    RATE_LIMIT_DEFAULT: str = Field(default="100/minute", description="Default rate limit")
    RATE_LIMIT_LOGIN: str = Field(default="5/minute", description="Login rate limit")
    RATE_LIMIT_REGISTER: str = Field(default="3/hour", description="Registration rate limit")
    
    # =================================================================
    # Logging Settings
    # =================================================================
    LOG_LEVEL: LogLevel = Field(default=LogLevel.INFO, description="Logging level")
    LOG_FORMAT: str = Field(default="json", description="Log format (json or text)")
    LOG_FILE: Optional[str] = Field(default=None, description="Log file path")
    
    # =================================================================
    # Sentry Settings
    # =================================================================
    SENTRY_ENABLED: bool = Field(default=False, description="Enable Sentry")
    SENTRY_DSN: Optional[str] = Field(default=None, description="Sentry DSN")
    SENTRY_ENVIRONMENT: str = Field(default="development", description="Sentry environment")
    SENTRY_TRACES_SAMPLE_RATE: float = Field(default=0.1, description="Sentry traces sample rate")
    
    # =================================================================
    # AWS Settings
    # =================================================================
    AWS_REGION: str = Field(default="us-east-1", description="AWS region")
    AWS_ACCESS_KEY_ID: Optional[str] = Field(default=None, description="AWS access key ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = Field(default=None, description="AWS secret access key")
    S3_BUCKET_NAME: Optional[str] = Field(default=None, description="S3 bucket name")
    S3_AUDIT_PREFIX: str = Field(default="audit-logs/", description="S3 audit log prefix")
    S3_BACKUP_PREFIX: str = Field(default="backups/", description="S3 backup prefix")
    
    # =================================================================
    # Google OAuth Settings
    # =================================================================
    GOOGLE_CLIENT_ID: Optional[str] = Field(default=None, description="Google OAuth client ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = Field(default=None, description="Google OAuth client secret")
    GOOGLE_REDIRECT_URI: str = Field(
        default="http://localhost:8000/api/v1/drive/auth/callback",
        description="Google OAuth redirect URI"
    )
    FRONTEND_URL: str = Field(default="http://localhost:3000", description="Frontend URL for OAuth origins")
    
    # =================================================================
    # Email Settings
    # =================================================================
    SMTP_HOST: Optional[str] = Field(default=None, description="SMTP host")
    SMTP_PORT: int = Field(default=587, description="SMTP port")
    SMTP_USER: Optional[str] = Field(default=None, description="SMTP user")
    SMTP_PASSWORD: Optional[str] = Field(default=None, description="SMTP password")
    SMTP_TLS: bool = Field(default=True, description="Use SMTP TLS")
    EMAIL_FROM: str = Field(default="noreply@cerebrum.ai", description="From email address")
    
    # =================================================================
    # Encryption Settings
    # =================================================================
    ENCRYPTION_KEY: Optional[str] = Field(
        default=None,
        description="Field-level encryption key",
    )
    
    # =================================================================
    # Feature Flags
    # =================================================================
    FEATURE_MFA_ENABLED: bool = Field(default=True, description="Enable MFA")
    FEATURE_AUDIT_LOGGING: bool = Field(default=True, description="Enable audit logging")
    FEATURE_API_KEYS: bool = Field(default=True, description="Enable API keys")
    
    # =================================================================
    # Compatibility & Stub Mode Settings
    # =================================================================
    USE_STUB_CONNECTORS: bool = Field(
        default=True,
        description="Use stub implementations for external connectors (safe for dev/testing)",
    )
    USE_STUB_ML: bool = Field(
        default=True,
        description="Use stub ML models when real models unavailable",
    )
    USE_STUB_NOTIFICATIONS: bool = Field(
        default=True,
        description="Use stub notification services (log only, don't send)",
    )
    STUB_FALLBACK_ENABLED: bool = Field(
        default=True,
        description="Enable graceful fallback to stubs when services fail",
    )
    
    # =================================================================
    # Testing Settings
    # =================================================================
    TEST_DATABASE_URL: Optional[str] = Field(
        default=None,
        description="Test database URL",
    )
    
    # =================================================================
    # Formula Library Settings
    # =================================================================
    INITIAL_FORMULAS_PATH: Optional[str] = Field(
        default=None,
        description="Path to initial formulas JSON library (relative to repo root or absolute)",
    )
    
    # =================================================================
    # Validators
    # =================================================================
    @field_validator("SECRET_KEY", mode="before")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate secret key is set and has minimum length."""
        if not v or v == "change-me":
            raise ValueError(
                "SECRET_KEY environment variable must be set to a secure value "
                "(at least 32 characters recommended)"
            )
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v
    
    # =================================================================
    # Properties
    # =================================================================
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT == Environment.DEVELOPMENT
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT == Environment.PRODUCTION
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.ENVIRONMENT == Environment.TESTING
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS_ORIGINS string into list."""
        # Always include production frontend URL
        default_origins = ["http://localhost:3000", "https://cerebrum-frontend.onrender.com"]
        if not self.CORS_ORIGINS:
            return default_origins
        env_origins = [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        # Merge env origins with defaults, removing duplicates
        return list(dict.fromkeys(env_origins + default_origins))
    
    @property
    def cors_methods_list(self) -> List[str]:
        """Parse CORS_ALLOW_METHODS string into list."""
        if not self.CORS_ALLOW_METHODS:
            return ["*"]
        return [method.strip() for method in self.CORS_ALLOW_METHODS.split(",") if method.strip()]
    
    @property
    def cors_headers_list(self) -> List[str]:
        """Parse CORS_ALLOW_HEADERS string into list."""
        if not self.CORS_ALLOW_HEADERS:
            return ["*"]
        return [header.strip() for header in self.CORS_ALLOW_HEADERS.split(",") if header.strip()]
    
    @property
    def async_database_url(self) -> str:
        """Get async database URL."""
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url
    
    @property
    def sync_database_url(self) -> str:
        """Get sync database URL."""
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        if url.startswith("postgresql+asyncpg://"):
            return url.replace("postgresql+asyncpg://", "postgresql://", 1)
        return url
    
    @property
    def redis_url(self) -> str:
        """Get Redis URL."""
        if self.REDIS_URL:
            return self.REDIS_URL
        
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}"
    
    @property
    def API_V1_STR(self) -> str:
        """Get API v1 prefix."""
        return "/api/v1"


# Global settings instance - Pydantic validates SECRET_KEY on instantiation
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings
