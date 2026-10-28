"""Canonical, transport-only MCP endpoint.

The existing versioned management API remains under /api/v1/mcp. MCP clients
should use this protocol-only endpoint at /mcp, avoiding accidental exposure
of management routes on the public MCP transport path.
"""
import os
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api import deps
from app.services.mcp.transport_http import (
    extract_credential_from_request,
    handle_streamable_http,
)

router = APIRouter(tags=["mcp-protocol"])


@router.post("")
async def streamable_http_mcp(
    request: Request,
    db: Session = Depends(deps.get_db),
):
    """MCP Streamable HTTP transport (JSON-RPC over POST)."""
    origin = request.headers.get("origin")
    if origin:
        allowed_origins = {
            value.strip().rstrip("/")
            for value in os.getenv("MCP_ALLOWED_ORIGINS", "").split(",")
            if value.strip()
        }
        # Browser-originated requests fail closed unless deployment operators
        # explicitly configure trusted origins (DNS-rebinding mitigation).
        if origin.rstrip("/") not in allowed_origins:
            raise HTTPException(status_code=403, detail="Origin is not allowed for the MCP endpoint.")

    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type != "application/json":
        raise HTTPException(status_code=415, detail="MCP POST requests must use Content-Type: application/json.")

    accept = request.headers.get("accept", "*/*")
    accepted_types = {
        item.split(";", 1)[0].strip().lower()
        for item in accept.split(",")
        if item.strip()
    }
    if not ({"application/json", "*/*", "application/*"} & accepted_types):
        raise HTTPException(status_code=406, detail="This stateless MCP endpoint returns application/json.")

    credential = extract_credential_from_request(request, db)
    return await handle_streamable_http(request, credential)


@router.get("")
async def mcp_get_not_supported():
    """This endpoint is stateless and does not expose a server-initiated SSE stream."""
    return JSONResponse(
        status_code=405,
        content={"detail": "GET is not supported on this stateless MCP endpoint."},
        headers={"Allow": "POST"},
    )


@router.delete("")
async def mcp_delete_not_supported():
    """No server-side MCP session is created by this stateless endpoint."""
    return JSONResponse(
        status_code=405,
        content={"detail": "This MCP endpoint does not create stateful sessions."},
        headers={"Allow": "POST"},
    )
