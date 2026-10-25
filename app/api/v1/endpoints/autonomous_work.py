"""API for durable autonomous tasks, events, and approval requests."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api import deps
from app.core.rbac import Action, Resource, require_permission
from app.models.base import User
from app.models.autonomous_work import AutonomousApproval, AutonomousTask, AutonomousTaskEvent
from app.services.autonomous_runtime import AutonomousRuntime, RuntimePolicyError

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
