"""Messages from OctaOS back to a connected MCP client.

The same credential that calls OctaOS can receive a message on its open stream
or on its next gateway call. Delivery is recorded only when the message is
handed to that channel. A queued row is not a claim that the client displayed it.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.models.collaborative_workforce import AgentMessage


def _target(credential_id: str) -> str:
    return f"mcp:{credential_id}"


def queue_client_message(
    db: Session,
    *,
    tenant_id: str,
    credential_id: str,
    client_name: str,
    text: str,
) -> Dict[str, Any]:
    message_id = str(uuid.uuid4())
    row = AgentMessage(
        id=message_id,
        tenant_id=tenant_id,
        correlation_id=message_id,
        idempotency_key=f"mcp-client:{message_id}",
        from_agent="Orchestrator AI",
        to_agent=_target(credential_id),
        message_type="mcp_client",
        status="queued",
        payload={"text": text, "client_name": client_name},
    )
    db.add(row)
    db.commit()
    from app.services.mcp.transport_http import push_to_open_streams

    pushed = push_to_open_streams(credential_id, {"id": message_id, "text": text, "from": "Orchestrator AI"})
    return {
        "id": message_id,
        "status": "queued",
        "open_streams": pushed,
        "client_name": client_name,
        "text": text,
        "webhook_status": "absent",
    }


def connections_for_client(db: Session, tenant_id: str, client_name: str) -> List[Any]:
    """Enabled outbound webhooks whose name matches this MCP client."""
    from app.models.external_agents import ExternalAgentConnection

    needle = (client_name or "").strip().lower()
    if not needle:
        return []
    rows = (
        db.query(ExternalAgentConnection)
        .filter(
            ExternalAgentConnection.tenant_id == tenant_id,
            ExternalAgentConnection.enabled == True,
        )
        .all()
    )
    tokens = [token for token in re.findall(r"[a-z0-9]{4,}", needle)]
    chosen = []
    for row in rows:
        blob = (row.name or "").lower()
        if needle in blob or blob in needle or any(token in blob for token in tokens):
            chosen.append(row)
    return chosen


async def dispatch_client_message(
    db: Session,
    *,
    tenant_id: str,
    credential_id: str,
    client_name: str,
    text: str,
) -> Dict[str, Any]:
    """Queue the message, push an open stream, and POST the saved webhook now."""
    placed = queue_client_message(
        db,
        tenant_id=tenant_id,
        credential_id=credential_id,
        client_name=client_name,
        text=text,
    )
    try:
        connections = connections_for_client(db, tenant_id, client_name)
    except Exception:
        return placed
    if not connections:
        return placed

    from app.services.webhooks.dispatcher import deliver_webhook, generate_envelope

    attempts = []
    for connection in connections:
        envelope = generate_envelope(
            event_type="agent.message",
            tenant_id=tenant_id,
            payload={
                "text": text,
                "client_name": client_name,
                "message_id": placed["id"],
                "from": "Orchestrator AI",
            },
            correlation_id=placed["id"],
        )
        try:
            delivery = await deliver_webhook(connection, envelope, db)
            attempts.append({
                "connection": connection.name,
                "status": delivery.status,
                "http_status": delivery.last_http_status,
                "error": delivery.last_error,
            })
        except Exception as exc:
            attempts.append({
                "connection": connection.name,
                "status": "failed",
                "http_status": None,
                "error": str(exc),
            })

    posted = next((item for item in attempts if item["status"] == "delivered"), None)
    if posted:
        row = db.query(AgentMessage).filter(AgentMessage.id == placed["id"]).first()
        if row is not None and row.status == "queued":
            payload = dict(row.payload or {})
            payload["webhook"] = {
                "connection": posted["connection"],
                "http_status": posted["http_status"],
            }
            row.payload = payload
            row.status = "delivered"
            row.completed_at = datetime.now(timezone.utc)
            db.commit()
        placed["status"] = "delivered"
        placed["webhook_status"] = "delivered"
        placed["webhook_http_status"] = posted["http_status"]
        return placed

    failed = attempts[0] if attempts else {}
    placed["webhook_status"] = "failed"
    placed["webhook_http_status"] = failed.get("http_status")
    placed["webhook_error"] = failed.get("error") or "the webhook call failed"
    return placed


def take_pending_messages(db: Session, tenant_id: str, credential_id: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Hand queued messages to this client's next response and mark that handoff."""
    rows = (
        db.query(AgentMessage)
        .filter(
            AgentMessage.tenant_id == tenant_id,
            AgentMessage.to_agent == _target(credential_id),
            AgentMessage.message_type == "mcp_client",
            AgentMessage.status == "queued",
        )
        .order_by(AgentMessage.created_at.asc())
        .limit(limit)
        .all()
    )
    now = datetime.now(timezone.utc)
    handed = []
    for row in rows:
        row.status = "delivered"
        row.completed_at = now
        payload = row.payload or {}
        handed.append({
            "id": row.id,
            "text": payload.get("text") or "",
            "from": row.from_agent,
            "client_name": payload.get("client_name"),
        })
    if handed:
        db.commit()
    return handed


def attach_pending_messages(db: Session, credential: Any, content: Any) -> Any:
    """Add messages waiting for this credential without dropping the original result."""
    messages = take_pending_messages(db, str(credential.tenant_id), str(credential.id))
    if not messages:
        return content
    if isinstance(content, dict):
        merged = dict(content)
        merged["messages_from_octaos"] = messages
        return merged
    return {"result": content, "messages_from_octaos": messages}
