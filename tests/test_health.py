import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test that the app is alive and returns correct app info."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "app_name" in data
    assert "env" in data


@pytest.mark.asyncio
async def test_readiness_check(client: AsyncClient):
    """Test that the database connection verification check works."""
    response = await client.get("/ready")
    # Should be 200 if connected to PG, otherwise 503
    assert response.status_code in [200, 503]
    data = response.json()
    if response.status_code == 200:
        assert data["status"] == "ready"
        assert data["database"] == "connected"
    else:
        assert data["status"] == "not_ready"
        assert data["database"] == "disconnected"
