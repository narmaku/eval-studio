"""Unit tests for ToolServerRegistry."""

from app.core.tool_servers import StandaloneToolDef, ToolServerProfile, ToolServerRegistry


def test_add_and_get(tmp_path):
    registry = ToolServerRegistry()
    registry._config_path = tmp_path / "tool_servers.yaml"
    profile = ToolServerProfile(id="ts-1", name="Test Server", type="mcp_stdio", command="echo")
    registry.add_tool_server(profile)

    result = registry.get_tool_server("ts-1")
    assert result is not None
    assert result.name == "Test Server"
    assert result.command == "echo"


def test_list_all(tmp_path):
    registry = ToolServerRegistry()
    registry._config_path = tmp_path / "tool_servers.yaml"
    registry.add_tool_server(ToolServerProfile(id="ts-1", name="Server 1", type="mcp_stdio"))
    registry.add_tool_server(ToolServerProfile(id="ts-2", name="Server 2", type="standalone"))

    servers = registry.list_tool_servers()
    assert len(servers) == 2


def test_list_filter_type(tmp_path):
    registry = ToolServerRegistry()
    registry._config_path = tmp_path / "tool_servers.yaml"
    registry.add_tool_server(ToolServerProfile(id="ts-1", name="MCP", type="mcp_stdio"))
    registry.add_tool_server(ToolServerProfile(id="ts-2", name="Standalone", type="standalone"))

    mcp = registry.list_tool_servers(type_filter="mcp_stdio")
    assert len(mcp) == 1
    assert mcp[0].type == "mcp_stdio"


def test_list_filter_enabled(tmp_path):
    registry = ToolServerRegistry()
    registry._config_path = tmp_path / "tool_servers.yaml"
    registry.add_tool_server(ToolServerProfile(id="ts-1", name="Enabled", enabled=True))
    registry.add_tool_server(ToolServerProfile(id="ts-2", name="Disabled", enabled=False))

    enabled = registry.list_tool_servers(enabled_only=True)
    assert len(enabled) == 1
    assert enabled[0].enabled is True


def test_update(tmp_path):
    registry = ToolServerRegistry()
    registry._config_path = tmp_path / "tool_servers.yaml"
    registry.add_tool_server(ToolServerProfile(id="ts-1", name="Original"))

    updated = registry.update_tool_server("ts-1", {"name": "Updated"})
    assert updated is not None
    assert updated.name == "Updated"


def test_delete(tmp_path):
    registry = ToolServerRegistry()
    registry._config_path = tmp_path / "tool_servers.yaml"
    registry.add_tool_server(ToolServerProfile(id="ts-1", name="Doomed"))

    assert registry.delete_tool_server("ts-1") is True
    assert registry.get_tool_server("ts-1") is None


def test_get_nonexistent(tmp_path):
    registry = ToolServerRegistry()
    registry._config_path = tmp_path / "tool_servers.yaml"
    assert registry.get_tool_server("nope") is None


def test_yaml_persistence(tmp_path):
    config_path = tmp_path / "tool_servers.yaml"
    reg1 = ToolServerRegistry()
    reg1._config_path = config_path
    reg1.add_tool_server(
        ToolServerProfile(
            id="ts-1",
            name="Persisted",
            type="standalone",
            tools=[StandaloneToolDef(name="my_tool", description="does stuff", parameters={"type": "object"})],
            tags=["test"],
        )
    )

    reg2 = ToolServerRegistry()
    reg2.load_from_yaml(config_path)
    result = reg2.get_tool_server("ts-1")
    assert result is not None
    assert result.name == "Persisted"
    assert result.type == "standalone"
    assert len(result.tools) == 1
    assert result.tools[0].name == "my_tool"
    assert result.tags == ["test"]


def test_mtime_reload(tmp_path):
    config_path = tmp_path / "tool_servers.yaml"
    registry = ToolServerRegistry()
    registry._config_path = config_path
    registry.add_tool_server(ToolServerProfile(id="ts-1", name="V1"))

    import time

    time.sleep(0.05)

    import yaml

    data = {"tool_servers": [{"id": "ts-1", "name": "V2", "type": "mcp_stdio", "enabled": True}]}
    with open(config_path, "w") as f:
        yaml.dump(data, f)

    result = registry.get_tool_server("ts-1")
    assert result is not None
    assert result.name == "V2"
