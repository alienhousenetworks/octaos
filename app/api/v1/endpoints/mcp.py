"""FastAPI endpoints for OctaOS Governed Dynamic MCP Platform."""
from __future__ import annotations

import logging
import json
import re
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api import deps
from app.db.session import SessionLocal
from app.models.base import User, tenant_context
from app.models.mcp import SystemMCPCredential, CapabilityGrant, DynamicConnector, DynamicObjectDefinition
from app.services.mcp.auth.credentials import (
    authenticate_mcp_key,
    create_credential_with_grants,
)
from app.services.mcp.registry.schema_discovery import SchemaDiscoveryService
from app.services.mcp.connectors.octaos_internal import OctaOSInternalAdapter
from app.services.mcp.registry.capability_registry import UNIVERSAL_TOOLS_SPEC, DOMAIN_WRAPPERS_SPEC
from app.services.mcp.external_client import (
    ExternalMCPClient,
    ExternalMCPError,
    validate_external_mcp_config,
)
from app.core.security import decrypt_api_key, encrypt_api_key
from app.services.mcp.transport_http import (
    extract_credential_from_request,
    handle_streamable_http,
    initiate_sse_session,
    handle_sse_message,
    validate_mcp_origin,
)
from app.services.mcp.server import mcp_server

logger = logging.getLogger(__name__)

router = APIRouter()


# -------------------------------------------------------------
# MCP Protocol Gateway Routes (Authenticated via MCP API Key)
# -------------------------------------------------------------

@router.post("/stream")
async def mcp_stream_endpoint(
    request: Request,
    db: Session = Depends(deps.get_db),
):
    """
    Primary MCP Streamable HTTP transport endpoint.
    Processes JSON-RPC 2.0 requests over HTTP.
    """
    validate_mcp_origin(request)
    credential = extract_credential_from_request(request, db)
    return await handle_streamable_http(request, credential)


@router.get("/sse")
async def mcp_sse_endpoint(
    request: Request,
    db: Session = Depends(deps.get_db),
):
    """
    Legacy Server-Sent Events stream initialization.
    """
    validate_mcp_origin(request)
    credential = extract_credential_from_request(request, db)
    return initiate_sse_session(request, credential)


@router.post("/messages")
async def mcp_sse_message_endpoint(
    request: Request,
    session_id: str = Query(..., description="Active SSE session ID"),
    db: Session = Depends(deps.get_db),
):
    """
    Message receiver for an active SSE stream session.
    """
    validate_mcp_origin(request)
    credential = extract_credential_from_request(request, db)
    return await handle_sse_message(session_id, request, credential)


# -------------------------------------------------------------
# Hub Management & Configuration Routes (User Authenticated)
# -------------------------------------------------------------

class CreateCredentialRequest(BaseModel):
    name: str
    client_type: str = "generic" # claude_desktop, cursor, windsurf, zed, langchain, n8n, custom
    role: str = "read_only" # read_only, standard_operator, admin, custom
    grants: Optional[List[Dict[str, Any]]] = None
    rate_limit_rpm: int = 120
    max_records_per_query: int = 100
    expires_in_days: Optional[int] = None


class TestConnectionRequest(BaseModel):
    raw_key: Optional[str] = None
    credential_id: Optional[str] = None


class AddExternalMCPServerRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    slug: Optional[str] = Field(default=None, min_length=1, max_length=80)
    transport: str = "streamable_http"
    endpoint: Optional[str] = None
    command: Optional[str] = None
    args: List[str] = Field(default_factory=list)
    headers: Dict[str, str] = Field(default_factory=dict)
    env: Dict[str, str] = Field(default_factory=dict)
    timeout_seconds: float = 30.0

class CallExternalMCPToolRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    arguments: Dict[str, Any] = Field(default_factory=dict)
    # Remote tools can trigger external side effects. Require an explicit
    # acknowledgement unless the remote server marks the tool read-only.
    confirm_side_effects: bool = False


def _mcp_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug[:80] or "external-mcp"


def _external_mcp_config(req: AddExternalMCPServerRequest) -> Dict[str, Any]:
    return validate_external_mcp_config(
        {
            "transport": req.transport,
            "endpoint": req.endpoint,
            "command": req.command,
            "args": req.args,
            "headers": req.headers,
            "env": req.env,
            "timeout_seconds": req.timeout_seconds,
        }
    )


def _external_mcp_servers_query(db: Session, tenant_id: str):
    return (
        db.query(DynamicConnector)
        .filter(
            DynamicConnector.tenant_id == tenant_id,
            DynamicConnector.connector_type == "mcp",
        )
        .order_by(DynamicConnector.created_at.desc())
    )


def _external_mcp_server_response(connector: DynamicConnector) -> Dict[str, Any]:
    config: Dict[str, Any] = {}
    if connector.encrypted_config:
        try:
            config = json.loads(decrypt_api_key(connector.encrypted_config))
        except Exception:
            config = {}
    transport = config.get("transport", "streamable_http")
    target = config.get("endpoint") if transport != "stdio" else config.get("command")
    if target and transport != "stdio":
        parsed_target = urlsplit(str(target))
        target = urlunsplit((parsed_target.scheme, parsed_target.netloc, parsed_target.path, "", ""))
    return {
        "id": connector.id,
        "name": connector.name,
        "slug": connector.slug,
        "transport": transport,
        "target": target,
        "status": connector.status,
        "enabled": connector.status != "suspended",
        "has_headers": bool(config.get("headers")),
        "has_environment": bool(config.get("env")),
        "last_synced_at": connector.last_synced_at.isoformat() if connector.last_synced_at else None,
        "created_at": connector.created_at.isoformat() if connector.created_at else None,
    }


@router.get("/credentials")
def list_credentials(
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
):
    """List all active MCP credentials for the current tenant."""
    creds = (
        db.query(SystemMCPCredential)
        .filter(SystemMCPCredential.tenant_id == current_user.tenant_id)
        .order_by(SystemMCPCredential.created_at.desc())
        .all()
    )
    result = []
    for c in creds:
        grants = [
            {
                "connector_slug": g.connector_slug,
                "object_name": g.object_name,
                "allowed_actions": g.allowed_actions,
                "permitted_fields": g.permitted_fields,
                "denied_fields": g.denied_fields,
                "requires_approval": g.requires_approval,
            }
            for g in c.grants
        ]
        result.append({
            "id": c.id,
            "name": c.name,
            "client_type": c.client_type,
            "key_prefix": c.key_prefix,
            "role": c.role,
            "rate_limit_rpm": c.rate_limit_rpm,
            "max_records_per_query": c.max_records_per_query,
            "is_active": c.is_active,
            "last_used_at": c.last_used_at.isoformat() if c.last_used_at else None,
            "expires_at": c.expires_at.isoformat() if c.expires_at else None,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "grants": grants,
        })
    return {"credentials": result}


@router.post("/credentials")
def create_credential(
    req: CreateCredentialRequest,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
):
    """Create a new scoped MCP credential. Returns raw key once."""
    expires_at = None
    if req.expires_in_days and req.expires_in_days > 0:
        from datetime import timedelta, timezone
        expires_at = datetime.now(timezone.utc) + timedelta(days=req.expires_in_days)

    cred, raw_key = create_credential_with_grants(
        db=db,
        tenant_id=current_user.tenant_id,
        name=req.name,
        user_id=current_user.id,
        client_type=req.client_type,
        role=req.role,
        grants=req.grants,
        rate_limit_rpm=req.rate_limit_rpm,
        max_records_per_query=req.max_records_per_query,
        expires_at=expires_at,
    )

    return {
        "id": cred.id,
        "name": cred.name,
        "raw_key": raw_key, # DISPLAYED ONLY ONCE
        "key_prefix": cred.key_prefix,
        "role": cred.role,
        "client_type": cred.client_type,
        "created_at": cred.created_at.isoformat() if cred.created_at else None,
        "message": "Copy this key now. It will not be shown again.",
    }


@router.delete("/credentials/{credential_id}")
def revoke_credential(
    credential_id: str,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
):
    """Revokes an MCP credential immediately."""
    cred = (
        db.query(SystemMCPCredential)
        .filter(
            SystemMCPCredential.id == credential_id,
            SystemMCPCredential.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if not cred:
        raise HTTPException(status_code=404, detail="Credential not found.")

    cred.is_active = False
    db.commit()
    return {"status": "success", "message": f"Credential '{cred.name}' revoked."}


@router.get("/connectors")
async def list_connectors(
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
):
    """List connectors and discovered business objects for this tenant."""
    # Ensure default OctaOS connector is registered
    conn = SchemaDiscoveryService.get_or_register_default_octaos_connector(db, current_user.tenant_id)
    adapter = OctaOSInternalAdapter(db_factory=SessionLocal)
    await SchemaDiscoveryService.sync_connector_schemas(db, current_user.tenant_id, conn, adapter)

    connectors = (
        db.query(DynamicConnector)
        .filter(DynamicConnector.tenant_id == current_user.tenant_id)
        .all()
    )

    res = []
    for c in connectors:
        objects = [
            {
                "object_name": o.object_name,
                "display_name": o.display_name,
                "description": o.description,
                "supported_operations": o.supported_operations,
                "schema_fingerprint": o.schema_fingerprint,
                "is_stale": o.is_stale,
                "properties": list(o.schema_json.get("properties", {}).keys()),
            }
            for o in c.objects
        ]
        res.append({
            "id": c.id,
            "name": c.name,
            "slug": c.slug,
            "connector_type": c.connector_type,
            "status": c.status,
            "last_synced_at": c.last_synced_at.isoformat() if c.last_synced_at else None,
            "objects": objects,
        })
    return {"connectors": res}


@router.get("/servers")
def list_external_mcp_servers(
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
):
    """List any external MCP servers registered for the current tenant."""
    return {
        "servers": [
            _external_mcp_server_response(connector)
            for connector in _external_mcp_servers_query(db, current_user.tenant_id).all()
        ]
    }


@router.post("/servers")
def add_external_mcp_server(
    req: AddExternalMCPServerRequest,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
):
    """Register an arbitrary MCP server without a provider-specific allow-list."""
    try:
        config = _external_mcp_config(req)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    slug = _mcp_slug(req.slug or req.name)
    existing = (
        db.query(DynamicConnector)
        .filter(
            DynamicConnector.tenant_id == current_user.tenant_id,
            DynamicConnector.slug == slug,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail=f"MCP server slug '{slug}' is already registered.")

    connector = DynamicConnector(
        tenant_id=current_user.tenant_id,
        name=req.name.strip(),
        slug=slug,
        connector_type="mcp",
        is_read_only=False,
        encrypted_config=encrypt_api_key(json.dumps(config, sort_keys=True)),
        status="active",
    )
    db.add(connector)
    db.commit()
    db.refresh(connector)
    return _external_mcp_server_response(connector)


@router.post("/servers/{server_id}/test")
async def test_external_mcp_server(
    server_id: str,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
):
    """Initialize an external MCP server and discover its tools."""
    connector = (
        _external_mcp_servers_query(db, current_user.tenant_id)
        .filter(DynamicConnector.id == server_id)
        .first()
    )
    if not connector:
        raise HTTPException(status_code=404, detail="MCP server not found.")
    if not connector.encrypted_config:
        raise HTTPException(status_code=422, detail="MCP server has no connection configuration.")

    try:
        config = json.loads(decrypt_api_key(connector.encrypted_config))
        client = ExternalMCPClient(config)
        initialized = await client.initialize()
        tools = await client.list_tools()
        connector.status = "active"
        connector.last_synced_at = datetime.now(timezone.utc)
        db.commit()
        return {
            "status": "success",
            "server": _external_mcp_server_response(connector),
            "server_info": initialized.get("serverInfo", {}),
            "protocol_version": initialized.get("protocolVersion"),
            "tools": tools.get("tools", []) if isinstance(tools, dict) else [],
        }
    except (ExternalMCPError, ValueError, json.JSONDecodeError) as exc:
        connector.status = "degraded"
        db.commit()
        raise HTTPException(status_code=502, detail=f"MCP connection failed: {exc}") from exc
    except Exception as exc:
        connector.status = "degraded"
        db.commit()
        raise HTTPException(status_code=502, detail="MCP connection failed.") from exc


@router.get("/servers/{server_id}/tools")
async def list_external_mcp_server_tools(
    server_id: str,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
):
    """Discover live tools from a configured external MCP server."""
    connector = (
        _external_mcp_servers_query(db, current_user.tenant_id)
        .filter(DynamicConnector.id == server_id)
        .first()
    )
    if not connector:
        raise HTTPException(status_code=404, detail="MCP server not found.")
    if connector.status == "suspended":
        raise HTTPException(status_code=409, detail="MCP server is disabled.")
    if not connector.encrypted_config:
        raise HTTPException(status_code=422, detail="MCP server has no connection configuration.")
    try:
        config = json.loads(decrypt_api_key(connector.encrypted_config))
        tools = await ExternalMCPClient(config).list_tools()
        return {
            "server_id": connector.id,
            "server_name": connector.name,
            "tools": tools.get("tools", []) if isinstance(tools, dict) else [],
        }
    except (ExternalMCPError, ValueError, json.JSONDecodeError) as exc:
        connector.status = "degraded"
        db.commit()
        raise HTTPException(status_code=502, detail="Unable to discover tools from the external MCP server.") from exc


@router.post("/servers/{server_id}/tools/call")
async def call_external_mcp_server_tool(
    server_id: str,
    req: CallExternalMCPToolRequest,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
):
    """Invoke a discovered remote MCP tool with tenant-scoped configuration.

    Read-only tools can be called directly. Tools without an explicit
    readOnlyHint require confirm_side_effects=true in the request.
    """
    connector = (
        _external_mcp_servers_query(db, current_user.tenant_id)
        .filter(DynamicConnector.id == server_id)
        .first()
    )
    if not connector:
        raise HTTPException(status_code=404, detail="MCP server not found.")
    if connector.status == "suspended":
        raise HTTPException(status_code=409, detail="MCP server is disabled.")
    if not connector.encrypted_config:
        raise HTTPException(status_code=422, detail="MCP server has no connection configuration.")

    try:
        config = json.loads(decrypt_api_key(connector.encrypted_config))
        client = ExternalMCPClient(config)
        discovery = await client.list_tools()
        available_tools = discovery.get("tools", []) if isinstance(discovery, dict) else []
        selected = next((tool for tool in available_tools if tool.get("name") == req.name), None)
        if selected is None:
            raise HTTPException(status_code=404, detail="Tool was not advertised by the remote MCP server.")

        annotations = selected.get("annotations") or {}
        is_read_only = annotations.get("readOnlyHint") is True
        if not is_read_only and not req.confirm_side_effects:
            raise HTTPException(
                status_code=409,
                detail="Remote tool may have side effects. Review its schema and retry with confirm_side_effects=true.",
            )

        result = await client.call_tool(req.name, req.arguments)
        connector.last_synced_at = datetime.now(timezone.utc)
        connector.status = "active"
        db.commit()
        return {
            "status": "success",
            "server_id": connector.id,
            "tool_name": req.name,
            "result": result,
        }
    except HTTPException:
        raise
    except (ExternalMCPError, ValueError, json.JSONDecodeError) as exc:
        connector.status = "degraded"
        db.commit()
        raise HTTPException(status_code=502, detail="Remote MCP tool invocation failed.") from exc
    except Exception as exc:
        connector.status = "degraded"
        db.commit()
        raise HTTPException(status_code=502, detail="Remote MCP tool invocation failed.") from exc


@router.delete("/servers/{server_id}")
def delete_external_mcp_server(
    server_id: str,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
):
    """Remove an external MCP server and its discovered objects."""
    connector = (
        _external_mcp_servers_query(db, current_user.tenant_id)
        .filter(DynamicConnector.id == server_id)
        .first()
    )
    if not connector:
        raise HTTPException(status_code=404, detail="MCP server not found.")
    db.delete(connector)
    db.commit()
    return {"status": "success", "message": f"MCP server '{connector.name}' removed."}


@router.post("/servers/{server_id}/disable")
def disable_external_mcp_server(
    server_id: str,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
):
    """Disable an external MCP server without deleting its encrypted config."""
    connector = (
        _external_mcp_servers_query(db, current_user.tenant_id)
        .filter(DynamicConnector.id == server_id)
        .first()
    )
    if not connector:
        raise HTTPException(status_code=404, detail="MCP server not found.")
    connector.status = "suspended" if connector.status != "suspended" else "active"
    db.commit()
    db.refresh(connector)
    return _external_mcp_server_response(connector)


@router.post("/connectors/sync")
async def trigger_sync(
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
):
    """Triggers schema discovery sync and drift check."""
    conn = SchemaDiscoveryService.get_or_register_default_octaos_connector(db, current_user.tenant_id)
    adapter = OctaOSInternalAdapter(db_factory=SessionLocal)
    synced = await SchemaDiscoveryService.sync_connector_schemas(db, current_user.tenant_id, conn, adapter)
    return {
        "status": "success",
        "synced_objects_count": len(synced),
        "connector": conn.slug,
    }


@router.get("/catalog")
def get_catalog(
    current_user: User = Depends(deps.get_current_user),
):
    """Returns the available tool specifications and parameter contracts."""
    return {
        "universal_tools": UNIVERSAL_TOOLS_SPEC,
        "domain_wrappers": DOMAIN_WRAPPERS_SPEC,
    }


@router.post("/test-connection")
async def test_connection(
    req: TestConnectionRequest,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
):
    """Performs a safe read-only test using the credential."""
    cred = None
    if req.raw_key:
        cred = authenticate_mcp_key(db, req.raw_key)
        if cred and cred.tenant_id != current_user.tenant_id:
            cred = None
    elif req.credential_id:
        cred = (
            db.query(SystemMCPCredential)
            .filter(
                SystemMCPCredential.id == req.credential_id,
                SystemMCPCredential.tenant_id == current_user.tenant_id,
            )
            .first()
        )
        # Selecting a credential by ID does not run key authentication, so
        # explicitly update the connection heartbeat after tenant-scoped lookup.
        if cred and cred.is_active:
            cred.last_used_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(cred)

    if not cred or not cred.is_active or cred.tenant_id != current_user.tenant_id:
        return {"status": "error", "message": "Credential could not be authenticated."}

    # Exercise the protocol ping as well as the tenant-scoped authorization
    # registry. A credential lookup alone is not proof that MCP is responsive.
    ping = await mcp_server.handle_message(
        cred,
        {"jsonrpc": "2.0", "id": "connection-test", "method": "ping", "params": {}},
    )
    if not isinstance(ping, dict) or "result" not in ping:
        raise HTTPException(status_code=502, detail="MCP protocol ping failed.")

    tools = mcp_server.registry.get_authorized_tools(db, cred)
    return {
        "status": "success",
        "protocol_ping": "success",
        "credential_name": cred.name,
        "role": cred.role,
        "authorized_tools_count": len(tools),
        "sample_tools": [t["name"] for t in tools[:5]],
        "message": f"Connection verified. MCP ping succeeded; client is authorized for {len(tools)} tools.",
    }
