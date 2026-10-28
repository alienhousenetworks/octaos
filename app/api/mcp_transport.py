"""Canonical, transport-only MCP endpoint.

The existing versioned management API remains under /api/v1/mcp. MCP clients
should use this protocol-only endpoint at /mcp, avoiding accidental exposure
of management routes on the public MCP transport path.
"""
from fastapi import APIRouter, Depends, Request
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
