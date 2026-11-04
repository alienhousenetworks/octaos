"""Adapter that exposes arbitrary tenant-configured MCP servers to OctaOS."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.security import decrypt_api_key
from app.models.mcp import DynamicConnector
from app.services.mcp.connectors.base import ConnectorAdapter, ConnectorContext, DiscoveredObjectMeta
from app.services.mcp.external_client import ExternalMCPClient, ExternalMCPError


class ExternalMCPAdapter(ConnectorAdapter):
    """Resolve a tenant's MCP connection from the database for every operation."""

    def __init__(self, db_factory):
        self.db_factory = db_factory

    def _load_config(self, ctx: ConnectorContext) -> Dict[str, Any]:
        db: Session = self.db_factory()
        try:
            connector = (
                db.query(DynamicConnector)
                .filter(
                    DynamicConnector.tenant_id == ctx.tenant_id,
                    DynamicConnector.slug == ctx.connector_slug,
                    DynamicConnector.connector_type == "mcp",
                )
                .first()
            )
            if not connector or connector.status == "suspended":
                raise ExternalMCPError(f"MCP connector '{ctx.connector_slug}' is unavailable.")
            if not connector.encrypted_config:
                raise ExternalMCPError(f"MCP connector '{ctx.connector_slug}' has no connection config.")
            return json.loads(decrypt_api_key(connector.encrypted_config))
        finally:
            db.close()

    async def _client(self, ctx: ConnectorContext) -> ExternalMCPClient:
        return ExternalMCPClient(self._load_config(ctx))

    async def discover_objects(self, ctx: ConnectorContext) -> List[DiscoveredObjectMeta]:
        client = await self._client(ctx)
        result = await client.list_tools()
        tools = result.get("tools", []) if isinstance(result, dict) else []
        discovered: List[DiscoveredObjectMeta] = []
        for tool in tools:
            name = str(tool.get("name") or "").strip()
            if not name:
                continue
            schema = tool.get("inputSchema") or {
                "type": "object",
                "properties": {},
                "additionalProperties": True,
            }
            discovered.append(
                DiscoveredObjectMeta(
                    object_name=name,
                    display_name=name.replace("_", " ").title(),
                    description=tool.get("description") or "External MCP tool",
                    primary_key="name",
                    supported_operations=["invoke"],
                    json_schema=schema,
                )
            )
        return discovered

    async def describe_object(self, ctx: ConnectorContext, object_name: str) -> Optional[DiscoveredObjectMeta]:
        for item in await self.discover_objects(ctx):
            if item.object_name == object_name:
                return item
        return None

    async def query_records(
        self,
        ctx: ConnectorContext,
        object_name: str,
        query: Dict[str, Any],
    ) -> Dict[str, Any]:
        raise ExternalMCPError("External MCP servers expose tools, not OctaOS record queries.")

    async def get_record(
        self,
        ctx: ConnectorContext,
        object_name: str,
        record_id: str,
        fields: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        raise ExternalMCPError("External MCP servers expose tools, not OctaOS records.")

    async def create_record(
        self,
        ctx: ConnectorContext,
        object_name: str,
        values: Dict[str, Any],
    ) -> Dict[str, Any]:
        return await self.invoke_action(ctx, object_name, values)

    async def update_record(
        self,
        ctx: ConnectorContext,
        object_name: str,
        record_id: str,
        values: Dict[str, Any],
    ) -> Dict[str, Any]:
        return await self.invoke_action(ctx, object_name, values)

    async def delete_record(self, ctx: ConnectorContext, object_name: str, record_id: str) -> bool:
        raise ExternalMCPError("External MCP tools cannot be deleted as OctaOS records.")

    async def invoke_action(
        self,
        ctx: ConnectorContext,
        action_name: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        client = await self._client(ctx)
        supplied = dict(arguments or {})
        confirmed = bool(supplied.pop("__octaos_confirm_side_effects", False))

        # Re-discover on every invocation: a remote server may change its tools
        # after connection. Never call a tool that is no longer advertised.
        discovery = await client.list_tools()
        tools = discovery.get("tools", []) if isinstance(discovery, dict) else []
        selected = next(
            (tool for tool in tools if tool.get("name") == action_name),
            None,
        )
        if selected is None:
            raise ExternalMCPError("Requested tool is not advertised by the remote MCP server.")

        annotations = selected.get("annotations") or {}
        if annotations.get("readOnlyHint") is not True and not confirmed:
            raise ExternalMCPError(
                "Remote tool is not explicitly marked read-only. "
                "Review its schema and set confirm_side_effects=true to acknowledge possible side effects."
            )

        # The marker is stripped above and never forwarded to the provider.
        result = await client.call_tool(action_name, supplied)
        return result if isinstance(result, dict) else {"result": result}
