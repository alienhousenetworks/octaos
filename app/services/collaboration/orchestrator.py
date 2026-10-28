"""Collaboration Orchestrator: Loop prevention, cycle detection, idempotency, and webhooks."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
import httpx
from sqlalchemy.orm import Session

from app.models.collaborative_workforce import AgentMessage, DelegationReceipt

logger = logging.getLogger(__name__)

MAX_DELEGATION_DEPTH = 3
MAX_CHILDREN_PER_PARENT = 5


class DelegationLoopError(ValueError):
    """Raised when a task delegation loop or cycle is detected."""
    pass


class DelegationLimitError(ValueError):
    """Raised when delegation depth or child task limits are exceeded."""
    pass


def compute_task_fingerprint(tenant_id: str, task_description: str, context: Dict[str, Any]) -> str:
    """
    Computes a deterministic hash fingerprint to detect duplicate task submissions.
    """
    serialized_ctx = json.dumps(context, sort_keys=True, default=str)
    raw = f"{tenant_id}:{task_description.strip().lower()}:{serialized_ctx}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def validate_delegation_safety(
    db: Session,
    *,
    tenant_id: str,
    source_agent: str,
    target: str,
    lineage: List[str],
    parent_task_id: Optional[str] = None,
) -> Tuple[int, List[str]]:
    """
    Validates delegation limits and prevents cycles.
    Returns: (new_depth, updated_lineage)
    """
    # 1. Cycle Detection: Reject if target is already in the call lineage
    normalized_target = target.lower().strip()
    normalized_lineage = [step.lower().strip() for step in lineage]
    if normalized_target in normalized_lineage:
        raise DelegationLoopError(
            f"Delegation cycle detected: '{target}' already exists in lineage chain: {' -> '.join(lineage)}"
        )

    # 2. Depth Check: Maximum allowed parent-to-child depth
    current_depth = len(lineage)
    if current_depth >= MAX_DELEGATION_DEPTH:
        raise DelegationLimitError(
            f"Maximum delegation depth of {MAX_DELEGATION_DEPTH} exceeded. Lineage: {' -> '.join(lineage)}"
        )

    # Check child task limit for parent
    if parent_task_id:
        existing_children_count = (
            db.query(AgentMessage)
            .filter(
                AgentMessage.tenant_id == tenant_id,
                AgentMessage.payload["parent_task_id"].astext == parent_task_id
                if hasattr(AgentMessage.payload, "astext")
                else AgentMessage.correlation_id == parent_task_id
            )
            .count()
        )
        if existing_children_count >= MAX_CHILDREN_PER_PARENT:
            raise DelegationLimitError(
                f"Maximum of {MAX_CHILDREN_PER_PARENT} child tasks per parent task exceeded for parent '{parent_task_id}'."
            )

    updated_lineage = list(lineage) + [target]
    return current_depth + 1, updated_lineage


def check_duplicate_task(
    db: Session,
    *,
    tenant_id: str,
    fingerprint: str,
    lookback_minutes: int = 10,
) -> Optional[AgentMessage]:
    """
    Checks if an identical task was submitted recently within lookback window.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=lookback_minutes)
    existing = (
        db.query(AgentMessage)
        .filter(
            AgentMessage.tenant_id == tenant_id,
            AgentMessage.idempotency_key == fingerprint,
            AgentMessage.created_at >= cutoff,
        )
        .first()
    )
    return existing


async def dispatch_signed_webhook(
    webhook_url: str,
    payload: Dict[str, Any],
    secret: str,
    timeout_seconds: float = 10.0,
) -> bool:
    """
    Dispatches task completion notification with HMAC-SHA256 signature
    and anti-replay timestamp headers.
    """
    if not webhook_url:
        return False

    timestamp = str(int(time.time()))
    body_bytes = json.dumps(payload, default=str).encode("utf-8")
    sig_payload = f"{timestamp}.".encode("utf-8") + body_bytes
    signature = hmac.new(secret.encode("utf-8"), sig_payload, hashlib.sha256).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-OctaOS-Timestamp": timestamp,
        "X-OctaOS-Signature": f"sha256={signature}",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            res = await client.post(webhook_url, content=body_bytes, headers=headers)
            return res.is_success
    except Exception as e:
        logger.warning("Webhook dispatch failed to %s: %s", webhook_url, e)
        return False
