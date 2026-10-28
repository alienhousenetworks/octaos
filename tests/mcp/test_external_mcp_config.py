"""Regression tests for provider-neutral external MCP registration."""

import pytest

from app.services.mcp.external_client import (
    normalize_external_transport,
    validate_external_mcp_config,
)


def test_external_mcp_config_accepts_arbitrary_http_provider():
    config = validate_external_mcp_config(
        {
            "transport": "http",
            "endpoint": "https://mcp.provider.example/tools?token=secret",
            "headers": {"Authorization": "Bearer secret"},
        }
    )

    assert config["transport"] == "streamable_http"
    assert config["endpoint"].startswith("https://mcp.provider.example/")
    assert config["headers"]["Authorization"] == "Bearer secret"


def test_external_mcp_config_accepts_stdio_provider(monkeypatch):
    monkeypatch.setenv("OCTAOS_MCP_ALLOW_UNSANDBOXED_STDIO", "true")
    config = validate_external_mcp_config(
        {
            "transport": "stdio",
            "command": "npx -y provider-mcp-server",
            "args": ["--api-key", "$MCP_API_KEY"],
            "env": {"MCP_API_KEY": "secret"},
        }
    )

    assert config["transport"] == "stdio"
    assert config["args"][-1] == "$MCP_API_KEY"


def test_external_mcp_config_rejects_unknown_transport_and_invalid_endpoint():
    with pytest.raises(ValueError):
        normalize_external_transport("vendor_custom_socket")
    with pytest.raises(ValueError):
        validate_external_mcp_config({"transport": "sse", "endpoint": "file:///tmp/server"})
