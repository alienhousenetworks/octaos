"""Outbound Webhook Dispatcher for External Agent Controllers."""
from __future__ import annotations

import json
import time
import uuid
import hashlib
import hmac
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.core.config import settings
from app.core.security import decrypt_api_key
from app.models.external_agents import ExternalAgentConnection, WebhookSubscription, WebhookDelivery
from app.services.agents.tools import validate_outbound_url, SSRFProtectionError

logger = logging.getLogger(__name__)

RETRY_SCHEDULE_SECONDS = [0, 30, 120, 600, 3600]


def generate_envelope(
    event_type: str,
    tenant_id: str,
    payload: Dict[str, Any],
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Builds canonical JSON envelope for outbound webhook delivery."""
    return {
        "id": f"evt_{uuid.uuid4().hex}",
        "event": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tenant_id": tenant_id,
        "correlation_id": correlation_id or f"corr_{uuid.uuid4().hex[:12]}",
        "payload": payload,
    }


def sign_webhook_headers(
    envelope_str: str,
    secret: Optional[str],
    delivery_id: str,
    event_type: str,
    auth_type: str = "hmac",
    custom_header_name: Optional[str] = None,
) -> Dict[str, str]:
    """Generates standard OctaOS webhook security headers including HMAC-SHA256 signature."""
    timestamp = str(int(time.time()))
    signing_secret = secret or settings.SECRET_KEY or "octaos-default-webhook-key"
    signature_payload = f"{timestamp}.{envelope_str}".encode("utf-8")
    signature = hmac.new(
        signing_secret.encode("utf-8"),
        signature_payload,
        hashlib.sha256,
    ).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-OctaOS-Delivery": delivery_id,
        "X-OctaOS-Event": event_type,
        "X-OctaOS-Timestamp": timestamp,
        "X-OctaOS-Signature": f"t={timestamp},v1={signature}",
    }

    if auth_type == "bearer" and secret:
        headers["Authorization"] = f"Bearer {secret}"
    elif auth_type == "custom_header" and custom_header_name and secret:
        headers[custom_header_name] = secret

    return headers


async def deliver_webhook(
    connection: ExternalAgentConnection,
    envelope: Dict[str, Any],
    db: Session,
    delivery_record: Optional[WebhookDelivery] = None,
) -> WebhookDelivery:
    """Delivers a webhook to an external agent with SSRF protection, HMAC signing, and status recording."""
    delivery_id = envelope.get("id") or f"evt_{uuid.uuid4().hex}"
    event_type = envelope.get("event", "unknown")
    correlation_id = envelope.get("correlation_id")

    # Retrieve or initialize WebhookDelivery ledger record
    if not delivery_record:
        delivery_record = db.query(WebhookDelivery).filter(WebhookDelivery.id == delivery_id).first()
    if not delivery_record:
        delivery_record = WebhookDelivery(
            id=delivery_id,
            tenant_id=connection.tenant_id,
            connection_id=connection.id,
            event_type=event_type,
            correlation_id=correlation_id,
            payload_json=envelope,
            status="pending",
            attempt_count=0,
        )
        db.add(delivery_record)
        db.flush()

    delivery_record.attempt_count = (delivery_record.attempt_count or 0) + 1

    # SSRF Protection
    try:
        safe_url = validate_outbound_url(connection.endpoint_url)
    except SSRFProtectionError as exc:
        delivery_record.status = "failed"
        delivery_record.last_error = f"SSRF Protection blocked URL: {exc}"
        db.commit()
        return delivery_record
    except Exception as exc:
        delivery_record.status = "failed"
        delivery_record.last_error = f"Invalid endpoint URL: {exc}"
        db.commit()
        return delivery_record

    # Resolve secret
    raw_secret = ""
    if connection.auth_secret_encrypted:
        try:
            raw_secret = decrypt_api_key(connection.auth_secret_encrypted)
        except Exception:
            raw_secret = connection.auth_secret_encrypted

    envelope_bytes = json.dumps(envelope, separators=(",", ":")).encode("utf-8")
    envelope_str = envelope_bytes.decode("utf-8")

    headers = sign_webhook_headers(
        envelope_str=envelope_str,
        secret=raw_secret,
        delivery_id=delivery_id,
        event_type=event_type,
        auth_type=connection.auth_type or "hmac",
        custom_header_name=connection.custom_header_name,
    )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                safe_url,
                content=envelope_bytes,
                headers=headers,
            )
            delivery_record.last_http_status = resp.status_code
            if 200 <= resp.status_code < 300:
                delivery_record.status = "delivered"
                delivery_record.delivered_at = func.now()
                delivery_record.last_error = None
            else:
                delivery_record.status = "failed"
                delivery_record.last_error = f"HTTP {resp.status_code}: {resp.text[:500]}"
    except httpx.RequestError as exc:
        delivery_record.status = "failed"
        delivery_record.last_error = f"Transport error: {str(exc)}"
    except Exception as exc:
        delivery_record.status = "failed"
        delivery_record.last_error = f"Unexpected delivery error: {str(exc)}"

    db.commit()
    db.refresh(delivery_record)
    return delivery_record


async def test_connection_delivery(
    connection: ExternalAgentConnection,
    db: Session,
) -> Dict[str, Any]:
    """Issues a test ping event to verify connectivity, authentication, and endpoint responsiveness."""
    start_time = time.monotonic()
    envelope = generate_envelope(
        event_type="connection.test",
        tenant_id=connection.tenant_id,
        payload={"message": "OctaOS external agent test ping", "connection_id": connection.id},
    )

    delivery = await deliver_webhook(connection, envelope, db)
    latency_ms = round((time.monotonic() - start_time) * 1000, 2)

    success = delivery.status == "delivered"
    connection.last_tested_at = func.now()
    connection.last_test_status = delivery.last_http_status or (200 if success else 500)
    db.commit()

    return {
        "success": success,
        "delivery_id": delivery.id,
        "status_code": delivery.last_http_status,
        "latency_ms": latency_ms,
        "error": delivery.last_error,
    }


def save_outbound_webhook(
    db: Session,
    *,
    tenant_id: str,
    name: str,
    endpoint_url: str,
    auth_type: str = "bearer",
    auth_secret: Optional[str] = None,
    custom_header_name: Optional[str] = None,
    created_by: Optional[str] = None,
    subscriptions: Optional[List[str]] = None,
) -> ExternalAgentConnection:
    """Save the URL OctaOS calls immediately when it has a message for this client."""
    from app.core.security import encrypt_api_key

    safe_url = validate_outbound_url(endpoint_url.strip())
    clean_name = name.strip()
    connection = (
        db.query(ExternalAgentConnection)
        .filter(
            ExternalAgentConnection.tenant_id == tenant_id,
            ExternalAgentConnection.name == clean_name,
        )
        .first()
    )
    if connection is None:
        connection = ExternalAgentConnection(
            tenant_id=tenant_id,
            name=clean_name,
            endpoint_url=safe_url,
            auth_type=auth_type or "bearer",
            enabled=True,
            created_by=created_by,
        )
        db.add(connection)
        db.flush()
    else:
        connection.endpoint_url = safe_url
        connection.auth_type = auth_type or connection.auth_type or "bearer"
        connection.enabled = True
    if auth_secret:
        connection.auth_secret_encrypted = encrypt_api_key(auth_secret)
    if custom_header_name:
        connection.custom_header_name = custom_header_name

    event_names = subscriptions or ["agent.message", "command.issued"]
    existing = {
        row.event_type
        for row in db.query(WebhookSubscription).filter(WebhookSubscription.connection_id == connection.id).all()
    }
    for event_name in {item.strip() for item in event_names if item and item.strip()}:
        if event_name in existing:
            continue
        db.add(WebhookSubscription(
            connection_id=connection.id,
            tenant_id=tenant_id,
            event_type=event_name,
            enabled=True,
        ))
    db.commit()
    db.refresh(connection)
    return connection


def enqueue_webhook_event(
    db: Session,
    tenant_id: str,
    event_type: str,
    payload: Dict[str, Any],
    correlation_id: Optional[str] = None,
) -> List[str]:
    """
    Fan out an event to all external agent connections with an active subscription.
    Enqueues delivery records and schedules worker dispatch.
    """
    # Find matching connections
    subscriptions = (
        db.query(WebhookSubscription)
        .join(ExternalAgentConnection, ExternalAgentConnection.id == WebhookSubscription.connection_id)
        .filter(
            WebhookSubscription.tenant_id == tenant_id,
            WebhookSubscription.enabled == True,
            ExternalAgentConnection.enabled == True,
            WebhookSubscription.event_type.in_([event_type, "*"]),
        )
        .all()
    )

    delivery_ids: List[str] = []
    if not subscriptions:
        return delivery_ids

    for sub in subscriptions:
        envelope = generate_envelope(
            event_type=event_type,
            tenant_id=tenant_id,
            payload=payload,
            correlation_id=correlation_id,
        )
        delivery = WebhookDelivery(
            id=envelope["id"],
            tenant_id=tenant_id,
            connection_id=sub.connection_id,
            event_type=event_type,
            correlation_id=envelope["correlation_id"],
            payload_json=envelope,
            status="pending",
            attempt_count=0,
        )
        db.add(delivery)
        delivery_ids.append(delivery.id)

    db.commit()

    # Attempt Celery task enqueue
    for del_id in delivery_ids:
        try:
            from app.worker.tasks import dispatch_webhook_delivery_task
            dispatch_webhook_delivery_task.delay(del_id)
        except Exception as exc:
            logger.info("Celery task dispatch skipped or delayed: %s", exc)

    return delivery_ids
