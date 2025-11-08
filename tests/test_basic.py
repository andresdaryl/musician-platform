import pytest
from httpx import AsyncClient
from server import app

@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_register_user():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "testuser@example.com",
                "password": "TestPassword123",
                "display_name": "Test User"
            }
        )
        assert response.status_code in [201, 400]  # 400 if user already exists
