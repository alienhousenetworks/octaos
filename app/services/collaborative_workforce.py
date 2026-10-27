"""Persistence primitives for safe cross-agent hand-offs.

This service deliberately does not call an LLM or execute tools. Callers must
authorize both agents and validate the requested capability before enqueueing.
A response is a claim, not verified completion, until criteria/evidence pass.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.collaborative_workforce import AgentMessage, DelegationReceipt


class CollaborationError(ValueError):
    pass


def enqueue_agent_request(
    db: Session,
    *,
    tenant_id: str,
    correlation_id: str,
    idempotency_key: str,
    from_agent: str,
    to_agent: str,
    payload: Dict[str, Any],
) -> AgentMessage:
    """Persist a request once. A repeated tenant/key returns the original record."""
    if not all(str(v).strip() for v in (tenant_id, correlation_id, idempotency_key, from_agent, to_agent)):
        raise CollaborationError("tenant, correlation, idempotency, and agent identifiers are required")
    if from_agent == to_agent:
        raise CollaborationError("an agent cannot delegate a task to itself")
    existing = db.query(AgentMessage).filter_by(
        tenant_id=tenant_id, idempotency_key=idempotency_key
    ).one_or_none()
    if existing:
        if existing.from_agent != from_agent or existing.to_agent != to_agent:
            raise CollaborationError("idempotency key already belongs to a different hand-off")
        return existing

    message = AgentMessage(
        id=str(uuid4()), tenant_id=tenant_id, correlation_id=correlation_id,
        idempotency_key=idempotency_key, from_agent=from_agent, to_agent=to_agent,
        message_type="request", status="queued", payload=payload or {},
    )
    db.add(message)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.query(AgentMessage).filter_by(
            tenant_id=tenant_id, idempotency_key=idempotency_key
        ).one_or_none()
        if existing:
            return existing
        raise
    db.refresh(message)
    return message


def claim_next_message(
    db: Session, *, tenant_id: str, agent_id: str
) -> Optional[AgentMessage]:
    """Claim the oldest queued inbox message; use row locking where supported."""
    query = db.query(AgentMessage).filter_by(
        tenant_id=tenant_id, to_agent=agent_id, status="queued"
    ).order_by(AgentMessage.created_at.asc()).with_for_update(skip_locked=True)
    message = query.first()
    if message is None:
        return None
    message.status = "processing"
    message.attempt_count = (message.attempt_count or 0) + 1
    db.commit()
    db.refresh(message)
    return message


def complete_agent_message(
    db: Session, *, tenant_id: str, message_id: str, agent_id: str,
    response: Dict[str, Any]
) -> AgentMessage:
    """Only the addressed agent may complete its message, within the same tenant."""
    message = db.query(AgentMessage).filter_by(
        id=message_id, tenant_id=tenant_id, to_agent=agent_id
    ).with_for_update().one_or_none()
    if message is None:
        raise CollaborationError("message not found for this tenant and agent")
    if message.status != "processing":
        raise CollaborationError(f"cannot complete a message in status {message.status}")
    message.response = response or {}
    message.status = "completed"
    message.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(message)
    return message


def verify_delegated_result(
    *, result: Dict[str, Any], acceptance_criteria: Iterable[str],
    evidence: Iterable[Dict[str, Any]]
) -> Dict[str, Any]:
    """Conservative structural gate; never interprets an LLM's 'success' as proof."""
    criteria = [str(c).strip() for c in acceptance_criteria if str(c).strip()]
    evidence_items = [e for e in evidence if isinstance(e, dict) and e.get("source") and e.get("claim")]
    errors = []
    if not isinstance(result, dict) or not result:
        errors.append("missing_structured_result")
    if criteria and not result.get("criterion_results"):
        errors.append("acceptance_criteria_not_individually_evaluated")
    else:
        reported = result.get("criterion_results", {})
        for criterion in criteria:
            if not isinstance(reported, dict) or reported.get(criterion) is not True:
                errors.append("criterion_not_verified:" + criterion[:120])
    if not evidence_items:
        errors.append("no_claim_linked_evidence")
    return {
        "verified": not errors,
        "status": "verified" if not errors else "needs_review",
        "errors": errors,
        "evidence_count": len(evidence_items),
        "criteria_count": len(criteria),
    }


def record_delegation(
    db: Session, *, tenant_id: str, task_id: str, parent_agent: str,
    child_agent: str, request_message_id: str, acceptance_criteria: list,
    result: Dict[str, Any], evidence: list
) -> DelegationReceipt:
    """Persist a reviewable receipt; only structurally verified outputs get verified status."""
    message = db.query(AgentMessage).filter_by(
        id=request_message_id, tenant_id=tenant_id
    ).one_or_none()
    if message is None or message.from_agent != parent_agent or message.to_agent != child_agent:
        raise CollaborationError("delegation does not match the tenant-scoped request")
    gate = verify_delegated_result(
        result=result, acceptance_criteria=acceptance_criteria, evidence=evidence
    )
    receipt = DelegationReceipt(
        tenant_id=tenant_id, task_id=task_id, parent_agent=parent_agent,
        child_agent=child_agent, request_message_id=request_message_id,
        status=gate["status"], acceptance_criteria=acceptance_criteria or [],
        result=result or {}, evidence=evidence or [],
        verification_errors=gate["errors"],
    )
    db.add(receipt)
    db.commit()
    db.refresh(receipt)
    return receipt
