"""FastAPI endpoints for OctaOS Governed Dynamic MCP Platform."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
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
from app.services.mcp.transport_http import (
    extract_credential_from_request,
    handle_streamable_http,
    initiate_sse_session,
    handle_sse_message,
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
    elif req.credential_id:
        cred = (
            db.query(SystemMCPCredential)
            .filter(
                SystemMCPCredential.id == req.credential_id,
                SystemMCPCredential.tenant_id == current_user.tenant_id,
            )
            .first()
        )

    if not cred:
        return {"status": "error", "message": "Credential could not be authenticated."}

    # Execute a safe ping and tools/list check
    tools = mcp_server.registry.get_authorized_tools(db, cred)
    return {
        "status": "success",
        "credential_name": cred.name,
        "role": cred.role,
        "authorized_tools_count": len(tools),
        "sample_tools": [t["name"] for t in tools[:5]],
        "message": f"Connection verified. Client is authorized for {len(tools)} tools.",
    }
