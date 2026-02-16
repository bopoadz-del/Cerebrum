"""
Integration Tests for Authentication Endpoints

Tests for login, registration, token refresh, and MFA.
"""

import pytest
from httpx import AsyncClient


class TestAuthEndpoints:
    """Tests for authentication endpoints."""
    
    @pytest.mark.asyncio
    async def test_register(self, async_client: AsyncClient):
        """Test user registration."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "TestPassword123!",
                "full_name": "New User",
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["full_name"] == "New User"
    
    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, async_client: AsyncClient, user_data):
        """Test registration with duplicate email."""
        # First registration
        await async_client.post("/api/v1/auth/register", json=user_data)
        
        # Second registration with same email
        response = await async_client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_login(self, async_client: AsyncClient, user_data):
        """Test user login."""
        # Register user first
        await async_client.post("/api/v1/auth/register", json=user_data)
        
        # Login
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": user_data["email"],
                "password": user_data["password"],
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
    
    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, async_client: AsyncClient, user_data):
        """Test login with invalid credentials."""
        # Register user
        await async_client.post("/api/v1/auth/register", json=user_data)
        
        # Login with wrong password
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": user_data["email"],
                "password": "wrongpassword",
            },
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_refresh_token(self, async_client: AsyncClient, user_data):
        """Test token refresh."""
        # Register and login
        await async_client.post("/api/v1/auth/register", json=user_data)
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": user_data["email"],
                "password": user_data["password"],
            },
        )
        
        refresh_token = login_response.json()["refresh_token"]
        
        # Refresh token
        response = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
    
    @pytest.mark.asyncio
    async def test_get_me(self, async_client: AsyncClient, user_data):
        """Test get current user endpoint."""
        # Register and login
        await async_client.post("/api/v1/auth/register", json=user_data)
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": user_data["email"],
                "password": user_data["password"],
            },
        )
        
        access_token = login_response.json()["access_token"]
        
        # Get current user
        response = await async_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["full_name"] == user_data["full_name"]
    
    @pytest.mark.asyncio
    async def test_logout(self, async_client: AsyncClient, user_data):
        """Test logout endpoint."""
        # Register and login
        await async_client.post("/api/v1/auth/register", json=user_data)
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": user_data["email"],
                "password": user_data["password"],
            },
        )
        
        access_token = login_response.json()["access_token"]
        
        # Logout
        response = await async_client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"all_devices": False},
        )
        
        assert response.status_code == 200
        assert "Successfully logged out" in response.json()["message"]


class TestHealthEndpoints:
    """Tests for health check endpoints."""
    
    @pytest.mark.asyncio
    async def test_health_check(self, async_client: AsyncClient):
        """Test health check endpoint."""
        response = await async_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
    
    @pytest.mark.asyncio
    async def test_liveness_check(self, async_client: AsyncClient):
        """Test liveness probe endpoint."""
        response = await async_client.get("/health/live")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
    
    @pytest.mark.asyncio
    async def test_readiness_check(self, async_client: AsyncClient):
        """Test readiness probe endpoint."""
        response = await async_client.get("/health/ready")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
