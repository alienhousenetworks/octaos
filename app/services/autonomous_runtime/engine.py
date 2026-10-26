"""Lifecycle primitives for durable autonomous work.

The runtime never reports success merely because a model generated a response.
Execution adapters must be registered by the application and return verifiable
evidence. If no adapter exists, a task is explicitly blocked.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.autonomous_work import AutonomousTask, AutonomousTaskEvent


class RuntimePolicyError(Exception):
    """Raised when an operation violates runtime policy."""


TERMINAL_STATES = {"succeeded", "failed", "cancelled"}
ALLOWED_TRANSITIONS = {
    "queued": {"planning", "cancelled", "blocked"},
    "planning": {"running", "awaiting_approval", "blocked", "failed", "cancelled"},
    "running": {"verifying", "awaiting_approval", "blocked", "failed", "cancelled"},
    "verifying": {"succeeded", "running", "blocked", "failed", "cancelled"},
    "awaiting_approval": {"queued", "cancelled", "blocked"},
    "blocked": {"queued", "cancelled"},
    "failed": {"queued"},
    "succeeded": set(),
    "cancelled": set(),
}


class AutonomousRuntime:
    """Tenant-scoped task lifecycle and evidence ledger.

    Tool execution is deliberately injected: business modules can register a handler
    without bypassing the common policy, state, and audit boundary.
    """

    def __init__(self, db: Session):
        self.db = db
        self._handlers: Dict[str, Callable[..., Dict[str, Any]]] = {}

    def register_handler(self, task_type: str, handler: Callable[..., Dict[str, Any]]) -> None:
        if not task_type or not callable(handler):
            raise ValueError("A task type and callable handler are required.")
        self._handlers[task_type] = handler

    def emit(
        self,
        task: AutonomousTask,
        event_type: str,
        message: str,
        *,
        actor_type: str = "system",
        actor_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> AutonomousTaskEvent:
        event = AutonomousTaskEvent(
            task_id=task.id,
            tenant_id=task.tenant_id,
            actor_type=actor_type,
            actor_id=actor_id,
            event_type=event_type,
            message=message,
            payload=payload or {},
        )
        self.db.add(event)
        return event

    def transition(
        self,
        task: AutonomousTask,
        new_status: str,
        message: str,
        *,
        payload: Optional[Dict[str, Any]] = None,
    ) -> AutonomousTask:
        old_status = task.status
        if new_status not in ALLOWED_TRANSITIONS.get(old_status, set()):
            raise RuntimePolicyError(f"Invalid task transition: {old_status} -> {new_status}")
        task.status = new_status
        task.updated_at = datetime.now(timezone.utc)
        if new_status == "running" and task.started_at is None:
            task.started_at = datetime.now(timezone.utc)
        if new_status in TERMINAL_STATES:
            task.finished_at = datetime.now(timezone.utc)
        self.emit(task, "state_transition", message, payload={
            "from": old_status, "to": new_status, **(payload or {})
        })
        self.db.flush()
        return task

    def create_task(
        self,
        *,
        tenant_id: str,
        created_by_id: str,
        title: str,
        goal: str,
        organization_id: Optional[str] = None,
        autonomy_level: str = "supervised",
        risk_level: str = "standard",
        acceptance_criteria: Optional[list] = None,
        context: Optional[dict] = None,
        idempotency_key: Optional[str] = None,
    ) -> AutonomousTask:
        if autonomy_level not in {"supervised", "bounded", "approval_required"}:
            raise RuntimePolicyError("Unsupported autonomy level.")
        if risk_level not in {"low", "standard", "high", "critical"}:
            raise RuntimePolicyError("Unsupported risk level.")
        if not title.strip() or not goal.strip():
            raise RuntimePolicyError("Task title and goal are required.")
        if len(goal) > 20000:
            raise RuntimePolicyError("Task goal exceeds the 20,000 character limit.")
        if idempotency_key:
            existing = self.db.query(AutonomousTask).filter(
                AutonomousTask.tenant_id == tenant_id,
                AutonomousTask.idempotency_key == idempotency_key,
            ).first()
            if existing:
                return existing
        task = AutonomousTask(
            tenant_id=tenant_id,
            organization_id=organization_id,
            created_by_id=created_by_id,
            title=title.strip(),
            goal=goal.strip(),
            status="queued",
            autonomy_level=autonomy_level,
            risk_level=risk_level,
            acceptance_criteria=acceptance_criteria or [],
            context=context or {},
            idempotency_key=idempotency_key,
        )
        self.db.add(task)
        try:
            self.db.flush()
        except IntegrityError:
            # Concurrent requests can both pass the initial lookup. The unique
            # (tenant_id, idempotency_key) index is the final arbiter; on conflict,
            # roll back this transaction and return the already-persisted task.
            self.db.rollback()
            if idempotency_key:
                existing = self.db.query(AutonomousTask).filter(
                    AutonomousTask.tenant_id == tenant_id,
                    AutonomousTask.idempotency_key == idempotency_key,
                ).first()
                if existing:
                    return existing
            raise
        self.emit(task, "task_created", "Task accepted and persisted; execution has not yet been verified.",
                  actor_type="user", actor_id=created_by_id,
                  payload={"autonomy_level": autonomy_level, "risk_level": risk_level})
        self.db.commit()
        self.db.refresh(task)
        return task

    def cancel(self, task: AutonomousTask, actor_id: str) -> AutonomousTask:
        if task.status in TERMINAL_STATES:
            return task
        self.transition(task, "cancelled", "Task cancelled by an authorized user.",
                        payload={"actor_id": actor_id})
        self.db.commit()
        self.db.refresh(task)
        return task

    def execute_registered_handler(self, task: AutonomousTask) -> AutonomousTask:
        """Run only an explicitly registered handler; never silently fake execution."""
        if task.status != "queued":
            return task
        task.attempt_count += 1
        self.transition(task, "planning", "Runtime started task planning.")
        self.db.commit()

        task_type = (task.context or {}).get("task_type", "general")
        handler = self._handlers.get(task_type)
        if handler is None:
            task.blocker = (
                f"No execution adapter is registered for task type '{task_type}'. "
                "The goal is saved, but no external action has been performed."
            )
            task.error_code = "EXECUTOR_NOT_CONFIGURED"
            self.transition(task, "blocked", task.blocker, payload={"task_type": task_type})
            self.db.commit()
            self.db.refresh(task)
            return task

        try:
            self.transition(task, "running", "Registered execution adapter started.")
            self.db.commit()
            outcome = handler(task=task, db=self.db)
            if not isinstance(outcome, dict):
                raise TypeError("Execution adapters must return a dictionary with evidence.")
            self.transition(task, "verifying", "Execution adapter returned an outcome; verification is required.")
            evidence = outcome.get("evidence") or []
            verified = outcome.get("verified") is True and bool(evidence)
            if not verified:
                task.blocker = "Adapter returned no sufficient verification evidence."
                task.result = {"output": outcome.get("output"), "evidence": evidence}
                self.transition(task, "blocked", task.blocker)
            else:
                task.result = {
                    "output": outcome.get("output"),
                    "evidence": evidence,
                    "verification": outcome.get("verification"),
                    "evidence_digest": hashlib.sha256(
                        json.dumps(evidence, sort_keys=True, default=str).encode("utf-8")
                    ).hexdigest(),
                }
                task.blocker = None
                task.error_code = None
                self.transition(task, "succeeded", "Task outcome verified by its registered adapter.")
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            task = self.db.query(AutonomousTask).filter(
                AutonomousTask.id == task.id, AutonomousTask.tenant_id == task.tenant_id
            ).first()
            if task and task.status not in TERMINAL_STATES:
                task.error_code = "EXECUTOR_FAILED"
                task.blocker = f"Execution failed: {type(exc).__name__}"
                try:
                    self.transition(task, "failed", task.blocker)
                    self.db.commit()
                except Exception:
                    self.db.rollback()
            if task is None:
                raise
        self.db.refresh(task)
        return task
