"""Database-backed webhook outbox for reliable collaboration callbacks."""
from __future__ import annotations

import uuid
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.models.collaborative_workforce import AgentMessage


def persist_webhook_outbox(
    db: Session,
    *,
    tenant_id: str,
    task_id: str,
    webhook_url: str,
    callback_payload: Dict[str, Any],
    credential_id: str,
) -> AgentMessage:
    """Persist callback intent in the same transaction as its task result."""
    key = f"collaboration-webhook:{task_id}"
    existing = db.query(AgentMessage).filter(
        AgentMessage.tenant_id == tenant_id,
        AgentMessage.idempotency_key == key,
    ).first()
    if existing:
        return existing
    row = AgentMessage(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        correlation_id=task_id,
        idempotency_key=key,
        from_agent="collaboration-engine",
        to_agent="webhook:delivery",
        message_type="webhook_outbox",
        status="queued",
        payload={
            "task_id": task_id,
            "webhook_url": webhook_url,
            "callback_payload": callback_payload,
            "credential_id": credential_id,
        },
    )
    db.add(row)
    return row
