"""Governed HR self-service, lifecycle, performance and compensation APIs."""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api import deps
from app.models.base import User
from app.models.hr_core import (
    EmployeeProfile, HRServiceRequest, HRPerformanceReview,
    HRCompensationChange, HRLifecycleTask, HRLifecycleCase,
)
from app.services.rbac_service import user_has_perm

router = APIRouter()
_ADMIN_ROLES = {"admin", "organization_admin", "super_admin"}


def _require_permission(db: Session, user: User, codename: str) -> None:
    if getattr(user, "is_system_admin", False) or getattr(user, "is_superuser", False) or (getattr(user, "role", "") or "").lower() in _ADMIN_ROLES:
        return
    if not user_has_perm(db, user, codename):
        raise HTTPException(status_code=403, detail=f"Missing required permission: {codename}")


def _employee_or_404(db: Session, tenant_id: str, employee_id: str) -> EmployeeProfile:
    employee = db.query(EmployeeProfile).filter_by(id=employee_id, tenant_id=tenant_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found.")
    return employee


def _self_or_permission(db: Session, user: User, employee: EmployeeProfile, codename: str) -> None:
    if employee.user_id and str(employee.user_id) == str(user.id):
        return
    _require_permission(db, user, codename)


class ServiceRequestCreate(BaseModel):
    employee_id: str
    category: str = Field(min_length=2, max_length=60)
    subject: str = Field(min_length=3, max_length=180)
    description: str = Field(min_length=3, max_length=10000)
    priority: str = "medium"


class ServiceRequestUpdate(BaseModel):
    status: str
    assigned_to_id: Optional[str] = None
    resolution_draft: Optional[str] = None


class ReviewCreate(BaseModel):
    employee_id: str
    cycle: str = Field(min_length=2, max_length=80)
    goals: List[dict] = Field(default_factory=list)


class ReviewUpdate(BaseModel):
    status: Optional[str] = None
    goals: Optional[List[dict]] = None
    strengths: Optional[str] = None
    development_areas: Optional[str] = None
    employee_comments: Optional[str] = None


class CompensationProposalCreate(BaseModel):
    employee_id: str
    currency: str = Field(min_length=3, max_length=3)
    current_amount: Optional[Decimal] = None
    proposed_amount: Decimal = Field(gt=0)
    reason: str = Field(min_length=10, max_length=4000)


class CompensationDecision(BaseModel):
    decision: str
    reason: str = Field(min_length=5, max_length=2000)


class LifecycleStart(BaseModel):
    employee_id: str
    lifecycle: str
    due_at: Optional[datetime] = None


class LifecycleTaskUpdate(BaseModel):
    status: str
    verification_note: Optional[str] = None


class LifecycleFinalize(BaseModel):
    reason: Optional[str] = None


@router.post("/service-requests")
def create_service_request(
    payload: ServiceRequestCreate,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
):
    employee = _employee_or_404(db, tenant_id, payload.employee_id)
    _self_or_permission(db, current_user, employee, "hr.view_employees")
    priority = payload.priority.strip().lower()
    if priority not in {"low", "medium", "high", "urgent"}:
        raise HTTPException(status_code=422, detail="Invalid priority.")
    ticket = HRServiceRequest(
        tenant_id=tenant_id,
        ticket_number=f"HR-{uuid.uuid4().hex[:10].upper()}",
        employee_id=employee.id,
        category=payload.category.strip().lower(),
        subject=payload.subject.strip(),
        description=payload.description.strip(),
        priority=priority,
        status="open",
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return {"id": ticket.id, "ticket_number": ticket.ticket_number, "status": ticket.status}


@router.get("/service-requests")
def list_service_requests(
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
):
    q = db.query(HRServiceRequest).filter(HRServiceRequest.tenant_id == tenant_id)
    if not (getattr(current_user, "is_system_admin", False) or getattr(current_user, "is_superuser", False) or (getattr(current_user, "role", "") or "").lower() in _ADMIN_ROLES):
        # A regular employee can only see their own tickets; HR needs explicit manage permission.
        if user_has_perm(db, current_user, "hr.manage_service_requests") or user_has_perm(db, current_user, "hr.manage_employees"):
            pass
        else:
            own = db.query(EmployeeProfile.id).filter_by(tenant_id=tenant_id, user_id=current_user.id).subquery()
            q = q.filter(HRServiceRequest.employee_id.in_(own))
    if status:
        q = q.filter(HRServiceRequest.status == status.strip().lower())
    rows = q.order_by(HRServiceRequest.created_at.desc()).offset(skip).limit(limit).all()
    return [{
        "id": row.id, "ticket_number": row.ticket_number, "employee_id": row.employee_id,
        "category": row.category, "subject": row.subject, "description": row.description,
        "priority": row.priority, "status": row.status, "assigned_to_id": row.assigned_to_id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    } for row in rows]


@router.patch("/service-requests/{request_id}")
def update_service_request(
    request_id: str,
    payload: ServiceRequestUpdate,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
):
    _require_permission(db, current_user, "hr.manage_service_requests")
    row = db.query(HRServiceRequest).filter_by(id=request_id, tenant_id=tenant_id).with_for_update().first()
    if not row:
        raise HTTPException(status_code=404, detail="HR service request not found.")
    allowed = {"open", "in_progress", "awaiting_employee", "resolved", "closed"}
    if payload.status not in allowed:
        raise HTTPException(status_code=422, detail="Invalid service-request status.")
    if row.status == "closed" and payload.status != "closed":
        raise HTTPException(status_code=409, detail="Resolved/closed tickets require a reopen workflow.")
    row.status = payload.status
    if payload.assigned_to_id is not None:
        assignee = db.query(User).filter_by(id=payload.assigned_to_id, tenant_id=tenant_id).first()
        if not assignee:
            raise HTTPException(status_code=422, detail="Assignee must be an existing user in this organization.")
        row.assigned_to_id = assignee.id
    if payload.resolution_draft is not None:
        row.ai_resolution_draft = payload.resolution_draft
    if payload.status == "resolved":
        row.resolved_at = datetime.now(timezone.utc)
    db.commit()
    return {"id": row.id, "status": row.status}


@router.post("/performance-reviews")
def create_performance_review(
    payload: ReviewCreate,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
):
    _require_permission(db, current_user, "hr.manage_performance")
    employee = _employee_or_404(db, tenant_id, payload.employee_id)
    review = HRPerformanceReview(
        tenant_id=tenant_id, employee_id=employee.id, reviewer_user_id=current_user.id,
        cycle=payload.cycle.strip(), goals=payload.goals, status="draft",
    )
    db.add(review)
    try:
        db.commit()
        db.refresh(review)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A review for this employee, reviewer and cycle already exists.")
    return {"id": review.id, "employee_id": review.employee_id, "cycle": review.cycle, "status": review.status}


@router.get("/performance-reviews")
def list_performance_reviews(
    employee_id: Optional[str] = None,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
):
    q = db.query(HRPerformanceReview).filter_by(tenant_id=tenant_id)
    if employee_id:
        employee = _employee_or_404(db, tenant_id, employee_id)
        _self_or_permission(db, current_user, employee, "hr.view_employees")
        q = q.filter(HRPerformanceReview.employee_id == employee.id)
    elif not user_has_perm(db, current_user, "hr.view_employees") and not getattr(current_user, "is_system_admin", False) and not getattr(current_user, "is_superuser", False) and (getattr(current_user, "role", "") or "").lower() not in _ADMIN_ROLES:
        own = db.query(EmployeeProfile.id).filter_by(tenant_id=tenant_id, user_id=current_user.id).subquery()
        q = q.filter(HRPerformanceReview.employee_id.in_(own))
    rows = q.order_by(HRPerformanceReview.created_at.desc()).all()
    return [{
        "id": r.id, "employee_id": r.employee_id, "reviewer_user_id": r.reviewer_user_id,
        "cycle": r.cycle, "status": r.status, "goals": r.goals,
        "strengths": r.strengths, "development_areas": r.development_areas,
        "employee_comments": r.employee_comments,
    } for r in rows]


@router.patch("/performance-reviews/{review_id}")
def update_performance_review(
    review_id: str,
    payload: ReviewUpdate,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
):
    row = db.query(HRPerformanceReview).filter_by(id=review_id, tenant_id=tenant_id).with_for_update().first()
    if not row:
        raise HTTPException(status_code=404, detail="Performance review not found.")
    is_reviewer = str(row.reviewer_user_id) == str(current_user.id)
    employee = _employee_or_404(db, tenant_id, row.employee_id)
    is_employee = employee.user_id and str(employee.user_id) == str(current_user.id)
    if payload.employee_comments is not None and is_employee and not is_reviewer:
        if row.status not in {"submitted", "acknowledged"}:
            raise HTTPException(status_code=409, detail="Employee comments are available after the review is submitted.")
        row.employee_comments = payload.employee_comments
        row.status = "acknowledged"
    else:
        _require_permission(db, current_user, "hr.manage_performance")
        if not is_reviewer and (getattr(current_user, "role", "") or "").lower() not in _ADMIN_ROLES:
            raise HTTPException(status_code=403, detail="Only the assigned reviewer or HR administrator may edit this review.")
        if row.status != "draft":
            raise HTTPException(status_code=409, detail="Submitted reviews are immutable; use an amendment workflow.")
        if payload.goals is not None: row.goals = payload.goals
        if payload.strengths is not None: row.strengths = payload.strengths
        if payload.development_areas is not None: row.development_areas = payload.development_areas
        if payload.status is not None:
            if payload.status != "submitted": raise HTTPException(status_code=422, detail="Only draft-to-submitted is supported.")
            row.status = "submitted"
            row.submitted_at = datetime.now(timezone.utc)
    db.commit()
    return {"id": row.id, "status": row.status}


@router.post("/compensation/proposals")
def create_compensation_proposal(
    payload: CompensationProposalCreate,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
):
    _require_permission(db, current_user, "hr.manage_compensation")
    employee = _employee_or_404(db, tenant_id, payload.employee_id)
    currency = payload.currency.strip().upper()
    if not currency.isalpha():
        raise HTTPException(status_code=422, detail="Currency must be a three-letter ISO code.")
    if payload.current_amount is not None and payload.current_amount < 0:
        raise HTTPException(status_code=422, detail="Current amount cannot be negative.")
    if payload.current_amount is not None and payload.proposed_amount == payload.current_amount:
        raise HTTPException(status_code=422, detail="Proposed compensation must differ from current compensation.")
    proposal = HRCompensationChange(
        tenant_id=tenant_id, employee_id=employee.id, requested_by_user_id=current_user.id,
        currency=currency, current_amount=payload.current_amount, proposed_amount=payload.proposed_amount,
        reason=payload.reason.strip(), status="pending_approval",
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)
    return {"id": proposal.id, "status": proposal.status, "approval_required": True}


@router.post("/compensation/proposals/{proposal_id}/decision")
def decide_compensation_proposal(
    proposal_id: str,
    payload: CompensationDecision,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
):
    _require_permission(db, current_user, "hr.manage_compensation")
    proposal = db.query(HRCompensationChange).filter_by(id=proposal_id, tenant_id=tenant_id).with_for_update().first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Compensation proposal not found.")
    if str(proposal.requested_by_user_id) == str(current_user.id):
        raise HTTPException(status_code=403, detail="The proposer cannot approve their own compensation change.")
    if proposal.status != "pending_approval":
        raise HTTPException(status_code=409, detail="Only pending compensation proposals can be decided.")
    decision = payload.decision.strip().lower()
    if decision not in {"approved", "rejected"}:
        raise HTTPException(status_code=422, detail="Decision must be approved or rejected.")
    proposal.status = decision
    proposal.approver_user_id = current_user.id
    proposal.decided_at = datetime.now(timezone.utc)
    proposal.decision_reason = payload.reason.strip()
    db.commit()
    # Approval is a decision record only; this endpoint does not alter payroll or salary systems.
    return {"id": proposal.id, "status": proposal.status, "payroll_applied": False}


@router.post("/lifecycle/start")
def start_lifecycle(
    payload: LifecycleStart,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
):
    _require_permission(db, current_user, "hr.manage_lifecycle")
    employee = _employee_or_404(db, tenant_id, payload.employee_id)
    lifecycle = payload.lifecycle.strip().lower()
    if lifecycle not in {"onboarding", "offboarding"}:
        raise HTTPException(status_code=422, detail="lifecycle must be onboarding or offboarding.")
    if lifecycle == "onboarding" and employee.status not in {"onboarding", "probation"}:
        raise HTTPException(status_code=409, detail="Onboarding tasks require an onboarding/probation employee.")
    if lifecycle == "offboarding" and employee.status == "terminated":
        raise HTTPException(status_code=409, detail="Employee is already terminated.")
    active_case = db.query(HRLifecycleCase).filter_by(
        tenant_id=tenant_id, employee_id=employee.id, lifecycle=lifecycle, status="in_progress"
    ).first()
    if not active_case:
        active_case = HRLifecycleCase(
            tenant_id=tenant_id, employee_id=employee.id, lifecycle=lifecycle,
            initiated_by_user_id=current_user.id, status="in_progress"
        )
        db.add(active_case)
        db.flush()

    templates = {
        "onboarding": [
            ("identity_verification", "Verify identity and employment documents"),
            ("contract", "Confirm signed employment agreement"),
            ("payroll_setup", "Verify payroll and tax setup"),
            ("equipment_access", "Provision equipment and approved system access"),
            ("manager_orientation", "Complete manager and team orientation"),
        ],
        "offboarding": [
            ("manager_handover", "Complete manager handover"),
            ("assets_return", "Verify return of company assets"),
            ("access_revocation", "Revoke access after authorized separation time"),
            ("payroll_reconciliation", "Reconcile final payroll and benefits"),
            ("records_retention", "Apply retention and legal-hold policy"),
        ],
    }
    created = []
    for key, title in templates[lifecycle]:
        task = db.query(HRLifecycleTask).filter_by(tenant_id=tenant_id, employee_id=employee.id, lifecycle=lifecycle, task_key=key).first()
        if not task:
            task = HRLifecycleTask(tenant_id=tenant_id, employee_id=employee.id, lifecycle=lifecycle, task_key=key, title=title, due_at=payload.due_at)
            db.add(task)
        created.append(task)
    db.commit()
    return {"case_id": active_case.id, "employee_id": employee.id, "lifecycle": lifecycle, "case_status": active_case.status, "tasks": [{"id": t.id, "key": t.task_key, "title": t.title, "status": t.status} for t in created]}


@router.get("/lifecycle/{employee_id}")
def list_lifecycle_tasks(
    employee_id: str,
    lifecycle: Optional[str] = None,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
):
    employee = _employee_or_404(db, tenant_id, employee_id)
    _self_or_permission(db, current_user, employee, "hr.view_employees")
    q = db.query(HRLifecycleTask).filter_by(tenant_id=tenant_id, employee_id=employee.id)
    if lifecycle: q = q.filter(HRLifecycleTask.lifecycle == lifecycle)
    tasks = q.order_by(HRLifecycleTask.created_at.asc()).all()
    return [{"id": t.id, "lifecycle": t.lifecycle, "task_key": t.task_key, "title": t.title, "status": t.status, "verification_required": t.verification_required, "verified_at": t.verified_at.isoformat() if t.verified_at else None} for t in tasks]


@router.patch("/lifecycle/tasks/{task_id}")
def update_lifecycle_task(
    task_id: str,
    payload: LifecycleTaskUpdate,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
):
    _require_permission(db, current_user, "hr.manage_lifecycle")
    task = db.query(HRLifecycleTask).filter_by(id=task_id, tenant_id=tenant_id).with_for_update().first()
    if not task:
        raise HTTPException(status_code=404, detail="Lifecycle task not found.")
    if task.status == "completed" and payload.status != "completed":
        raise HTTPException(status_code=409, detail="Completed tasks are immutable; use a reopening workflow.")
    if payload.status not in {"open", "in_progress", "blocked", "completed"}:
        raise HTTPException(status_code=422, detail="Invalid task status.")
    if payload.status == "completed" and task.verification_required and not (payload.verification_note and payload.verification_note.strip()):
        raise HTTPException(status_code=422, detail="A verification note is required to complete this task.")
    task.status = payload.status
    if payload.status == "completed":
        task.verified_by_user_id = current_user.id
        task.verified_at = datetime.now(timezone.utc)
        task.verification_note = payload.verification_note.strip() if payload.verification_note else None
    db.commit()
    return {"id": task.id, "status": task.status, "verified_at": task.verified_at.isoformat() if task.verified_at else None}


@router.post("/lifecycle/{employee_id}/finalize")
def finalize_lifecycle(
    employee_id: str,
    payload: LifecycleFinalize,
    lifecycle: str = Query(..., pattern="^(onboarding|offboarding)$"),
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
):
    _require_permission(db, current_user, "hr.manage_lifecycle")
    employee = _employee_or_404(db, tenant_id, employee_id)
    case = db.query(HRLifecycleCase).filter_by(
        tenant_id=tenant_id, employee_id=employee.id, lifecycle=lifecycle, status="in_progress"
    ).with_for_update().first()
    if not case:
        raise HTTPException(status_code=404, detail="No active lifecycle case found.")
    if str(case.initiated_by_user_id) == str(current_user.id):
        raise HTTPException(status_code=403, detail="The lifecycle initiator cannot finalize the same case.")
    if lifecycle == "offboarding" and not (payload.reason and payload.reason.strip()):
        raise HTTPException(status_code=422, detail="A documented offboarding reason is required.")
    tasks = db.query(HRLifecycleTask).filter_by(
        tenant_id=tenant_id, employee_id=employee.id, lifecycle=lifecycle
    ).all()
    if not tasks:
        raise HTTPException(status_code=409, detail="Lifecycle checklist is empty; initialize it before finalization.")
    incomplete = [task.task_key for task in tasks if task.status != "completed" or (task.verification_required and not task.verified_at)]
    if incomplete:
        raise HTTPException(status_code=409, detail={"message": "Required lifecycle tasks are incomplete or unverified.", "tasks": incomplete})
    if lifecycle == "offboarding":
        employee.status = "terminated"
        employee.termination_date = datetime.now(timezone.utc)
        case.reason = payload.reason.strip()
    else:
        if employee.status not in {"onboarding", "probation"}:
            raise HTTPException(status_code=409, detail="Only onboarding/probation employees can complete onboarding.")
        employee.status = "active"
    case.status = "completed"
    case.finalized_by_user_id = current_user.id
    case.finalized_at = datetime.now(timezone.utc)
    db.commit()
    return {
        "case_id": case.id, "employee_id": employee.id, "lifecycle": lifecycle,
        "case_status": case.status, "employee_status": employee.status,
        "finalized_by_user_id": current_user.id, "finalized_at": case.finalized_at.isoformat(),
    }


@router.get("/compensation/proposals")
def list_compensation_proposals(
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
):
    _require_permission(db, current_user, "hr.manage_compensation")
    q = db.query(HRCompensationChange).filter_by(tenant_id=tenant_id)
    if status:
        q = q.filter(HRCompensationChange.status == status.strip().lower())
    rows = q.order_by(HRCompensationChange.created_at.desc()).offset(skip).limit(limit).all()
    return [{
        "id": row.id, "employee_id": row.employee_id, "currency": row.currency,
        "current_amount": str(row.current_amount) if row.current_amount is not None else None,
        "proposed_amount": str(row.proposed_amount), "reason": row.reason,
        "status": row.status, "requested_by_user_id": row.requested_by_user_id,
        "approver_user_id": row.approver_user_id, "decision_reason": row.decision_reason,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "decided_at": row.decided_at.isoformat() if row.decided_at else None,
        "payroll_applied": False,
    } for row in rows]
