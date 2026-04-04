"""
HashiCorp Vault Client

Provides secure secrets management with dynamic database credentials,
automatic lease renewal, and token lifecycle management.
"""

import asyncio
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

import httpx
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class VaultCredentials:
    """Vault database credentials."""
    username: str
    password: str
    lease_id: str
    lease_duration: int
    renewable: bool


class VaultError(Exception):
    """Vault client error."""
    pass


class VaultClient:
    """
    HashiCorp Vault client for secrets management.
    
    Provides:
    - Dynamic database credentials
    - Secret retrieval
    - Automatic lease renewal
    - Token lifecycle management
    """
    
    def __init__(self) -> None:
        """Initialize Vault client."""
        self._client: Optional[httpx.AsyncClient] = None
        self._token: Optional[str] = None
        self._token_expires: Optional[datetime] = None
        self._credentials_cache: Dict[str, VaultCredentials] = {}
        self._renewal_task: Optional[asyncio.Task] = None
        
    async def initialize(self) -> None:
        """Initialize Vault client and authenticate."""
        if not settings.VAULT_ENABLED:
            logger.info("Vault is disabled")
            return
        
        self._client = httpx.AsyncClient(
            base_url=settings.VAULT_ADDR,
            timeout=30.0,
        )
        
        await self._authenticate()
        logger.info("Vault client initialized")
    
    async def _authenticate(self) -> None:
        """Authenticate with Vault."""
        if settings.VAULT_TOKEN:
            # Token-based authentication
            self._token = settings.VAULT_TOKEN
            logger.debug("Using Vault token authentication")
            
        elif settings.VAULT_ROLE_ID and settings.VAULT_SECRET_ID:
            # AppRole authentication
            await self._auth_approle()
            
        else:
            raise VaultError("No Vault authentication method configured")
        
        # Verify token
        await self._verify_token()
    
    async def _auth_approle(self) -> None:
        """Authenticate using AppRole."""
        try:
            response = await self._client.post(
                "/v1/auth/approle/login",
                json={
                    "role_id": settings.VAULT_ROLE_ID,
                    "secret_id": settings.VAULT_SECRET_ID,
                },
            )
            response.raise_for_status()
            
            data = response.json()["auth"]
            self._token = data["client_token"]
            lease_duration = data.get("lease_duration", 3600)
            self._token_expires = datetime.utcnow() + timedelta(seconds=lease_duration)
            
            logger.info("Vault AppRole authentication successful")
            
        except httpx.HTTPError as e:
            raise VaultError(f"Vault AppRole authentication failed: {e}") from e
    
    async def _verify_token(self) -> None:
        """Verify token is valid."""
        try:
            response = await self._client.get(
                "/v1/auth/token/lookup-self",
                headers={"X-Vault-Token": self._token},
            )
            response.raise_for_status()
            logger.debug("Vault token verified")
            
        except httpx.HTTPError as e:
            raise VaultError(f"Vault token verification failed: {e}") from e
    
    async def _ensure_token(self) -> None:
        """Ensure token is valid, renew if needed."""
        if not self._token_expires:
            return
        
        # Renew if expiring in less than 5 minutes
        if datetime.utcnow() + timedelta(minutes=5) >= self._token_expires:
            await self._renew_token()
    
    async def _renew_token(self) -> None:
        """Renew Vault token."""
        try:
            response = await self._client.post(
                "/v1/auth/token/renew-self",
                headers={"X-Vault-Token": self._token},
            )
            response.raise_for_status()
            
            data = response.json()["auth"]
            lease_duration = data.get("lease_duration", 3600)
            self._token_expires = datetime.utcnow() + timedelta(seconds=lease_duration)
            
            logger.info("Vault token renewed")
            
        except httpx.HTTPError as e:
            logger.error(f"Vault token renewal failed: {e}")
            # Re-authenticate on renewal failure
            await self._authenticate()
    
    async def get_database_credentials(
        self,
        path: Optional[str] = None,
    ) -> VaultCredentials:
        """
        Get dynamic database credentials from Vault.
        
        Args:
            path: Path to database credentials in Vault
            
        Returns:
            Database credentials with lease information
        """
        if not settings.VAULT_ENABLED:
            raise VaultError("Vault is not enabled")
        
        await self._ensure_token()
        
        creds_path = path or settings.VAULT_DB_PATH
        
        try:
            response = await self._client.get(
                f"/v1/{creds_path}",
                headers={"X-Vault-Token": self._token},
            )
            response.raise_for_status()
            
            data = response.json()
            lease_data = data.get("lease", {})
            creds_data = data.get("data", {})
            
            credentials = VaultCredentials(
                username=creds_data.get("username"),
                password=creds_data.get("password"),
                lease_id=lease_data.get("id", ""),
                lease_duration=lease_data.get("duration", 3600),
                renewable=lease_data.get("renewable", False),
            )
            
            # Cache credentials
            self._credentials_cache[credentials.lease_id] = credentials
            
            # Start renewal task if renewable
            if credentials.renewable and not self._renewal_task:
                self._renewal_task = asyncio.create_task(
                    self._renewal_loop()
                )
            
            logger.info(
                "Retrieved database credentials from Vault",
                username=credentials.username,
                lease_duration=credentials.lease_duration,
            )
            
            return credentials
            
        except httpx.HTTPError as e:
            raise VaultError(f"Failed to get database credentials: {e}") from e
    
    async def _renewal_loop(self) -> None:
        """Background task for lease renewal."""
        while self._credentials_cache:
            await asyncio.sleep(60)  # Check every minute
            
            for lease_id, creds in list(self._credentials_cache.items()):
                if not creds.renewable:
                    continue
                
                try:
                    await self._renew_lease(lease_id)
                except Exception as e:
                    logger.error(f"Failed to renew lease {lease_id}: {e}")
                    # Remove from cache on renewal failure
                    del self._credentials_cache[lease_id]
    
    async def _renew_lease(self, lease_id: str) -> None:
        """Renew a lease."""
        try:
            response = await self._client.put(
                "/v1/sys/leases/renew",
                headers={"X-Vault-Token": self._token},
                json={"lease_id": lease_id},
            )
            response.raise_for_status()
            
            logger.debug(f"Renewed lease {lease_id}")
            
        except httpx.HTTPError as e:
            raise VaultError(f"Failed to renew lease: {e}") from e
    
    async def revoke_lease(self, lease_id: str) -> None:
        """
        Revoke a lease.
        
        Args:
            lease_id: Lease ID to revoke
        """
        if not settings.VAULT_ENABLED:
            return
        
        try:
            response = await self._client.put(
                "/v1/sys/leases/revoke",
                headers={"X-Vault-Token": self._token},
                json={"lease_id": lease_id},
            )
            response.raise_for_status()
            
            # Remove from cache
            self._credentials_cache.pop(lease_id, None)
            
            logger.info(f"Revoked lease {lease_id}")
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to revoke lease {lease_id}: {e}")
    
    async def get_secret(self, path: str) -> Dict[str, Any]:
        """
        Get secret from Vault.
        
        Args:
            path: Path to secret
            
        Returns:
            Secret data
        """
        if not settings.VAULT_ENABLED:
            raise VaultError("Vault is not enabled")
        
        await self._ensure_token()
        
        try:
            response = await self._client.get(
                f"/v1/{settings.VAULT_MOUNT_POINT}/data/{path}",
                headers={"X-Vault-Token": self._token},
            )
            response.raise_for_status()
            
            return response.json().get("data", {}).get("data", {})
            
        except httpx.HTTPError as e:
            raise VaultError(f"Failed to get secret: {e}") from e
    
    async def put_secret(self, path: str, data: Dict[str, Any]) -> None:
        """
        Store secret in Vault.
        
        Args:
            path: Path to store secret
            data: Secret data
        """
        if not settings.VAULT_ENABLED:
            raise VaultError("Vault is not enabled")
        
        await self._ensure_token()
        
        try:
            response = await self._client.post(
                f"/v1/{settings.VAULT_MOUNT_POINT}/data/{path}",
                headers={"X-Vault-Token": self._token},
                json={"data": data},
            )
            response.raise_for_status()
            
            logger.info(f"Stored secret at {path}")
            
        except httpx.HTTPError as e:
            raise VaultError(f"Failed to store secret: {e}") from e
    
    async def close(self) -> None:
        """Close Vault client and cleanup."""
        # Cancel renewal task
        if self._renewal_task:
            self._renewal_task.cancel()
            try:
                await self._renewal_task
            except asyncio.CancelledError:
                pass
        
        # Revoke all cached leases
        for lease_id in list(self._credentials_cache.keys()):
            await self.revoke_lease(lease_id)
        
        # Close HTTP client
        if self._client:
            await self._client.aclose()
        
        logger.info("Vault client closed")


# Global Vault client instance
vault_client = VaultClient()


async def get_vault_client() -> VaultClient:
    """Get initialized Vault client."""
    if not vault_client._client and settings.VAULT_ENABLED:
        await vault_client.initialize()
    return vault_client
