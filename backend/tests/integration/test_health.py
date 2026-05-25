import pytest


@pytest.mark.asyncio
async def test_health_endpoint(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_health_response_has_correlation_id(client):
    response = await client.get("/api/v1/health")
    assert "x-request-id" in response.headers
