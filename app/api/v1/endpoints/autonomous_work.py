"""API for durable autonomous tasks, events, and approval requests."""
import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api import deps
from app.core.rbac import Action, Resource, require_permission
from app.models.base import User
from app.models.autonomous_work import AutonomousApproval, AutonomousTask, AutonomousTaskEvent
from app.models.flow_engine import ExecutionEvent
from app.services.autonomous_runtime import AutonomousRuntime, RuntimePolicyError
from app.services.agent_runtime.protocol import sanitize_public_text
from app.services.agent_runtime.execution_identity import register_execution_identity

router = APIRouter()


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    goal: str = Field(min_length=1, max_length=20000)
    autonomy_level: str = Field(default="supervised")
    risk_level: str = Field(default="standard")
    acceptance_criteria: List[str] = Field(default_factory=list, max_length=30)
    context: Dict[str, Any] = Field(default_factory=dict)
    idempotency_key: Optional[str] = Field(default=None, max_length=160)


class ApprovalDecision(BaseModel):
    decision: str = Field(pattern="^(approve|reject)$")
    note: Optional[str] = Field(default=None, max_length=2000)


def _task_dict(task: AutonomousTask) -> dict:
    return {
        "id": task.id,
        "title": task.title,
        "goal": task.goal,
        "status": task.status,
        "autonomy_level": task.autonomy_level,
        "risk_level": task.risk_level,
        "acceptance_criteria": task.acceptance_criteria or [],
        "context": task.context or {},
        "result": task.result,
        "blocker": task.blocker,
        "error_code": task.error_code,
        "attempt_count": task.attempt_count,
        "max_attempts": task.max_attempts,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "started_at": task.started_at,
        "finished_at": task.finished_at,
    }


def _owned_task(db: Session, task_id: str, user: User) -> AutonomousTask:
    query = db.query(AutonomousTask).filter(
        AutonomousTask.id == task_id,
        AutonomousTask.tenant_id == user.tenant_id,
    )
    task = query.first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    if not (user.is_system_admin or user.role in {"admin", "organization_admin"}):
        if task.created_by_id != user.id:
            raise HTTPException(status_code=403, detail="You can only access tasks you created.")
    return task


@router.post("/tasks", status_code=201)
def create_task(
    request: TaskCreate,
    db: Session = Depends(deps.get_db),
    user: User = Depends(deps.get_current_user),
    _: User = Depends(require_permission(Resource.SETTINGS, Action.EXECUTE)),
):
    runtime = AutonomousRuntime(db)
    try:
        task = runtime.create_task(
            tenant_id=user.tenant_id,
            organization_id=getattr(user, "organization_id", None),
            created_by_id=user.id,
            title=request.title,
            goal=request.goal,
            autonomy_level=request.autonomy_level,
            risk_level=request.risk_level,
            acceptance_criteria=request.acceptance_criteria,
            context=request.context,
            idempotency_key=request.idempotency_key,
        )
    except RuntimePolicyError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    context = dict(task.context or {})
    canonical_id = str(context.get("canonical_execution_id") or task.id)
    register_execution_identity(
        db, tenant_id=user.tenant_id, source_kind="autonomous_task",
        source_id=task.id, canonical_execution_id=canonical_id,
        metadata={"created_by_id": user.id, "task_title": task.title},
    )
    if context.get("canonical_execution_id") != canonical_id:
        context["canonical_execution_id"] = canonical_id
        task.context = context
        db.commit()
        db.refresh(task)
    return _task_dict(task)


@router.post("/tasks/{task_id}/run", status_code=202)
def run_task(
    task_id: str,
    db: Session = Depends(deps.get_db),
    user: User = Depends(deps.get_current_user),
):
    task = _owned_task(db, task_id, user)
    if task.status not in {"queued", "blocked", "failed"}:
        raise HTTPException(status_code=409, detail=f"Task cannot be run from status '{task.status}'.")
    if task.status in {"blocked", "failed"}:
        # Requeue only recoverable states and preserve the transition in the event ledger.
        runtime = AutonomousRuntime(db)
        try:
            runtime.transition(task, "queued", "Task manually requeued by an authorized user.",
                               payload={"actor_id": user.id})
        except RuntimePolicyError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        task.blocker = None
        task.error_code = None
        task.finished_at = None
        db.commit()
    try:
        from app.services.autonomous_runtime.worker import execute_autonomous_task
        job = execute_autonomous_task.delay(task.id, user.tenant_id)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail="Task was saved, but the worker queue is unavailable. Start Redis/Celery and retry.",
        ) from exc
    runtime = AutonomousRuntime(db)
    runtime.emit(task, "task_dispatched", "Task dispatched to the autonomous-work worker.",
                 actor_type="user", actor_id=user.id, payload={"job_id": job.id})
    db.commit()
    return {"task_id": task.id, "status": task.status, "job_id": job.id, "message": "Task queued; completion is not yet verified."}


@router.get("/tasks")
def list_tasks(
    status: Optional[str] = Query(default=None, max_length=32),
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(deps.get_db),
    user: User = Depends(deps.get_current_user),
):
    query = db.query(AutonomousTask).filter(AutonomousTask.tenant_id == user.tenant_id)
    if not (user.is_system_admin or user.role in {"admin", "organization_admin"}):
        query = query.filter(AutonomousTask.created_by_id == user.id)
    if status:
        query = query.filter(AutonomousTask.status == status)
    tasks = query.order_by(AutonomousTask.created_at.desc()).offset(offset).limit(limit).all()
    return {"items": [_task_dict(task) for task in tasks], "limit": limit, "offset": offset}


@router.get("/tasks/{task_id}")
def get_task(
    task_id: str,
    db: Session = Depends(deps.get_db),
    user: User = Depends(deps.get_current_user),
):
    return _task_dict(_owned_task(db, task_id, user))


@router.get("/tasks/{task_id}/events")
def list_task_events(
    task_id: str,
    db: Session = Depends(deps.get_db),
    user: User = Depends(deps.get_current_user),
):
    task = _owned_task(db, task_id, user)
    events = db.query(AutonomousTaskEvent).filter(
        AutonomousTaskEvent.task_id == task.id,
        AutonomousTaskEvent.tenant_id == user.tenant_id,
    ).order_by(AutonomousTaskEvent.created_at.asc()).all()
    return {"items": [{
        "id": event.id,
        "event_type": event.event_type,
        "message": event.message,
        "actor_type": event.actor_type,
        "payload": event.payload or {},
        "created_at": event.created_at,
    } for event in events]}


_SENSITIVE_EVENT_KEYS = {"api_key", "access_token", "refresh_token", "password", "secret", "client_secret", "authorization", "cookie", "private_key", "system_prompt", "chain_of_thought", "private_reasoning"}


def _public_event_value(value: Any, depth: int = 0) -> Any:
    """Bound and redact persisted event payloads before exposing them to the browser."""
    if depth > 5:
        return "[TRUNCATED]"
    if isinstance(value, dict):
        return {str(key): _public_event_value(child, depth + 1)
                for key, child in list(value.items())[:100]
                if str(key).lower().replace("-", "_") not in _SENSITIVE_EVENT_KEYS}
    if isinstance(value, (list, tuple)):
        return [_public_event_value(item, depth + 1) for item in value[:100]]
    if isinstance(value, str):
        return sanitize_public_text(value, 1000)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return sanitize_public_text(str(value), 500)


@router.get("/agent-runs/{run_id}/events/stream")
async def stream_agent_run_events(
    run_id: str,
    request: Request,
    timeout_seconds: int = Query(default=30, ge=1, le=60),
    db: Session = Depends(deps.get_db),
    user: User = Depends(deps.get_current_user),
):
    """Stream normalized agent-runtime events scoped to the authenticated tenant."""
    if not run_id or len(run_id) > 200:
        raise HTTPException(status_code=400, detail="Invalid run ID.")

    async def event_generator():
        seen: set[str] = set()
        deadline = asyncio.get_running_loop().time() + timeout_seconds
        terminal_types = {"run.completed", "run.failed", "run.cancelled", "approval.required"}
        while asyncio.get_running_loop().time() < deadline:
            if await request.is_disconnected():
                break
            events = db.query(ExecutionEvent).filter(
                ExecutionEvent.tenant_id == user.tenant_id,
                ExecutionEvent.flow_run_id == run_id,
            ).order_by(ExecutionEvent.created_at.asc()).limit(500).all()
            terminal_seen = False
            for event in events:
                if event.id in seen:
                    continue
                seen.add(event.id)
                payload = _public_event_value(event.payload or {})
                event_type = str(event.event_type)
                message = {
                    "id": event.id,
                    "run_id": run_id,
                    "event_type": event_type,
                    "payload": payload,
                    "created_at": event.created_at.isoformat() if event.created_at else None,
                }
                yield f"id: {event.id}\\nevent: agent.event\\ndata: {json.dumps(message, separators=(',', ':'))}\\n\\n"
                if event_type in terminal_types:
                    terminal_seen = True
            if terminal_seen:
                break
            yield ": keep-alive\\n\\n"
            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no",
    })


@router.get("/tasks/{task_id}/events/stream")
async def stream_task_events(
    task_id: str,
    request: Request,
    timeout_seconds: int = Query(default=30, ge=1, le=60),
    db: Session = Depends(deps.get_db),
    user: User = Depends(deps.get_current_user),
):
    """Replay persisted task events and stream new sanitized events over SSE."""
    _owned_task(db, task_id, user)

    async def event_generator():
        seen: set[str] = set()
        deadline = asyncio.get_running_loop().time() + timeout_seconds
        while asyncio.get_running_loop().time() < deadline:
            if await request.is_disconnected():
                break
            current = _owned_task(db, task_id, user)
            events = db.query(AutonomousTaskEvent).filter(
                AutonomousTaskEvent.task_id == current.id,
                AutonomousTaskEvent.tenant_id == user.tenant_id,
            ).order_by(AutonomousTaskEvent.created_at.asc()).limit(500).all()
            for event in events:
                if event.id in seen:
                    continue
                seen.add(event.id)
                message = {
                    "id": event.id,
                    "task_id": current.id,
                    "event_type": event.event_type,
                    "message": sanitize_public_text(event.message, 1500),
                    "actor_type": event.actor_type,
                    "payload": _public_event_value(event.payload or {}),
                    "created_at": event.created_at.isoformat() if event.created_at else None,
                }
                yield f"id: {event.id}\nevent: task.event\ndata: {json.dumps(message, separators=(',', ':'))}\n\n"
            if current.status in {"completed", "failed", "cancelled"} and events:
                break
            yield ": keep-alive\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no",
    })


@router.post("/tasks/{task_id}/cancel")
def cancel_task(
    task_id: str,
    db: Session = Depends(deps.get_db),
    user: User = Depends(deps.get_current_user),
):
    task = _owned_task(db, task_id, user)
    try:
        task = AutonomousRuntime(db).cancel(task, user.id)
    except RuntimePolicyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _task_dict(task)


@router.post("/tasks/{task_id}/approvals/{approval_id}/decision")
def decide_approval(
    task_id: str,
    approval_id: str,
    request: ApprovalDecision,
    db: Session = Depends(deps.get_db),
    user: User = Depends(deps.get_current_user),
    _: User = Depends(require_permission(Resource.SETTINGS, Action.EXECUTE)),
):
    task = _owned_task(db, task_id, user)
    approval = db.query(AutonomousApproval).filter(
        AutonomousApproval.id == approval_id,
        AutonomousApproval.task_id == task.id,
        AutonomousApproval.tenant_id == user.tenant_id,
        AutonomousApproval.status == "pending",
    ).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Pending approval not found.")
    approval.status = "approved" if request.decision == "approve" else "rejected"
    approval.decided_by_id = user.id
    approval.decision_note = request.note
    approval.decided_at = datetime.now(timezone.utc)
    runtime = AutonomousRuntime(db)
    runtime.emit(task, "approval_decided", f"Approval {approval.status}.",
                 actor_type="user", actor_id=user.id,
                 payload={"approval_id": approval.id, "decision": approval.status})
    db.commit()
    return {"approval_id": approval.id, "status": approval.status, "task_id": task.id}
