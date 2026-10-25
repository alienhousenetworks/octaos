"""Persistent execution ledger for tenant-scoped marketing workflows."""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.verticals import MarketingExecution, MarketingExecutionStep


TERMINAL_STATES = {"completed", "failed", "cancelled"}


def _json_safe(value: Any) -> Any:
    """Convert input to JSON-safe values without leaking arbitrary objects."""
    try:
        return json.loads(json.dumps(value, sort_keys=True, default=str))
    except (TypeError, ValueError):
        return {"unserializable": True}


def _request_hash(payload: Dict[str, Any]) -> str:
    raw = json.dumps(_json_safe(payload), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class MarketingExecutionLedger:
    """Idempotent run creation, durable stage transitions, and bounded retries.

    This ledger records state; it is not a distributed queue. Callers must still
    arrange worker execution and use provider-side idempotency where supported.
    """

    def __init__(self, db: Session, tenant_id: str):
        if not tenant_id:
            raise ValueError("tenant_id is required")
        self.db = db
        self.tenant_id = str(tenant_id)

    def start_or_resume(
        self,
        workflow_type: str,
        idempotency_key: str,
        request_payload: Dict[str, Any],
        *,
        max_attempts: int = 3,
    ) -> MarketingExecution:
        if not workflow_type or not idempotency_key:
            raise ValueError("workflow_type and idempotency_key are required")
        if len(idempotency_key) > 200:
            raise ValueError("idempotency_key must be at most 200 characters")
        digest = _request_hash(request_payload)
        query = self.db.query(MarketingExecution).filter_by(
            tenant_id=self.tenant_id,
            workflow_type=workflow_type,
            idempotency_key=idempotency_key,
        )
        existing = query.with_for_update().first()
        if existing:
            if existing.request_hash != digest:
                raise ValueError("idempotency key was already used with a different request")
            if existing.status == "completed":
                return existing
            if existing.status == "running" and existing.attempts >= max_attempts:
                raise RuntimeError("execution reached its retry limit")
            if existing.status in {"failed", "queued", "running"}:
                if existing.attempts >= max_attempts and existing.status != "queued":
                    raise RuntimeError("execution reached its retry limit")
                existing.status = "running"
                existing.attempts = int(existing.attempts or 0) + 1
                existing.error = None
                existing.started_at = datetime.now(timezone.utc)
                existing.finished_at = None
                self.db.commit()
                self.db.refresh(existing)
            return existing

        run = MarketingExecution(
            id=str(uuid.uuid4()),
            tenant_id=self.tenant_id,
            workflow_type=workflow_type,
            idempotency_key=idempotency_key,
            request_hash=digest,
            status="running",
            attempts=1,
            request_payload=_json_safe(request_payload),
            started_at=datetime.now(timezone.utc),
        )
        self.db.add(run)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            # Concurrent first writers race on the unique constraint; reload safely.
            existing = query.first()
            if not existing:
                raise
            if existing.request_hash != digest:
                raise ValueError("idempotency key was already used with a different request")
            return existing
        self.db.refresh(run)
        return run

    def begin_step(
        self, execution_id: str, stage_id: str, input_payload: Optional[Dict[str, Any]] = None
    ) -> MarketingExecutionStep:
        run = self._get_run(execution_id)
        if run.status in TERMINAL_STATES:
            raise ValueError(f"cannot begin a step for terminal execution: {run.status}")
        previous = (
            self.db.query(MarketingExecutionStep)
            .filter_by(tenant_id=self.tenant_id, execution_id=execution_id, stage_id=stage_id)
            .order_by(MarketingExecutionStep.attempt.desc())
            .first()
        )
        attempt = int(previous.attempt if previous else 0) + 1
        step = MarketingExecutionStep(
            id=str(uuid.uuid4()),
            tenant_id=self.tenant_id,
            execution_id=execution_id,
            stage_id=stage_id,
            status="running",
            attempt=attempt,
            input_payload=_json_safe(input_payload or {}),
        )
        run.current_stage = stage_id
        run.status = "running"
        self.db.add(step)
        self.db.commit()
        self.db.refresh(step)
        return step

    def finish_step(
        self,
        execution_id: str,
        stage_id: str,
        *,
        output_payload: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> None:
        run = self._get_run(execution_id)
        step = (
            self.db.query(MarketingExecutionStep)
            .filter_by(tenant_id=self.tenant_id, execution_id=execution_id, stage_id=stage_id, status="running")
            .order_by(MarketingExecutionStep.attempt.desc())
            .first()
        )
        if step:
            step.status = "failed" if error else "completed"
            step.output_payload = _json_safe(output_payload or {})
            step.error = (error or "")[:4000] or None
            step.finished_at = datetime.now(timezone.utc)
        if error:
            run.status = "failed"
            run.error = error[:4000]
        self.db.commit()

    def complete(self, execution_id: str, result_payload: Dict[str, Any]) -> None:
        run = self._get_run(execution_id)
        run.status = "completed"
        run.result_payload = _json_safe(result_payload)
        run.error = None
        run.finished_at = datetime.now(timezone.utc)
        self.db.commit()

    def fail(self, execution_id: str, error: str) -> None:
        run = self._get_run(execution_id)
        run.status = "failed"
        run.error = (error or "Unknown error")[:4000]
        run.finished_at = datetime.now(timezone.utc)
        self.db.commit()

    def get(self, execution_id: str) -> Optional[MarketingExecution]:
        return self.db.query(MarketingExecution).filter_by(
            tenant_id=self.tenant_id, id=execution_id
        ).first()

    def _get_run(self, execution_id: str) -> MarketingExecution:
        run = self.get(execution_id)
        if not run:
            raise LookupError("marketing execution not found for this tenant")
        return run
