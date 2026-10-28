"""External Agent Connection Management, Webhook Deliveries, and Command Dispatch."""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.api import deps
from app.core.security import encrypt_api_key
from app.models.external_agents import (
    ExternalAgentConnection,
    WebhookSubscription,
    WebhookDelivery,
    ControllerCommand,
)
from app.services.webhooks.dispatcher import (
    test_connection_delivery,
    deliver_webhook,
    enqueue_webhook_event,
)

router = APIRouter()


class WebhookSubscriptionSchema(BaseModel):
    event_type: str
    enabled: bool = True


class ConnectionCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    endpoint_url: str = Field(..., min_length=7, max_length=500)
    auth_type: str = Field("bearer", description="bearer | hmac | custom_header")
    auth_secret: Optional[str] = Field(None, description="Secret token or key used for signing or headers")
    custom_header_name: Optional[str] = Field(None, max_length=120)
    enabled: bool = True
    description: Optional[str] = None
    subscriptions: List[str] = Field(default_factory=list, description="Subscribed event types, e.g. lead.created, *")


class ConnectionUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    endpoint_url: Optional[str] = Field(None, min_length=7, max_length=500)
    auth_type: Optional[str] = None
    auth_secret: Optional[str] = None
    custom_header_name: Optional[str] = None
    enabled: Optional[bool] = None
    description: Optional[str] = None
    subscriptions: Optional[List[str]] = None


class IssueCommandRequest(BaseModel):
    connection_id: Optional[str] = None
    command: str = Field(..., min_length=1)
    correlation_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)


def _serialize_connection(conn: ExternalAgentConnection) -> Dict[str, Any]:
    return {
        "id": conn.id,
        "name": conn.name,
        "endpoint_url": conn.endpoint_url,
        "auth_type": conn.auth_type,
        "has_secret": bool(conn.auth_secret_encrypted),
        "custom_header_name": conn.custom_header_name,
        "enabled": conn.enabled,
        "description": conn.description,
        "last_tested_at": conn.last_tested_at.isoformat() if conn.last_tested_at else None,
        "last_test_status": conn.last_test_status,
        "created_at": conn.created_at.isoformat() if conn.created_at else None,
        "subscriptions": [s.event_type for s in conn.subscriptions if s.enabled] if conn.subscriptions else [],
    }


@router.get("/connections")
def list_connections(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> Any:
    """List all registered external agent connections for the active tenant."""
    conns = (
        db.query(ExternalAgentConnection)
        .filter(ExternalAgentConnection.tenant_id == tenant_id)
        .order_by(ExternalAgentConnection.created_at.desc())
        .all()
    )
    return [_serialize_connection(c) for c in conns]


@router.post("/connections", status_code=status.HTTP_201_CREATED)
def create_connection(
    req: ConnectionCreateRequest,
    db: Session = Depends(deps.get_db),
    principal: deps.AuthPrincipal = Depends(deps.get_current_principal),
) -> Any:
    """Register a new external agent connection and configure event subscriptions."""
    tenant_id = principal.tenant_id

    existing = db.query(ExternalAgentConnection).filter(
        ExternalAgentConnection.tenant_id == tenant_id,
        ExternalAgentConnection.name == req.name,
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An external agent connection named '{req.name}' already exists.",
        )

    encrypted_secret = encrypt_api_key(req.auth_secret) if req.auth_secret else None

    conn = ExternalAgentConnection(
        tenant_id=tenant_id,
        name=req.name,
        endpoint_url=req.endpoint_url.strip(),
        auth_type=req.auth_type,
        auth_secret_encrypted=encrypted_secret,
        custom_header_name=req.custom_header_name,
        enabled=req.enabled,
        description=req.description,
        created_by=principal.user_id,
    )
    db.add(conn)
    db.flush()

    for event_name in set(req.subscriptions or []):
        sub = WebhookSubscription(
            connection_id=conn.id,
            tenant_id=tenant_id,
            event_type=event_name.strip(),
            enabled=True,
        )
        db.add(sub)

    db.commit()
    db.refresh(conn)
    return _serialize_connection(conn)


@router.put("/connections/{connection_id}")
def update_connection(
    connection_id: str,
    req: ConnectionUpdateRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> Any:
    """Update connection attributes, secrets, or subscriptions."""
    conn = db.query(ExternalAgentConnection).filter(
        ExternalAgentConnection.id == connection_id,
        ExternalAgentConnection.tenant_id == tenant_id,
    ).first()
    if not conn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found")

    if req.name is not None:
        conn.name = req.name
    if req.endpoint_url is not None:
        conn.endpoint_url = req.endpoint_url.strip()
    if req.auth_type is not None:
        conn.auth_type = req.auth_type
    if req.auth_secret is not None:
        conn.auth_secret_encrypted = encrypt_api_key(req.auth_secret) if req.auth_secret else None
    if req.custom_header_name is not None:
        conn.custom_header_name = req.custom_header_name
    if req.enabled is not None:
        conn.enabled = req.enabled
    if req.description is not None:
        conn.description = req.description

    if req.subscriptions is not None:
        db.query(WebhookSubscription).filter(WebhookSubscription.connection_id == conn.id).delete()
        for event_name in set(req.subscriptions):
            sub = WebhookSubscription(
                connection_id=conn.id,
                tenant_id=tenant_id,
                event_type=event_name.strip(),
                enabled=True,
            )
            db.add(sub)

    db.commit()
    db.refresh(conn)
    return _serialize_connection(conn)


@router.delete("/connections/{connection_id}")
def delete_connection(
    connection_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> Any:
    """Remove an external agent connection."""
    conn = db.query(ExternalAgentConnection).filter(
        ExternalAgentConnection.id == connection_id,
        ExternalAgentConnection.tenant_id == tenant_id,
    ).first()
    if not conn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found")

    db.delete(conn)
    db.commit()
    return {"message": "Connection deleted successfully", "id": connection_id}


@router.post("/connections/{connection_id}/test")
async def test_connection(
    connection_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> Any:
    """Send a test ping webhook to verify external agent connectivity."""
    conn = db.query(ExternalAgentConnection).filter(
        ExternalAgentConnection.id == connection_id,
        ExternalAgentConnection.tenant_id == tenant_id,
    ).first()
    if not conn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found")

    res = await test_connection_delivery(conn, db)
    return res


@router.get("/deliveries")
def list_deliveries(
    connection_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> Any:
    """Inspect outbound webhook deliveries, retry counts, latency, and status."""
    query = db.query(WebhookDelivery).filter(WebhookDelivery.tenant_id == tenant_id)
    if connection_id:
        query = query.filter(WebhookDelivery.connection_id == connection_id)
    if status_filter:
        query = query.filter(WebhookDelivery.status == status_filter)

    total = query.count()
    items = query.order_by(WebhookDelivery.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "items": [
            {
                "id": it.id,
                "connection_id": it.connection_id,
                "event_type": it.event_type,
                "correlation_id": it.correlation_id,
                "payload": it.payload_json,
                "status": it.status,
                "attempt_count": it.attempt_count,
                "last_http_status": it.last_http_status,
                "last_error": it.last_error,
                "delivered_at": it.delivered_at.isoformat() if it.delivered_at else None,
                "created_at": it.created_at.isoformat() if it.created_at else None,
            }
            for it in items
        ],
        "total": total,
    }


@router.post("/deliveries/{delivery_id}/replay")
async def replay_delivery(
    delivery_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> Any:
    """Manually replay a webhook delivery attempt."""
    delivery = db.query(WebhookDelivery).filter(
        WebhookDelivery.id == delivery_id,
        WebhookDelivery.tenant_id == tenant_id,
    ).first()
    if not delivery:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery record not found")

    conn = db.query(ExternalAgentConnection).filter(
        ExternalAgentConnection.id == delivery.connection_id,
        ExternalAgentConnection.tenant_id == tenant_id,
    ).first()
    if not conn:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Associated connection no longer exists")

    res = await deliver_webhook(conn, delivery.payload_json, db, delivery_record=delivery)
    return {
        "delivery_id": res.id,
        "status": res.status,
        "http_status": res.last_http_status,
        "error": res.last_error,
        "attempt_count": res.attempt_count,
    }


@router.post("/commands", status_code=status.HTTP_201_CREATED)
def issue_command(
    req: IssueCommandRequest,
    db: Session = Depends(deps.get_db),
    principal: deps.AuthPrincipal = Depends(deps.get_current_principal),
) -> Any:
    """
    Issue a high-priority command to an external controller or agent.
    Creates a ControllerCommand ledger entry and fires a command.issued webhook.
    """
    tenant_id = principal.tenant_id
    correlation_id = req.correlation_id or f"cmd_{uuid.uuid4().hex[:12]}"
    actor = principal.name or principal.key_name or "OctaOS Operator"

    cmd = ControllerCommand(
        tenant_id=tenant_id,
        connection_id=req.connection_id,
        correlation_id=correlation_id,
        command=req.command,
        context_json=req.context or {},
        status="sent",
        issued_by=actor,
    )
    db.add(cmd)
    db.commit()
    db.refresh(cmd)

    # Emit command.issued webhook
    enqueue_webhook_event(
        db=db,
        tenant_id=tenant_id,
        event_type="command.issued",
        payload={
            "command_id": cmd.id,
            "correlation_id": correlation_id,
            "command": cmd.command,
            "context": cmd.context_json,
            "issued_by": actor,
            "reply_endpoint": "/api/v1/controller/replies",
        },
        correlation_id=correlation_id,
    )

    return {
        "success": True,
        "command_id": cmd.id,
        "correlation_id": correlation_id,
        "status": cmd.status,
    }


@router.get("/commands")
def list_commands(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> Any:
    """List issued controller commands and their execution/reply states."""
    query = db.query(ControllerCommand).filter(ControllerCommand.tenant_id == tenant_id)
    total = query.count()
    items = query.order_by(ControllerCommand.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "items": [
            {
                "id": it.id,
                "connection_id": it.connection_id,
                "correlation_id": it.correlation_id,
                "command": it.command,
                "context": it.context_json,
                "status": it.status,
                "issued_by": it.issued_by,
                "reply_summary": it.reply_summary,
                "created_at": it.created_at.isoformat() if it.created_at else None,
                "updated_at": it.updated_at.isoformat() if it.updated_at else None,
            }
            for it in items
        ],
        "total": total,
    }
