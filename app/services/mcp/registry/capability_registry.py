"""Capability Registry: Layer A Universal Tools and Layer B Domain Wrappers."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.models.mcp import SystemMCPCredential, CapabilityGrant
from app.services.mcp.execution.dispatcher import GovernedExecutionDispatcher
from app.services.mcp.protocol import ToolResult


UNIVERSAL_TOOLS_SPEC: List[Dict[str, Any]] = [
    {
        "name": "octaos_discover_sources",
        "description": "Discover all active data connectors (internal OctaOS services, connected CRMs, SaaS APIs, databases) accessible to this client.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
        "required_action": "discover",
    },
    {
        "name": "octaos_list_objects",
        "description": "List all business objects (e.g. leads, tickets, content posts, customer accounts) available within a specified connector.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Connector slug (e.g. 'octaos'). Defaults to 'octaos'.",
                    "default": "octaos",
                },
            },
            "required": [],
        },
        "required_action": "discover",
    },
    {
        "name": "octaos_mcp_list_tools",
        "description": "Discover tools exposed by any tenant-registered external MCP server.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Registered external MCP server slug.",
                },
            },
            "required": ["source"],
        },
        "required_action": "discover",
    },
    {
        "name": "octaos_mcp_call_tool",
        "description": "Call a tool on any tenant-registered external MCP server through the governed policy boundary.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Registered external MCP server slug.",
                },
                "tool_name": {
                    "type": "string",
                    "description": "Exact MCP tool name returned by octaos_mcp_list_tools.",
                },
                "arguments": {
                    "type": "object",
                    "description": "Arguments accepted by the external MCP tool.",
                },
            },
            "required": ["source", "tool_name"],
        },
        "required_action": "invoke",
    },
    {
        "name": "octaos_describe_object",
        "description": "Retrieve the dynamic JSON Schema, fields, supported operations, and relationships for a specific business object.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "object": {
                    "type": "string",
                    "description": "Business object name (e.g. 'lead', 'ticket', 'content_post', 'customer_account').",
                },
                "source": {
                    "type": "string",
                    "description": "Connector slug. Defaults to 'octaos'.",
                    "default": "octaos",
                },
            },
            "required": ["object"],
        },
        "required_action": "discover",
    },
    {
        "name": "octaos_query_records",
        "description": "Query records of any business object using the safe typed query DSL (filtering, sorting, field projection, pagination).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "object": {
                    "type": "string",
                    "description": "Target business object name.",
                },
                "source": {
                    "type": "string",
                    "description": "Connector slug. Defaults to 'octaos'.",
                    "default": "octaos",
                },
                "fields": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of fields to return in projection.",
                },
                "filter": {
                    "type": "object",
                    "description": "Filter clauses: e.g. {'field': 'status', 'operator': 'eq', 'value': 'captured'} or {'and': [...]}",
                },
                "sort": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "field": {"type": "string"},
                            "direction": {"type": "string", "enum": ["asc", "desc"]},
                        },
                        "required": ["field"],
                    },
                    "description": "Sort directives.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max records to return (capped by policy).",
                    "default": 50,
                },
            },
            "required": ["object"],
        },
        "required_action": "query",
    },
    {
        "name": "octaos_get_record",
        "description": "Fetch a single record by its primary key identifier.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "object": {"type": "string", "description": "Target business object name."},
                "id": {"type": "string", "description": "Unique record identifier."},
                "source": {"type": "string", "default": "octaos"},
                "fields": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["object", "id"],
        },
        "required_action": "read",
    },
    {
        "name": "octaos_create_record",
        "description": "Create a new record for any business object. Input is validated dynamically against the object's JSON Schema.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "object": {"type": "string", "description": "Target business object name."},
                "source": {"type": "string", "default": "octaos"},
                "record": {
                    "type": "object",
                    "description": "Record key-value attributes to create.",
                },
            },
            "required": ["object", "record"],
        },
        "required_action": "create",
    },
    {
        "name": "octaos_update_record",
        "description": "Update attributes of an existing record by ID. Validated dynamically against object schema.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "object": {"type": "string", "description": "Target business object name."},
                "id": {"type": "string", "description": "Unique record identifier."},
                "source": {"type": "string", "default": "octaos"},
                "record": {
                    "type": "object",
                    "description": "Updated key-value attributes.",
                },
            },
            "required": ["object", "id", "record"],
        },
        "required_action": "update",
    },
    {
        "name": "octaos_delete_record",
        "description": "Delete a record by ID. Gated by explicit destructive delete permissions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "object": {"type": "string", "description": "Target business object name."},
                "id": {"type": "string", "description": "Unique record identifier."},
                "source": {"type": "string", "default": "octaos"},
            },
            "required": ["object", "id"],
        },
        "required_action": "delete",
    },
    {
        "name": "octaos_invoke_action",
        "description": "Execute a governed domain action (e.g. qualify_lead, reply_ticket, trigger_workflow).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action_name": {"type": "string", "description": "Domain action identifier."},
                "source": {"type": "string", "default": "octaos"},
                "arguments": {"type": "object", "description": "Action arguments."},
            },
            "required": ["action_name"],
        },
        "required_action": "invoke",
    },
]

# Layer B: Domain Convenience Wrappers
DOMAIN_WRAPPERS_SPEC: List[Dict[str, Any]] = [
    {
        "name": "octaos_create_lead",
        "description": "Convenience wrapper to capture a sales lead in OctaOS CRM.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Lead full name"},
                "email": {"type": "string", "description": "Contact email"},
                "company": {"type": "string", "description": "Company name"},
                "phone": {"type": "string", "description": "Phone number"},
                "status": {"type": "string", "default": "captured"},
                "need_of_what": {"type": "string", "description": "Buying intent/need"},
            },
            "required": ["name", "email"],
        },
        "required_action": "create",
        "wrapper_target": {"source": "octaos", "object": "lead", "action": "create"},
    },
    {
        "name": "octaos_reply_ticket",
        "description": "Convenience wrapper to post an official response to a customer support ticket.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string", "description": "Support Ticket ID"},
                "content": {"type": "string", "description": "Reply text to customer"},
            },
            "required": ["ticket_id", "content"],
        },
        "required_action": "invoke",
        "wrapper_target": {"source": "octaos", "object": "ticket", "action": "invoke", "action_name": "octaos.support.reply_ticket"},
    },
    {
        "name": "octaos_trigger_workflow",
        "description": "Convenience wrapper to trigger an automated business workflow.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workflow_id": {"type": "string", "description": "Workflow identifier"},
                "payload": {"type": "object", "description": "Input payload for workflow"},
            },
            "required": ["workflow_id"],
        },
        "required_action": "invoke",
        "wrapper_target": {"source": "octaos", "object": "workflow", "action": "invoke", "action_name": "octaos.workflows.trigger"},
    },
]


class CapabilityRegistry:
    """Manages tool advertising and routing for external clients."""

    def __init__(self, dispatcher: GovernedExecutionDispatcher):
        self.dispatcher = dispatcher

    def get_authorized_tools(self, db: Session, credential: SystemMCPCredential) -> List[Dict[str, Any]]:
        """
        Filters tools presented in tools/list based on the credential's grants.
        """
        if credential.role in ("admin", "super_admin"):
            all_specs = UNIVERSAL_TOOLS_SPEC + DOMAIN_WRAPPERS_SPEC
            return [self._format_tool_definition(t) for t in all_specs]

        grants = (
            db.query(CapabilityGrant)
            .filter(
                CapabilityGrant.credential_id == credential.id,
                CapabilityGrant.tenant_id == credential.tenant_id,
            )
            .all()
        )

        all_allowed_actions = set()
        for g in grants:
            all_allowed_actions.update(g.allowed_actions or [])

        advertised = []
        for t in UNIVERSAL_TOOLS_SPEC + DOMAIN_WRAPPERS_SPEC:
            req_act = t.get("required_action")
            if "*" in all_allowed_actions or req_act in all_allowed_actions:
                advertised.append(self._format_tool_definition(t))

        return advertised

    async def call_tool(
        self,
        credential: SystemMCPCredential,
        tool_name: str,
        arguments: Dict[str, Any],
        idempotency_key: Optional[str] = None,
    ) -> ToolResult:
        """
        Routes tool execution through the single governed execution dispatcher.
        """
        # Check domain wrappers first
        for dw in DOMAIN_WRAPPERS_SPEC:
            if dw["name"] == tool_name:
                target = dw["wrapper_target"]
                source = target["source"]
                obj = target["object"]
                action = target["action"]
                params = dict(arguments)
                if "action_name" in target:
                    params["action_name"] = target["action_name"]
                    params["arguments"] = arguments
                elif action == "create":
                    params = {"record": arguments}
                return await self.dispatcher.execute(
                    credential=credential,
                    connector_slug=source,
                    object_name=obj,
                    action=action,
                    parameters=params,
                    idempotency_key=idempotency_key,
                )

        # Handle Universal Tools
        source = arguments.get("source", "octaos")
        obj = arguments.get("object", "*")

        if tool_name == "octaos_discover_sources":
            return await self.dispatcher.execute(
                credential=credential,
                connector_slug=source,
                object_name="*",
                action="discover",
                parameters={},
                idempotency_key=idempotency_key,
            )
        elif tool_name == "octaos_list_objects":
            return await self.dispatcher.execute(
                credential=credential,
                connector_slug=source,
                object_name="*",
                action="discover",
                parameters={},
                idempotency_key=idempotency_key,
            )
        elif tool_name == "octaos_mcp_list_tools":
            return await self.dispatcher.execute(
                credential=credential,
                connector_slug=source,
                object_name="*",
                action="discover",
                parameters={},
                idempotency_key=idempotency_key,
            )
        elif tool_name == "octaos_mcp_call_tool":
            external_tool_name = arguments.get("tool_name")
            if not external_tool_name:
                return ToolResult(
                    content=[TextContent(text="Missing required 'tool_name'.")],
                    isError=True,
                    metadata={"error_code": "INVALID_PARAMS"},
                )
            return await self.dispatcher.execute(
                credential=credential,
                connector_slug=source,
                object_name=external_tool_name,
                action="invoke",
                parameters={
                    "action_name": external_tool_name,
                    "arguments": arguments.get("arguments") or {},
                },
                idempotency_key=idempotency_key,
            )
        elif tool_name == "octaos_describe_object":
            return await self.dispatcher.execute(
                credential=credential,
                connector_slug=source,
                object_name=obj,
                action="describe",
                parameters={},
                idempotency_key=idempotency_key,
            )
        elif tool_name == "octaos_query_records":
            return await self.dispatcher.execute(
                credential=credential,
                connector_slug=source,
                object_name=obj,
                action="query",
                parameters=arguments,
                idempotency_key=idempotency_key,
            )
        elif tool_name == "octaos_get_record":
            return await self.dispatcher.execute(
                credential=credential,
                connector_slug=source,
                object_name=obj,
                action="read",
                parameters=arguments,
                idempotency_key=idempotency_key,
            )
        elif tool_name == "octaos_create_record":
            return await self.dispatcher.execute(
                credential=credential,
                connector_slug=source,
                object_name=obj,
                action="create",
                parameters=arguments,
                idempotency_key=idempotency_key,
            )
        elif tool_name == "octaos_update_record":
            return await self.dispatcher.execute(
                credential=credential,
                connector_slug=source,
                object_name=obj,
                action="update",
                parameters=arguments,
                idempotency_key=idempotency_key,
            )
        elif tool_name == "octaos_delete_record":
            return await self.dispatcher.execute(
                credential=credential,
                connector_slug=source,
                object_name=obj,
                action="delete",
                parameters=arguments,
                idempotency_key=idempotency_key,
            )
        elif tool_name == "octaos_invoke_action":
            return await self.dispatcher.execute(
                credential=credential,
                connector_slug=source,
                object_name="*",
                action="invoke",
                parameters=arguments,
                idempotency_key=idempotency_key,
            )

        from app.services.mcp.protocol import TextContent
        return ToolResult(
            content=[TextContent(text=f"Unknown tool: '{tool_name}'")],
            isError=True,
            metadata={"error_code": "TOOL_NOT_FOUND"},
        )

    def _format_tool_definition(self, tool_meta: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "name": tool_meta["name"],
            "description": tool_meta["description"],
            "inputSchema": tool_meta["inputSchema"],
        }
