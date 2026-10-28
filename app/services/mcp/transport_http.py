"""Streamable HTTP and SSE Fallback Transports for Model Context Protocol."""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any, AsyncGenerator, Dict, Optional
from fastapi import Request, HTTPException, status
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.mcp import SystemMCPCredential
from app.services.mcp.auth.credentials import authenticate_mcp_key
from app.services.mcp.server import mcp_server

logger = logging.getLogger(__name__)

# In-memory session registry for SSE connections
_ACTIVE_SSE_SESSIONS: Dict[str, asyncio.Queue] = {}
_SESSIONS_BY_CREDENTIAL: Dict[str, Dict[str, asyncio.Queue]] = {}


def extract_credential_from_request(request: Request, db: Session) -> SystemMCPCredential:
    """
    Extracts and authenticates MCP credential from:
    1. Header: Authorization: Bearer octa_mcp_...
    2. Header: X-OctaOS-Key: octa_mcp_...
    3. Query parameter: ?api_key=octa_mcp_...
    """
    auth_header = request.headers.get("Authorization")
    raw_key = None

    if auth_header and auth_header.startswith("Bearer "):
        raw_key = auth_header[7:].strip()
    elif request.headers.get("X-OctaOS-Key"):
        raw_key = request.headers.get("X-OctaOS-Key", "").strip()
    elif "api_key" in request.query_params:
        raw_key = request.query_params["api_key"].strip()

    if not raw_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing MCP API key. Provide via 'Authorization: Bearer octa_mcp_...' or '?api_key=...'",
        )

    cred = authenticate_mcp_key(db, raw_key)
    if not cred:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or deactivated MCP API key.",
        )

    return cred


async def handle_streamable_http(request: Request, credential: SystemMCPCredential) -> JSONResponse:
    """
    Primary MCP remote transport: Streamable HTTP POST.
    Handles standard JSON-RPC 2.0 requests or batches.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")

    if isinstance(body, list):
        # Batch requests
        responses = []
        for req in body:
            res = await mcp_server.handle_message(credential, req)
            if res is not None:
                responses.append(res)
        return JSONResponse(content=responses)
    else:
        # Single request
        res = await mcp_server.handle_message(credential, body)
        if res is None:
            return JSONResponse(status_code=204, content=None)
        from app.services.mcp.client_channel import attach_pending_messages
        from app.db.session import SessionLocal
        attach_db = SessionLocal()
        try:
            res = attach_pending_messages(attach_db, credential, res)
        finally:
            attach_db.close()
        return JSONResponse(content=res)


async def sse_event_generator(session_id: str, queue: asyncio.Queue) -> AsyncGenerator[str, None]:
    """Generates Server-Sent Events stream for legacy SSE clients."""
    try:
        # Initial endpoint announcement per MCP SSE spec
        yield f"event: endpoint\ndata: /api/v1/mcp/messages?session_id={session_id}\n\n"

        while True:
            # Wait for message to arrive on session queue
            message = await queue.get()
            if message is None:
                break
            yield f"event: message\ndata: {json.dumps(message)}\n\n"
    except asyncio.CancelledError:
        logger.info(f"SSE connection closed for session {session_id}")
    finally:
        _ACTIVE_SSE_SESSIONS.pop(session_id, None)
        for credential_id, sessions in list(_SESSIONS_BY_CREDENTIAL.items()):
            sessions.pop(session_id, None)
            if not sessions:
                _SESSIONS_BY_CREDENTIAL.pop(credential_id, None)


def initiate_sse_session(request: Request, credential: SystemMCPCredential) -> StreamingResponse:
    """Initiates an SSE stream session."""
    session_id = str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue()
    _ACTIVE_SSE_SESSIONS[session_id] = queue
    _SESSIONS_BY_CREDENTIAL.setdefault(str(credential.id), {})[session_id] = queue

    return StreamingResponse(
        sse_event_generator(session_id, queue),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def handle_sse_message(
    session_id: str,
    request: Request,
    credential: SystemMCPCredential,
) -> JSONResponse:
    """Receives JSON-RPC messages for an active SSE session."""
    queue = _ACTIVE_SSE_SESSIONS.get(session_id)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")

    res = await mcp_server.handle_message(credential, body)

    if queue and res is not None:
        await queue.put(res)

    return JSONResponse(status_code=202, content={"status": "accepted", "id": body.get("id")})


def push_to_open_streams(credential_id: str, payload: Dict[str, Any]) -> int:
    """Place one server message on every stream this MCP client currently holds."""
    sessions = _SESSIONS_BY_CREDENTIAL.get(str(credential_id), {})
    pushed = 0
    notice = {
        "jsonrpc": "2.0",
        "method": "notifications/message",
        "params": {"level": "info", "logger": "octaos", "data": payload},
    }
    for queue in list(sessions.values()):
        try:
            queue.put_nowait(notice)
            pushed += 1
        except Exception:
            logger.debug("Could not push to an MCP stream", exc_info=True)
    return pushed
