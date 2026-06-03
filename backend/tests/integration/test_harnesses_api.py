"""Integration tests for the harnesses API endpoints."""

import pytest

from app.harnesses.registry import HarnessProfile, harness_registry


@pytest.fixture(autouse=True)
def _seed_test_harnesses(tmp_path):
    """Seed the registry with test harnesses.

    The root conftest isolates all registries to temp paths automatically.
    """
    harness_registry._config_path = tmp_path / "harnesses.yaml"
    harness_registry._harnesses["test-builtin"] = HarnessProfile(
        id="test-builtin",
        name="Test Builtin",
        type="builtin",
        description="A test builtin harness",
        default=True,
        enabled=True,
        supported_features=["streaming", "tool_calls"],
    )
    harness_registry._harnesses["test-goose"] = HarnessProfile(
        id="test-goose",
        name="Test Goose",
        type="subprocess",
        binary_path="echo",
        description="A test goose harness",
        output_format="goose",
        enabled=False,
        supported_features=["tool_calls"],
    )
    harness_registry._persist_yaml()


@pytest.mark.asyncio
async def test_list_harnesses(client):
    response = await client.get("/api/v1/harnesses")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_list_filter_type(client):
    response = await client.get("/api/v1/harnesses?type=subprocess")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["type"] == "subprocess"


@pytest.mark.asyncio
async def test_get_harness(client):
    response = await client.get("/api/v1/harnesses/test-builtin")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Builtin"
    assert data["type"] == "builtin"
    assert data["default"] is True


@pytest.mark.asyncio
async def test_get_not_found(client):
    response = await client.get("/api/v1/harnesses/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_harness(client):
    payload = {"name": "New Harness", "type": "subprocess", "binary_path": "ls"}
    response = await client.post("/api/v1/harnesses", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Harness"
    assert data["id"] is not None

    list_resp = await client.get("/api/v1/harnesses")
    assert len(list_resp.json()) == 3


@pytest.mark.asyncio
async def test_update_harness(client):
    response = await client.put("/api/v1/harnesses/test-builtin", json={"name": "Updated"})
    assert response.status_code == 200
    assert response.json()["name"] == "Updated"


@pytest.mark.asyncio
async def test_delete_harness(client):
    response = await client.delete("/api/v1/harnesses/test-goose")
    assert response.status_code == 204

    get_resp = await client.get("/api/v1/harnesses/test-goose")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_not_found(client):
    response = await client.delete("/api/v1/harnesses/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_check_builtin(client):
    response = await client.post("/api/v1/harnesses/test-builtin/check")
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is True


@pytest.mark.asyncio
async def test_check_subprocess(client):
    response = await client.post("/api/v1/harnesses/test-goose/check")
    assert response.status_code == 200
    data = response.json()
    # echo should be available on most systems
    assert "available" in data
