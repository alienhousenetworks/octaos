"""Transactional run ledger for the complete Sales AI lifecycle.

This is orchestration infrastructure, not a claim that every legacy workflow is
already routed through it. Every read/write is tenant-scoped and state changes
are constrained so retries cannot silently re-run a completed side effect.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.exc import IntegrityError

from app.models.sales_workflow import SalesWorkflowRun, SalesWorkflowStep

RUN_STATES = {"queued", "running", "waiting_approval", "waiting_reply", "completed", "blocked", "failed", "cancelled"}
STEP_STATES = {"queued", "running", "waiting_approval", "succeeded", "blocked", "failed", "skipped"}
RUN_TRANSITIONS = {
    "queued": {"running", "cancelled", "blocked"},
    "running": {"waiting_approval", "waiting_reply", "completed", "blocked", "failed", "cancelled"},
    "waiting_approval": {"running", "blocked", "cancelled"},
    "waiting_reply": {"running", "completed", "blocked", "cancelled"},
    "blocked": {"queued", "cancelled"},
    "failed": {"queued", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}
STEP_TRANSITIONS = {
    "queued": {"running", "blocked", "skipped"},
    "running": {"succeeded", "blocked", "failed", "waiting_approval"},
    "waiting_approval": {"running", "blocked", "skipped"},
    "failed": {"queued", "running"},
    "blocked": {"queued", "running"},
    "succeeded": set(),
    "skipped": set(),
}
STAGES = (
    "discovery", "source_verification", "account_enrichment", "contact_verification",
    "qualification", "personalization", "approval", "delivery", "reply_handling",
    "meeting_confirmation", "crm_reconciliation",
)


class WorkflowConflict(ValueError):
    """Raised for an invalid transition or tenant/idempotency conflict."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_or_get_run(
    db,
    *,
    tenant_id: str,
    campaign_id: str,
    idempotency_key: str,
    input_payload: dict[str, Any],
) -> SalesWorkflowRun:
    if not tenant_id or not campaign_id or not idempotency_key:
        raise ValueError("tenant_id, campaign_id and idempotency_key are required")
    existing = db.query(SalesWorkflowRun).filter_by(
        tenant_id=tenant_id, idempotency_key=idempotency_key
    ).first()
    if existing:
        return existing
    row = SalesWorkflowRun(
        tenant_id=tenant_id, campaign_id=campaign_id,
        idempotency_key=idempotency_key, status="queued",
        current_stage="discovery", input_payload=input_payload,
    )
    db.add(row)
    try:
        db.commit()
        db.refresh(row)
        return row
    except IntegrityError:
        db.rollback()
        # Another worker may have won the unique-key race.
        existing = db.query(SalesWorkflowRun).filter_by(
            tenant_id=tenant_id, idempotency_key=idempotency_key
        ).first()
        if existing:
            return existing
        raise


def get_run(db, *, tenant_id: str, run_id: str) -> SalesWorkflowRun | None:
    return db.query(SalesWorkflowRun).filter_by(tenant_id=tenant_id, id=run_id).first()


def transition_run(
    db, *, tenant_id: str, run_id: str, status: str,
    current_stage: str | None = None, result_payload: dict | None = None,
    failure_code: str | None = None, failure_detail: str | None = None,
) -> SalesWorkflowRun:
    if status not in RUN_STATES:
        raise ValueError(f"Unknown run status: {status}")
    row = get_run(db, tenant_id=tenant_id, run_id=run_id)
    if row is None:
        raise KeyError("Sales workflow run not found for this tenant")
    if status != row.status and status not in RUN_TRANSITIONS.get(row.status, set()):
        raise WorkflowConflict(f"Invalid run transition: {row.status} -> {status}")
    row.status = status
    if current_stage:
        if current_stage not in STAGES:
            raise ValueError(f"Unknown sales workflow stage: {current_stage}")
        row.current_stage = current_stage
    if result_payload is not None:
        row.result_payload = result_payload
    row.failure_code = failure_code
    row.failure_detail = failure_detail
    if status in {"completed", "failed", "cancelled"}:
        row.completed_at = _now()
    elif status in {"queued", "running", "waiting_approval", "waiting_reply"}:
        row.completed_at = None
    db.commit()
    db.refresh(row)
    return row


def record_step(
    db, *, tenant_id: str, run_id: str, step_key: str, stage: str,
    idempotency_key: str, input_payload: dict | None = None,
) -> SalesWorkflowStep:
    if stage not in STAGES:
        raise ValueError(f"Unknown sales workflow stage: {stage}")
    run = get_run(db, tenant_id=tenant_id, run_id=run_id)
    if run is None:
        raise KeyError("Sales workflow run not found for this tenant")
    existing = db.query(SalesWorkflowStep).filter_by(
        tenant_id=tenant_id, run_id=run_id, step_key=step_key
    ).first()
    if existing:
        if existing.idempotency_key != idempotency_key:
            raise WorkflowConflict("Step key already exists with a different idempotency key")
        return existing
    row = SalesWorkflowStep(
        tenant_id=tenant_id, run_id=run_id, step_key=step_key, stage=stage,
        idempotency_key=idempotency_key, input_payload=input_payload or {},
    )
    db.add(row)
    try:
        db.commit()
        db.refresh(row)
        return row
    except IntegrityError:
        db.rollback()
        existing = db.query(SalesWorkflowStep).filter_by(
            tenant_id=tenant_id, run_id=run_id, step_key=step_key
        ).first()
        if existing and existing.idempotency_key == idempotency_key:
            return existing
        raise


def transition_step(
    db, *, tenant_id: str, run_id: str, step_key: str, status: str,
    result_payload: dict | None = None, error_code: str | None = None,
    error_detail: str | None = None,
) -> SalesWorkflowStep:
    if status not in STEP_STATES:
        raise ValueError(f"Unknown step status: {status}")
    row = db.query(SalesWorkflowStep).filter_by(
        tenant_id=tenant_id, run_id=run_id, step_key=step_key
    ).first()
    if row is None:
        raise KeyError("Sales workflow step not found for this tenant/run")
    if status != row.status and status not in STEP_TRANSITIONS.get(row.status, set()):
        raise WorkflowConflict(f"Invalid step transition: {row.status} -> {status}")
    now = _now()
    if status == "running":
        row.started_at = row.started_at or now
        try:
            row.attempt = str(int(row.attempt or "0") + 1)
        except (TypeError, ValueError):
            row.attempt = "1"
    if status in {"succeeded", "blocked", "failed", "skipped"}:
        row.finished_at = now
    elif status in {"queued", "running", "waiting_approval"}:
        row.finished_at = None
    row.status = status
    row.result_payload = result_payload if result_payload is not None else row.result_payload
    row.error_code = error_code
    row.error_detail = error_detail
    db.commit()
    db.refresh(row)
    return row
