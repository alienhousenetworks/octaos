"""Regression tests for remote MCP tool discovery and side-effect gating."""
import pytest

from app.services.mcp.connectors.base import ConnectorContext
from app.services.mcp.connectors.external_mcp import ExternalMCPAdapter
from app.services.mcp.external_client import ExternalMCPError


class FakeMCPClient:
    def __init__(self, tools):
        self.tools = tools
        self.called = None

    async def list_tools(self):
        return {"tools": self.tools}

    async def call_tool(self, name, arguments):
        self.called = (name, arguments)
        return {"content": [{"type": "text", "text": "ok"}]}


def context():
    return ConnectorContext(
        tenant_id="tenant-test",
        connector_slug="remote-crm",
        credential_id="credential-test",
    )


@pytest.mark.asyncio
async def test_remote_mcp_tool_must_be_advertised(monkeypatch):
    adapter = ExternalMCPAdapter(db_factory=lambda: None)
    client = FakeMCPClient([{"name": "allowed_tool", "inputSchema": {"type": "object"}}])

    async def fake_client(_ctx):
        return client

    monkeypatch.setattr(adapter, "_client", fake_client)
    with pytest.raises(ExternalMCPError, match="not advertised"):
        await adapter.invoke_action(context(), "unknown_tool", {})


@pytest.mark.asyncio
async def test_unmarked_remote_tool_requires_explicit_confirmation(monkeypatch):
    adapter = ExternalMCPAdapter(db_factory=lambda: None)
    client = FakeMCPClient([
        {"name": "write_record", "annotations": {"readOnlyHint": False}},
    ])

    async def fake_client(_ctx):
        return client

    monkeypatch.setattr(adapter, "_client", fake_client)
    with pytest.raises(ExternalMCPError, match="confirm_side_effects=true"):
        await adapter.invoke_action(context(), "write_record", {"value": "x"})


@pytest.mark.asyncio
async def test_read_only_remote_tool_does_not_require_confirmation(monkeypatch):
    adapter = ExternalMCPAdapter(db_factory=lambda: None)
    client = FakeMCPClient([
        {"name": "search_records", "annotations": {"readOnlyHint": True}},
    ])

    async def fake_client(_ctx):
        return client

    monkeypatch.setattr(adapter, "_client", fake_client)
    await adapter.invoke_action(context(), "search_records", {"query": "Acme"})
    assert client.called == ("search_records", {"query": "Acme"})


@pytest.mark.asyncio
async def test_confirmation_marker_is_not_forwarded_to_remote_server(monkeypatch):
    adapter = ExternalMCPAdapter(db_factory=lambda: None)
    client = FakeMCPClient([
        {"name": "write_record", "annotations": {"readOnlyHint": False}},
    ])

    async def fake_client(_ctx):
        return client

    monkeypatch.setattr(adapter, "_client", fake_client)
    await adapter.invoke_action(
        context(),
        "write_record",
        {"value": "x", "__octaos_confirm_side_effects": True},
    )
    assert client.called == ("write_record", {"value": "x"})


def test_stdio_is_disabled_by_default_for_tenant_configured_servers(monkeypatch):
    from app.services.mcp.external_client import validate_external_mcp_config

    monkeypatch.delenv("OCTAOS_MCP_ALLOW_UNSANDBOXED_STDIO", raising=False)
    with pytest.raises(ValueError, match="disabled by default"):
        validate_external_mcp_config({"transport": "stdio", "command": "python"})


def test_stdio_requires_explicit_unsafe_opt_in(monkeypatch):
    from app.services.mcp.external_client import validate_external_mcp_config

    monkeypatch.setenv("OCTAOS_MCP_ALLOW_UNSANDBOXED_STDIO", "true")
    config = validate_external_mcp_config({"transport": "stdio", "command": "python"})
    assert config["transport"] == "stdio"
