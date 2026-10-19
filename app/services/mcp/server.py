"""MCP Server Orchestrator: Protocol session handling, dispatch, and capability negotiation."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Union
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.mcp import SystemMCPCredential
from app.services.mcp.protocol import (
    LATEST_PROTOCOL_VERSION,
    RPCErrorCode,
    make_rpc_error,
    make_rpc_success,
)
from app.services.mcp.execution.dispatcher import GovernedExecutionDispatcher
from app.services.mcp.registry.capability_registry import CapabilityRegistry

logger = logging.getLogger(__name__)


class MCPServer:
    """
    Standard Model Context Protocol Server.
    Processes JSON-RPC requests, negotiates protocol version,
    and dispatches tool/resource calls governed by policy.
    """

    def __init__(self, db_factory=SessionLocal):
        self.db_factory = db_factory
        self.dispatcher = GovernedExecutionDispatcher(db_factory=db_factory)
        self.registry = CapabilityRegistry(dispatcher=self.dispatcher)

    async def handle_message(
        self,
        credential: SystemMCPCredential,
        message: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Handles an incoming JSON-RPC message from an authenticated MCP client.
        """
        if not isinstance(message, dict):
            return make_rpc_error(None, RPCErrorCode.INVALID_REQUEST, "Message must be a JSON object.")

        msg_id = message.get("id")
        method = message.get("method")
        params = message.get("params") or {}

        if not method:
            return make_rpc_error(msg_id, RPCErrorCode.INVALID_REQUEST, "Missing 'method' field.")

        # Notification handling (no response expected for notifications)
        is_notification = (msg_id is None)

        try:
            # 1. Initialization Handshake
            if method == "initialize":
                client_version = params.get("protocolVersion", LATEST_PROTOCOL_VERSION)
                res = {
                    "protocolVersion": LATEST_PROTOCOL_VERSION,
                    "capabilities": {
                        "tools": {"listChanged": False},
                        "resources": {"subscribe": False, "listChanged": False},
                    },
                    "serverInfo": {
                        "name": "octaos-governed-mcp-platform",
                        "version": "2.0.0",
                        "description": "Enterprise Governed MCP Gateway for OctaOS Dynamic Business Capabilities",
                    },
                }
                return make_rpc_success(msg_id, res)

            elif method == "notifications/initialized":
                logger.info(f"Client initialized successfully for credential {credential.name}")
                return None

            # 2. Ping
            elif method == "ping":
                return make_rpc_success(msg_id, {})

            # 3. Tool Discovery
            elif method == "tools/list":
                db: Session = self.db_factory()
                try:
                    tools = self.registry.get_authorized_tools(db, credential)
                    return make_rpc_success(msg_id, {"tools": tools})
                finally:
                    db.close()

            # 4. Tool Invocation
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments") or {}
                if not tool_name:
                    return make_rpc_error(msg_id, RPCErrorCode.INVALID_PARAMS, "Missing tool 'name' parameter.")

                tool_result = await self.registry.call_tool(
                    credential=credential,
                    tool_name=tool_name,
                    arguments=arguments,
                    idempotency_key=params.get("idempotency_key"),
                )
                return make_rpc_success(msg_id, tool_result.model_dump())

            # 5. Resources Discovery & Read
            elif method == "resources/list":
                resources = [
                    {
                        "uri": "octaos://sources",
                        "name": "Active Connectors",
                        "description": "List of active connected systems in OctaOS",
                        "mimeType": "application/json",
                    },
                    {
                        "uri": "octaos://health",
                        "name": "System Health",
                        "description": "Connection health and tenant status",
                        "mimeType": "application/json",
                    },
                ]
                return make_rpc_success(msg_id, {"resources": resources})

            elif method == "resources/read":
                uri = params.get("uri")
                if uri == "octaos://sources":
                    contents = [{"uri": uri, "mimeType": "application/json", "text": "{\"sources\": [\"octaos\"]}"}]
                    return make_rpc_success(msg_id, {"contents": contents})
                elif uri == "octaos://health":
                    contents = [{"uri": uri, "mimeType": "application/json", "text": "{\"status\": \"healthy\", \"tenant\": \"" + credential.tenant_id + "\"}"}]
                    return make_rpc_success(msg_id, {"contents": contents})
                return make_rpc_error(msg_id, RPCErrorCode.RESOURCE_NOT_FOUND, f"Resource URI '{uri}' not found.")

            # Unknown Method
            if is_notification:
                return None
            return make_rpc_error(msg_id, RPCErrorCode.METHOD_NOT_FOUND, f"Method '{method}' is not implemented.")

        except Exception as e:
            logger.exception(f"Error handling MCP message: {e}")
            if is_notification:
                return None
            return make_rpc_error(msg_id, RPCErrorCode.INTERNAL_ERROR, f"Internal error: {str(e)}")


mcp_server = MCPServer()
