"""Tenant-scoped durable workflow checkpoints and persistent DLQ helpers."""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.enterprise import DeadLetterJob, WorkflowCheckpoint

logger = logging.getLogger(__name__)

_ALLOWED_TRANSITIONS = {
    "running": {"running", "waiting", "completed", "failed"},
    "waiting": {"waiting", "running", "failed"},
    # Failed workflows may be explicitly resumed by checkpointing them to running.
    "failed": {"failed", "running"},
    "completed": {"completed"},
}


def _scoped_idempotency_key(tenant_id: str, key: str) -> str:
    """Return a stable, tenant-namespaced storage key without storing caller input."""
    digest = hashlib.sha256(f"{tenant_id}:{key}".encode("utf-8")).hexdigest()
    return f"v1:{digest}"


class DurableWorkflowService:
    def __init__(self, db: Session, tenant_id: str):
        if not tenant_id:
            raise ValueError("tenant_id is required")
        self.db = db
        self.tenant_id = tenant_id

    def start_run(
        self,
        workflow_name: str,
        run_id: str,
        *,
        initial_state: Optional[dict] = None,
        idempotency_key: Optional[str] = None,
    ) -> WorkflowCheckpoint:
        if idempotency_key:
            # First support legacy rows, but only within the authenticated tenant.
            existing = (
                self.db.query(WorkflowCheckpoint)
                .filter(
                    WorkflowCheckpoint.tenant_id == self.tenant_id,
                    WorkflowCheckpoint.idempotency_key == idempotency_key,
                )
                .first()
            )
            if existing:
                return existing

            scoped_key = _scoped_idempotency_key(self.tenant_id, idempotency_key)
            existing = (
                self.db.query(WorkflowCheckpoint)
                .filter(
                    WorkflowCheckpoint.tenant_id == self.tenant_id,
                    WorkflowCheckpoint.idempotency_key == scoped_key,
                )
                .first()
            )
            if existing:
                return existing
        else:
            scoped_key = None

        cp = WorkflowCheckpoint(
            tenant_id=self.tenant_id,
            workflow_name=workflow_name,
            run_id=run_id,
            step_index=0,
            step_name="start",
            state=initial_state or {},
            status="running",
            idempotency_key=scoped_key,
        )
        self.db.add(cp)
        self.db.commit()
        self.db.refresh(cp)
        return cp

    def checkpoint(
        self,
        run_id: str,
        *,
        step_index: int,
        step_name: str,
        state: dict,
        status: str = "running",
    ) -> WorkflowCheckpoint:
        if status not in _ALLOWED_TRANSITIONS:
            raise ValueError(f"Unsupported workflow status: {status}")
        cp = (
            self.db.query(WorkflowCheckpoint)
            .filter(
                WorkflowCheckpoint.tenant_id == self.tenant_id,
                WorkflowCheckpoint.run_id == run_id,
            )
            .order_by(WorkflowCheckpoint.created_at.desc())
            .first()
        )
        if not cp:
            raise ValueError("Run not found")
        if status not in _ALLOWED_TRANSITIONS.get(cp.status or "running", set()):
            raise ValueError(f"Invalid workflow status transition: {cp.status} -> {status}")
        if step_index < (cp.step_index or 0):
            raise ValueError("Checkpoint step_index cannot move backwards")
        cp.step_index = step_index
        cp.step_name = step_name
        cp.state = state
        cp.status = status
        self.db.commit()
        self.db.refresh(cp)
        return cp

    def get_run(self, run_id: str) -> Optional[WorkflowCheckpoint]:
        return (
            self.db.query(WorkflowCheckpoint)
            .filter(
                WorkflowCheckpoint.tenant_id == self.tenant_id,
                WorkflowCheckpoint.run_id == run_id,
            )
            .order_by(WorkflowCheckpoint.created_at.desc())
            .first()
        )


class DeadLetterService:
    def __init__(self, db: Session):
        self.db = db

    def record(
        self,
        *,
        task_name: str,
        task_id: Optional[str] = None,
        args: Optional[list] = None,
        kwargs: Optional[dict] = None,
        error: Optional[str] = None,
        traceback: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> DeadLetterJob:
        job = DeadLetterJob(
            tenant_id=tenant_id,
            task_name=task_name,
            task_id=task_id,
            args=args or [],
            kwargs=kwargs or {},
            error_message=error,
            traceback=traceback,
            status="failed",
            attempts=1,
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        logger.error("DLQ recorded: %s %s — %s", task_name, task_id, error)
        return job

    def list_jobs(
        self,
        *,
        tenant_id: Optional[str] = None,
        status: str = "failed",
        limit: int = 50,
    ) -> List[DeadLetterJob]:
        q = self.db.query(DeadLetterJob).filter(DeadLetterJob.status == status)
        if tenant_id:
            q = q.filter(DeadLetterJob.tenant_id == tenant_id)
        return q.order_by(DeadLetterJob.created_at.desc()).limit(max(1, min(limit, 200))).all()

    def replay(self, job_id: str, *, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        q = self.db.query(DeadLetterJob).filter(DeadLetterJob.id == job_id)
        if tenant_id:
            q = q.filter(DeadLetterJob.tenant_id == tenant_id)
        job = q.first()
        if not job:
            raise ValueError("DLQ job not found")
        if job.status not in {"failed", "replaying"}:
            raise ValueError(f"DLQ job cannot be replayed from status: {job.status}")
        job.status = "replaying"
        job.attempts = (job.attempts or 0) + 1
        self.db.commit()

        try:
            from app.core.celery_app import celery_app

            result = celery_app.send_task(job.task_name, args=job.args or [], kwargs=job.kwargs or {})
            # Queue acceptance is not task completion. Keep the record replaying
            # until a worker/reconciler can confirm the actual outcome.
            self.db.commit()
            return {
                "status": "submitted",
                "job_id": job_id,
                "task_name": job.task_name,
                "dispatch_id": getattr(result, "id", None),
            }
        except Exception as e:
            job.status = "failed"
            job.error_message = f"Replay dispatch failed: {e}"
            self.db.commit()
            logger.exception("DLQ replay dispatch failed for job %s", job_id)
            return {"status": "error", "job_id": job_id, "error": "Replay dispatch failed"}

    def discard(self, job_id: str, *, tenant_id: Optional[str] = None) -> DeadLetterJob:
        q = self.db.query(DeadLetterJob).filter(DeadLetterJob.id == job_id)
        if tenant_id:
            q = q.filter(DeadLetterJob.tenant_id == tenant_id)
        job = q.first()
        if not job:
            raise ValueError("DLQ job not found")
        if job.status not in {"failed", "replaying"}:
            raise ValueError(f"DLQ job cannot be discarded from status: {job.status}")
        job.status = "discarded"
        job.resolved_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(job)
        return job
