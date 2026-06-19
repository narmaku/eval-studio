"""Integration tests for the tool servers API endpoints."""

from unittest.mock import patch

import pytest

from app.core.tool_servers import StandaloneToolDef, ToolServerProfile, tool_server_registry


@pytest.fixture(autouse=True)
def _bypass_command_validation():
    """Bypass command validation for integration tests focused on CRUD behavior."""
    with patch(
        "app.api.v1._registry_helpers.validate_command",
        side_effect=lambda cmd, allowed, **kw: cmd,
    ):
        yield


@pytest.fixture(autouse=True)
def _seed_test_tool_servers(tmp_path):
    """Seed the registry with test tool servers.

    The root conftest isolates all registries to temp paths automatically.
    """
    tool_server_registry._config_path = tmp_path / "tool_servers.yaml"
    tool_server_registry._items["test-mcp"] = ToolServerProfile(
        id="test-mcp",
        name="Test MCP Server",
        type="mcp_stdio",
        command="echo",
        args=["hello"],
        env={"MY_SECRET": "hidden-value"},
        description="A test MCP server",
        tags=["test"],
        enabled=True,
    )
    tool_server_registry._items["test-standalone"] = ToolServerProfile(
        id="test-standalone",
        name="Test Standalone",
        type="standalone",
        tools=[StandaloneToolDef(name="lookup", description="Look up data", parameters={"type": "object"})],
        tags=["tools"],
        enabled=True,
    )
    tool_server_registry._persist_yaml()


@pytest.mark.asyncio
async def test_list_tool_servers(client):
    response = await client.get("/api/v1/tool-servers")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_list_filter_type(client):
    response = await client.get("/api/v1/tool-servers?type=mcp_stdio")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["type"] == "mcp_stdio"


@pytest.mark.asyncio
async def test_get_tool_server(client):
    response = await client.get("/api/v1/tool-servers/test-mcp")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test MCP Server"
    assert data["command"] == "echo"


@pytest.mark.asyncio
async def test_get_not_found(client):
    response = await client.get("/api/v1/tool-servers/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_tool_server(client):
    payload = {"name": "New Server", "type": "mcp_stdio", "command": "ls"}
    response = await client.post("/api/v1/tool-servers", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Server"
    assert data["id"] is not None

    list_resp = await client.get("/api/v1/tool-servers")
    assert len(list_resp.json()) == 3


@pytest.mark.asyncio
async def test_update_tool_server(client):
    response = await client.put("/api/v1/tool-servers/test-mcp", json={"name": "Updated"})
    assert response.status_code == 200
    assert response.json()["name"] == "Updated"


@pytest.mark.asyncio
async def test_delete_tool_server(client):
    response = await client.delete("/api/v1/tool-servers/test-mcp")
    assert response.status_code == 204

    get_resp = await client.get("/api/v1/tool-servers/test-mcp")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_not_found(client):
    response = await client.delete("/api/v1/tool-servers/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_env_not_exposed(client):
    response = await client.get("/api/v1/tool-servers/test-mcp")
    data = response.json()
    assert "env" not in data
    assert "env_keys" in data
    assert data["env_keys"] == ["MY_SECRET"]
    assert "hidden-value" not in response.text


@pytest.mark.asyncio
async def test_validate_mcp_server(client):
    response = await client.post("/api/v1/tool-servers/test-mcp/validate")
    assert response.status_code == 200
    data = response.json()
    assert "available" in data


@pytest.mark.asyncio
async def test_validate_standalone(client):
    response = await client.post("/api/v1/tool-servers/test-standalone/validate")
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is True
    assert data["tool_count"] == 1


@pytest.mark.asyncio
async def test_tool_count_standalone(client):
    response = await client.get("/api/v1/tool-servers/test-standalone")
    assert response.json()["tool_count"] == 1


@pytest.mark.asyncio
async def test_tool_count_mcp_null(client):
    response = await client.get("/api/v1/tool-servers/test-mcp")
    assert response.json()["tool_count"] is None


@pytest.mark.asyncio
async def test_create_returns_500_on_persist_failure(client):
    """POST returns 500 with detail when YAML persistence fails."""
    with patch(
        "app.core.registry_base.YAMLBackedRegistry._persist_yaml",
        side_effect=RuntimeError("Failed to save configuration to /tmp/config.yaml: Permission denied"),
    ):
        payload = {"name": "Doomed Server", "type": "mcp_stdio", "command": "echo"}
        response = await client.post("/api/v1/tool-servers", json=payload)
        assert response.status_code == 500
        body = response.json()
        assert "detail" in body
        assert "An internal error occurred" in body["detail"]


@pytest.mark.asyncio
async def test_update_returns_500_on_persist_failure(client):
    """PUT returns 500 with detail when YAML persistence fails."""
    with patch(
        "app.core.registry_base.YAMLBackedRegistry._persist_yaml",
        side_effect=RuntimeError("Failed to save configuration"),
    ):
        response = await client.put("/api/v1/tool-servers/test-mcp", json={"name": "Updated"})
        assert response.status_code == 500
        body = response.json()
        assert "detail" in body
        assert "An internal error occurred" in body["detail"]


@pytest.mark.asyncio
async def test_delete_returns_500_on_persist_failure(client):
    """DELETE returns 500 with detail when YAML persistence fails."""
    with patch(
        "app.core.registry_base.YAMLBackedRegistry._persist_yaml",
        side_effect=RuntimeError("Failed to save configuration"),
    ):
        response = await client.delete("/api/v1/tool-servers/test-mcp")
        assert response.status_code == 500
        body = response.json()
        assert "detail" in body
        assert "An internal error occurred" in body["detail"]
