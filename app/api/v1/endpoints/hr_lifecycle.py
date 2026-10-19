"""Lifecycle routes added beside the existing hiring API. They do not replace it."""
import hashlib
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

import app.services.hr.capabilities  # noqa: F401
from app.api import deps
from app.core.approval_service import ApprovalService
from app.core.event_ledger import EventLedger
from app.core.governance import DeterministicGovernanceKernel
from app.core.rbac import normalize_role
from app.models.base import User
from app.models.executive import ApprovalDecision, BudgetEnvelope, BudgetReservation, ExecutiveApprovalRequest
from app.models.hr import (
    Application,
    Assessment,
    Employee,
    EvidenceFact,
    HRDocument,
    Interview,
    InterviewFeedback,
    JobRequisition,
    Offer,
    OnboardingTask,
    ProvisioningRequest,
    SalaryBand,
)
from app.models.verticals import Candidate
from app.models.workflows import Workflow, WorkflowTask
from app.services.executive_os.state_machine import TaskState
from app.services.hr.analytics import RecruitmentAnalytics
from app.services.hr.anchors import ensure_application_anchor, mark_running
from app.services.hr.agents.orchestrator import HROrchestrator
from app.services.hr.approvals import can_decide, r4_pair_ok
from app.services.hr.document_store import LocalPrivateDocumentStore, sha256_bytes
from app.services.hr.field_policy import HRFieldPolicy
from app.services.hr.idempotency import canonical_json, hr_idempotency_key
from app.services.hr.migration_map import backfill_candidates
from app.services.hr.offer_policy import OfferPolicy, hr_envelope
from app.services.hr.onboarding_service import complete_task
from app.services.hr.stage_service import StageService

router = APIRouter()

ADMIN_EQ = {"hr_admin", "admin", "super_admin"}
OFFER_AUTHORS = ADMIN_EQ | {"hr_hiring_manager", "manager"}
REJECT_AUTHORS = ADMIN_EQ | {"hr_recruiter", "hr_hiring_manager", "manager"}


class RequisitionIn(BaseModel):
    title: str
    headcount_approved: int = 1
    organization_id: Optional[str] = None


class ApplicationIn(BaseModel):
    candidate_id: str
    requisition_id: str
    source: Optional[str] = None
    lawful_basis: Optional[str] = None


class TransitionIn(BaseModel):
    to_stage: str
    idempotency_key: Optional[str] = None


class RejectIn(BaseModel):
    reason: str


class AssessmentIn(BaseModel):
    kind: str = "resume_screen"
    confirmed_facts: list[dict] = []
    narrative: Optional[str] = None


class InterviewIn(BaseModel):
    application_id: str
    round_name: str = "Interview"
    tz: str = "UTC"
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None


class FeedbackIn(BaseModel):
    ratings: dict = {}
    notes: Optional[str] = None
    recommendation: Optional[str] = None


class ScheduleIn(BaseModel):
    recipient_email: str


class BandIn(BaseModel):
    requisition_id: str
    currency: str = "USD"
    min_amount: Decimal
    mid_amount: Decimal
    max_amount: Decimal


class EnvelopeIn(BaseModel):
    currency: str = "USD"
    authorized_limit: Decimal


class OfferIn(BaseModel):
    application_id: str
    base_amount: Decimal
    currency: str = "USD"


class AcceptIn(BaseModel):
    token: str


class DecideIn(BaseModel):
    decision: str
    rationale: str
    payload: dict


class CopilotIn(BaseModel):
    message: str


class TaskVerifyIn(BaseModel):
    verified: bool = False


def _role(user: User) -> str:
    return normalize_role(getattr(user, "role", None) or "agent")


def _require(user: User, allowed: set[str]) -> None:
    if getattr(user, "is_system_admin", False) or getattr(user, "is_superuser", False):
        return
    if _role(user) not in allowed and (user.role or "") not in allowed:
        raise HTTPException(status_code=403, detail="Permission denied for this HR action.")


def _application(db: Session, tenant_id: str, application_id: str) -> Application:
    row = db.query(Application).filter_by(id=application_id, tenant_id=tenant_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Application not found.")
    return row


def _policy(user: User) -> HRFieldPolicy:
    return HRFieldPolicy(user.role or "agent")


@router.post("/requisitions")
def create_requisition(
    body: RequisitionIn,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    user: User = Depends(deps.get_current_user),
):
    _require(user, ADMIN_EQ | {"hr_recruiter", "hr_hiring_manager", "manager", "agent"})
    row = JobRequisition(
        tenant_id=tenant_id,
        organization_id=body.organization_id,
        title=body.title.strip() or "Unspecified role",
        status="draft",
        headcount_approved=body.headcount_approved,
        opened_at_confirmed=False,
        recruiter_user_id=str(user.id),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "title": row.title, "status": row.status}


@router.post("/requisitions/{requisition_id}/open")
def open_requisition(
    requisition_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    user: User = Depends(deps.get_current_user),
):
    _require(user, ADMIN_EQ)
    row = db.query(JobRequisition).filter_by(id=requisition_id, tenant_id=tenant_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Requisition not found.")
    row.status = "open"
    row.opened_at = row.opened_at or datetime.now(timezone.utc)
    row.opened_at_confirmed = True
    db.commit()
    return {"id": row.id, "status": row.status, "opened_at_confirmed": True}


@router.get("/requisitions")
def list_requisitions(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    user: User = Depends(deps.get_current_user),
):
    rows = db.query(JobRequisition).filter_by(tenant_id=tenant_id).all()
    policy = _policy(user)
    payload = [
        {
            "id": r.id,
            "title": r.title,
            "status": r.status,
            "headcount_approved": r.headcount_approved,
            "headcount_filled": r.headcount_filled,
            "opened_at_confirmed": r.opened_at_confirmed,
            "legacy_salary_text": r.legacy_salary_text,
        }
        for r in rows
    ]
    return [policy.redact(item) for item in payload]


@router.post("/applications")
def create_application(
    body: ApplicationIn,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    user: User = Depends(deps.get_current_user),
):
    _require(user, ADMIN_EQ | {"hr_recruiter", "hr_hiring_manager", "manager", "agent"})
    person = db.query(Candidate).filter_by(id=body.candidate_id, tenant_id=tenant_id).first()
    requisition = db.query(JobRequisition).filter_by(id=body.requisition_id, tenant_id=tenant_id).first()
    if not person or not requisition:
        raise HTTPException(status_code=404, detail="Candidate or requisition not found.")
    if person.merged_into_candidate_id:
        raise HTTPException(status_code=409, detail="This row was merged into another person. Use the surviving candidate.")
    existing = db.query(Application).filter_by(
        tenant_id=tenant_id, candidate_id=person.id, requisition_id=requisition.id
    ).first()
    if existing:
        return {"id": existing.id, "current_stage": existing.current_stage, "reused": True}
    consent = "basis_recorded" if body.lawful_basis else "unknown_legacy"
    row = Application(
        tenant_id=tenant_id,
        candidate_id=person.id,
        requisition_id=requisition.id,
        source=body.source,
        consent_status=consent,
        lawful_basis=body.lawful_basis,
        applied_at=datetime.now(timezone.utc),
        applied_at_confirmed=True,
        status="active",
        current_stage="sourced",
    )
    db.add(row)
    db.flush()
    ensure_application_anchor(db, tenant_id, row)
    db.commit()
    return {"id": row.id, "current_stage": row.current_stage, "workflow_id": row.workflow_id}


@router.get("/applications")
def list_applications(
    requisition_id: Optional[str] = None,
    stage: Optional[str] = None,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    user: User = Depends(deps.get_current_user),
):
    query = db.query(Application).filter_by(tenant_id=tenant_id)
    if requisition_id:
        query = query.filter_by(requisition_id=requisition_id)
    if stage:
        query = query.filter_by(current_stage=stage)
    policy = _policy(user)
    rows = []
    for app in query.all():
        person = db.query(Candidate).filter_by(id=app.candidate_id).first()
        req = db.query(JobRequisition).filter_by(id=app.requisition_id).first()
        rows.append(policy.redact({
            "id": app.id,
            "candidate_id": app.candidate_id,
            "name": person.name if person else None,
            "email": person.email if person else None,
            "requisition_id": app.requisition_id,
            "title": req.title if req else None,
            "current_stage": app.current_stage,
            "status": app.status,
            "source": app.source,
            "legacy_salary_text": req.legacy_salary_text if req else None,
        }))
    return rows


@router.post("/applications/{application_id}/transition")
def transition_application(
    application_id: str,
    body: TransitionIn,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    user: User = Depends(deps.get_current_user),
):
    application = _application(db, tenant_id, application_id)
    row = StageService(db, tenant_id).transition(
        application, body.to_stage, str(user.id), user.role or "agent", body.idempotency_key
    )
    approvals = db.query(ExecutiveApprovalRequest).filter_by(tenant_id=tenant_id, workflow_id=application.workflow_id).count()
    db.commit()
    return {"transition_id": row.id, "to_stage": row.to_stage, "approval_rows_for_workflow": approvals}


@router.post("/applications/{application_id}/reject")
def request_rejection(
    application_id: str,
    body: RejectIn,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    user: User = Depends(deps.get_current_user),
):
    _require(user, REJECT_AUTHORS)
    application = _application(db, tenant_id, application_id)
    workflow = ensure_application_anchor(db, tenant_id, application)
    payload = {"application_id": application.id, "reason": body.reason}
    key = hr_idempotency_key(tenant_id, "hr.application.reject", application.id, payload)
    decision = DeterministicGovernanceKernel(db, tenant_id).evaluate(
        capability_id="hr.application.reject",
        capability_version="1.0.0",
        inputs=payload,
        actor_role=user.role or "agent",
        actor_autonomy="L1",
    )
    if decision["decision"] == "DENY":
        raise HTTPException(status_code=403, detail=decision["reason"])
    task = WorkflowTask(
        workflow_id=workflow.id,
        name="Reject application",
        task_type="hr.application.reject",
        status=TaskState.PENDING.value,
        payload={"canonical": payload, "requester_role": user.role or "agent"},
    )
    db.add(task)
    db.flush()
    approval = ApprovalService(db, tenant_id).create_request(
        workflow_id=workflow.id,
        plan_version_id=None,
        task_id=task.id,
        capability_id="hr.application.reject",
        capability_version="1.0.0",
        payload=payload,
        risk_class="R3_EXTERNAL_IRREVERSIBLE",
        title="Reject application",
        description=body.reason,
        requester_user_id=str(user.id),
        idempotency_key=key,
    )
    EventLedger.append_event(
        db=db,
        tenant_id=tenant_id,
        workflow_id=workflow.id,
        execution_id=application.id,
        event_type="hr.application.rejection_requested",
        actor_type="USER",
        actor_id=str(user.id),
        payload={"application_id": application.id},
        correlation_id=key,
    )
    db.commit()
    return {"approval_id": approval.id, "current_stage": application.current_stage, "idempotency_key": key}


@router.post("/applications/{application_id}/assessments")
def add_assessment(
    application_id: str,
    body: AssessmentIn,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    user: User = Depends(deps.get_current_user),
):
    application = _application(db, tenant_id, application_id)
    version = db.query(Assessment).filter_by(application_id=application.id, kind=body.kind).count() + 1
    previous = db.query(Assessment).filter_by(application_id=application.id, kind=body.kind, status="current").all()
    for row in previous:
        row.status = "superseded"
    assessment = Assessment(
        tenant_id=tenant_id,
        application_id=application.id,
        requisition_id=application.requisition_id,
        kind=body.kind,
        version=version,
        status="current",
    )
    db.add(assessment)
    db.flush()
    for fact in body.confirmed_facts:
        if "match_score" in fact:
            continue
        db.add(EvidenceFact(
            tenant_id=tenant_id,
            assessment_id=assessment.id,
            application_id=application.id,
            source="recruiter_confirmed",
            fact_type=str(fact.get("fact_type") or "note"),
            value=str(fact.get("value") or ""),
            evaluative=bool(fact.get("evaluative", True)),
            reusable=False,
            extracted_at=datetime.now(timezone.utc),
        ))
    db.commit()
    return {"id": assessment.id, "version": version, "narrative_stored_as_decision": False}


@router.post("/interviews")
def propose_interview(
    body: InterviewIn,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    user: User = Depends(deps.get_current_user),
):
    application = _application(db, tenant_id, body.application_id)
    row = Interview(
        tenant_id=tenant_id,
        application_id=application.id,
        requisition_id=application.requisition_id,
        status="proposed",
        tz=body.tz or "UTC",
        round_name=body.round_name,
        starts_at=body.starts_at,
        ends_at=body.ends_at,
        meeting_url=None,
    )
    db.add(row)
    db.commit()
    return {"id": row.id, "status": row.status, "tz": row.tz, "meeting_url": None}


@router.post("/interviews/{interview_id}/feedback")
def add_feedback(
    interview_id: str,
    body: FeedbackIn,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    user: User = Depends(deps.get_current_user),
):
    interview = db.query(Interview).filter_by(id=interview_id, tenant_id=tenant_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found.")
    if db.query(InterviewFeedback).filter_by(interview_id=interview.id, author_user_id=str(user.id)).first():
        raise HTTPException(status_code=409, detail="Feedback already submitted for this interview.")
    application = _application(db, tenant_id, interview.application_id)
    version = db.query(Assessment).filter_by(application_id=application.id, kind="interview_round").count() + 1
    assessment = Assessment(
        tenant_id=tenant_id,
        application_id=application.id,
        requisition_id=application.requisition_id,
        interview_id=interview.id,
        kind="interview_round",
        version=version,
        status="current",
    )
    db.add(assessment)
    db.flush()
    feedback = InterviewFeedback(
        interview_id=interview.id,
        author_user_id=str(user.id),
        assessment_id=assessment.id,
        ratings=body.ratings,
        notes=body.notes,
        recommendation=body.recommendation,
    )
    db.add(feedback)
    db.commit()
    return _policy(user).redact({"id": feedback.id, "notes": feedback.notes, "ratings": feedback.ratings})


@router.post("/interviews/{interview_id}/schedule")
def schedule_interview(
    interview_id: str,
    body: ScheduleIn,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    user: User = Depends(deps.get_current_user),
):
    interview = db.query(Interview).filter_by(id=interview_id, tenant_id=tenant_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found.")
    application = _application(db, tenant_id, interview.application_id)
    if application.consent_status == "unknown_legacy":
        raise HTTPException(status_code=409, detail="Candidate email is blocked until a lawful basis is recorded.")
    return _queue_external(
        db, tenant_id, user, application, "hr.interview.schedule",
        {
            "interview_id": interview.id,
            "recipient_email": body.recipient_email,
            "tz": interview.tz,
            "starts_at": interview.starts_at.isoformat() if interview.starts_at else None,
        },
        "Schedule interview",
        "R3_EXTERNAL_IRREVERSIBLE",
    )


@router.post("/salary-bands")
def create_band(
    body: BandIn,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    user: User = Depends(deps.get_current_user),
):
    _require(user, ADMIN_EQ)
    if not db.query(JobRequisition).filter_by(id=body.requisition_id, tenant_id=tenant_id).first():
        raise HTTPException(status_code=404, detail="Requisition not found.")
    if not (body.min_amount <= body.mid_amount <= body.max_amount):
        raise HTTPException(status_code=422, detail="Band amounts must be min <= mid <= max.")
    row = SalaryBand(
        tenant_id=tenant_id,
        requisition_id=body.requisition_id,
        currency=body.currency,
        min_amount=body.min_amount,
        mid_amount=body.mid_amount,
        max_amount=body.max_amount,
        effective_from=datetime.now(timezone.utc),
        created_by_user_id=str(user.id),
    )
    db.add(row)
    db.commit()
    return {"id": row.id}


@router.post("/budget-envelopes")
def create_envelope(
    body: EnvelopeIn,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    user: User = Depends(deps.get_current_user),
):
    _require(user, ADMIN_EQ)
    if hr_envelope(db, tenant_id, body.currency):
        raise HTTPException(status_code=409, detail="An active HR envelope already exists for this currency.")
    now = datetime.now(timezone.utc)
    row = BudgetEnvelope(
        tenant_id=tenant_id,
        department="hr",
        currency=body.currency,
        period_start=now,
        period_end=now + timedelta(days=365),
        authorized_limit=body.authorized_limit,
        reserved_amount=Decimal("0"),
        consumed_amount=Decimal("0"),
        is_active=True,
    )
    db.add(row)
    db.commit()
    return {"id": row.id, "department": "hr", "currency": row.currency}


@router.post("/offers")
def draft_offer(
    body: OfferIn,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    user: User = Depends(deps.get_current_user),
):
    _require(user, OFFER_AUTHORS)
    application = _application(db, tenant_id, body.application_id)
    version = db.query(Offer).filter_by(application_id=application.id).count() + 1
    offer = Offer(
        tenant_id=tenant_id,
        application_id=application.id,
        version=version,
        currency=body.currency,
        base_amount=body.base_amount,
        status="draft",
        signature_state="none",
        created_by_user_id=str(user.id),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        document_sha256=hashlib.sha256(f"{application.id}:{body.base_amount}:{body.currency}".encode()).hexdigest(),
    )
    check = OfferPolicy(db, tenant_id).check(offer, dry=True)
    db.add(offer)
    db.commit()
    reservations = db.query(BudgetReservation).filter_by(tenant_id=tenant_id).count()
    return _policy(user).redact({
        "id": offer.id,
        "status": offer.status,
        "check": check.status,
        "risk_class": check.risk_class,
        "base_amount": str(offer.base_amount),
        "reservations": reservations,
    }, authored_by=str(user.id), viewer_id=str(user.id))


@router.post("/offers/{offer_id}/submit")
def submit_offer(
    offer_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    user: User = Depends(deps.get_current_user),
):
    _require(user, OFFER_AUTHORS)
    offer = db.query(Offer).filter_by(id=offer_id, tenant_id=tenant_id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found.")
    application = _application(db, tenant_id, offer.application_id)
    person = db.query(Candidate).filter_by(id=application.candidate_id).first()
    if application.consent_status == "unknown_legacy":
        raise HTTPException(status_code=409, detail="Candidate email is blocked until a lawful basis is recorded.")
    envelope = hr_envelope(db, tenant_id, offer.currency)
    if not envelope:
        raise HTTPException(status_code=422, detail="budget_unavailable")
    workflow = ensure_application_anchor(db, tenant_id, application)
    mark_running(db, workflow)
    payload = {
        "offer_id": offer.id,
        "recipient_email": person.email if person else "",
        "currency": offer.currency,
        "base_amount": str(offer.base_amount),
        "document_sha256": offer.document_sha256,
    }
    decision = DeterministicGovernanceKernel(db, tenant_id).evaluate(
        capability_id="hr.offer.send",
        capability_version="1.0.0",
        inputs=payload,
        actor_role=user.role or "agent",
        actor_autonomy="L1",
    )
    if decision["decision"] == "DENY":
        raise HTTPException(status_code=403, detail=decision["reason"])
    if decision["decision"] == "ALLOW":
        raise HTTPException(status_code=409, detail="offer_send_must_be_approved")
    key = hr_idempotency_key(tenant_id, "hr.offer.send", offer.id, payload)
    task = WorkflowTask(
        workflow_id=workflow.id,
        name="Send offer",
        task_type="hr.offer.send",
        status=TaskState.PENDING.value,
        payload={"canonical": payload, "requester_role": user.role or "agent"},
    )
    db.add(task)
    db.flush()
    check = OfferPolicy(db, tenant_id).check(
        offer, dry=False, envelope_id=envelope.id, workflow_id=workflow.id,
        task_id=task.id, idempotency_key=key, hold_until=offer.expires_at,
    )
    if check.status != "ok":
        raise HTTPException(status_code=422, detail=check.status)
    approval = ApprovalService(db, tenant_id).create_request(
        workflow_id=workflow.id,
        plan_version_id=None,
        task_id=task.id,
        capability_id="hr.offer.send",
        capability_version="1.0.0",
        payload=payload,
        risk_class=check.risk_class,
        title=f"Send offer {offer.id}",
        description="Candidate offer send",
        financial_impact=offer.base_amount,
        requester_user_id=str(user.id),
        idempotency_key=key,
    )
    if check.required_keys == 2:
        approval.required_keys = 2
        approval.risk_class = "R4_FINANCIAL_CRITICAL"
    offer.status = "pending_approval"
    offer.approval_request_id = approval.id
    offer.payload_hash = hashlib.sha256(canonical_json(payload).encode()).hexdigest()
    db.commit()
    return {"approval_id": approval.id, "idempotency_key": key, "risk_class": approval.risk_class}


@router.post("/offers/{offer_id}/accept")
def accept_offer(
    offer_id: str,
    body: AcceptIn,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    user: User = Depends(deps.get_current_user),
):
    offer = db.query(Offer).filter_by(id=offer_id, tenant_id=tenant_id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found.")
    if not body.token:
        raise HTTPException(status_code=422, detail="Acceptance token is required.")
    offer.signature_state = "signed"
    offer.status = "accepted"
    db.commit()
    employees = db.query(Employee).filter_by(tenant_id=tenant_id, application_id=offer.application_id).count()
    return {"signature_state": offer.signature_state, "employees": employees}


@router.post("/employees")
def request_hire(
    offer_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    user: User = Depends(deps.get_current_user),
):
    _require(user, ADMIN_EQ | {"hr_hiring_manager", "manager"})
    offer = db.query(Offer).filter_by(id=offer_id, tenant_id=tenant_id).first()
    if not offer or offer.signature_state != "signed":
        raise HTTPException(status_code=409, detail="A signed offer is required before hire.")
    application = _application(db, tenant_id, offer.application_id)
    send_approval = db.query(ExecutiveApprovalRequest).filter_by(id=offer.approval_request_id).first() if offer.approval_request_id else None
    if not send_approval or not send_approval.idempotency_key:
        raise HTTPException(status_code=409, detail="The offer hold key is missing.")
    payload = {
        "offer_id": offer.id,
        "application_id": application.id,
        "offer_idempotency_key": send_approval.idempotency_key,
    }
    return _queue_external(
        db, tenant_id, user, application, "hr.employee.hire", payload,
        "Hire employee", "R4_FINANCIAL_CRITICAL", subject_id=offer.id,
    )


@router.post("/employees/{employee_id}/offboard")
def request_offboard(
    employee_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    user: User = Depends(deps.get_current_user),
):
    _require(user, ADMIN_EQ)
    employee = db.query(Employee).filter_by(id=employee_id, tenant_id=tenant_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found.")
    application = _application(db, tenant_id, employee.application_id)
    key = hr_idempotency_key(tenant_id, "hr.provisioning.revoke", employee.id, {"employee_id": employee.id})
    db.add(ProvisioningRequest(
        tenant_id=tenant_id,
        employee_id=employee.id,
        action="revoke",
        system="manual",
        status="pending",
        idempotency_key=key,
    ))
    db.flush()
    queued = _queue_external(
        db, tenant_id, user, application, "hr.provisioning.revoke",
        {"employee_id": employee.id, "system": "manual"},
        "Revoke access", "R4_FINANCIAL_CRITICAL", subject_id=employee.id,
    )
    return queued


@router.post("/onboarding-tasks/{task_id}/complete")
def complete_onboarding_task(
    task_id: str,
    body: TaskVerifyIn,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    user: User = Depends(deps.get_current_user),
):
    task = db.query(OnboardingTask).filter_by(id=task_id, tenant_id=tenant_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    try:
        complete_task(db, task, body.verified)
    except ValueError:
        raise HTTPException(status_code=409, detail="This task requires verification.")
    db.commit()
    return {"status": task.status, "verified_at": task.verified_at.isoformat() if task.verified_at else None}


@router.post("/approvals/{approval_id}/decide")
def decide_approval(
    approval_id: str,
    body: DecideIn,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    user: User = Depends(deps.get_current_user),
):
    _require(user, ADMIN_EQ | {"executive"})
    approval = db.query(ExecutiveApprovalRequest).filter_by(id=approval_id, tenant_id=tenant_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found.")
    task = db.query(WorkflowTask).filter_by(id=approval.task_id).first()
    stored = (task.payload or {}) if task else {}
    requester_role = stored.get("requester_role") or "agent"
    if not can_decide(requester_role, user.role or "", approval.requester_user_id, str(user.id)):
        raise HTTPException(status_code=403, detail="You cannot approve this request.")
    if approval.risk_class == "R4_FINANCIAL_CRITICAL":
        prior = db.query(ApprovalDecision).filter_by(approval_request_id=approval.id, decision="APPROVE").all()
        if len({d.user_id for d in prior} | {str(user.id)}) >= approval.required_keys:
            if not r4_pair_ok([d.user_role for d in prior], user.role or ""):
                raise HTTPException(status_code=403, detail="Out-of-band approval needs one HR admin and one executive.")
    payload = stored.get("canonical") or body.payload
    try:
        result = ApprovalService(db, tenant_id).record_decision(
            request_id=approval.id,
            user_id=str(user.id),
            user_role=user.role or "admin",
            decision=body.decision,
            rationale=body.rationale,
            payload=payload,
            idempotency_key=approval.idempotency_key,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    if result["status"] == "APPROVED" and approval.capability_id == "hr.application.reject":
        application_id = payload.get("application_id")
        application = _application(db, tenant_id, application_id)
        StageService(db, tenant_id).apply_approved_rejection(application, str(user.id), approval.idempotency_key)
    db.commit()
    return result


@router.get("/analytics")
def analytics(
    metric: str = "time_to_fill",
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    user: User = Depends(deps.get_current_user),
):
    _require(user, ADMIN_EQ | {"executive", "hr_hiring_manager", "manager"})
    return RecruitmentAnalytics(db, tenant_id).metric(metric)


@router.post("/copilot")
def copilot(
    body: CopilotIn,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    user: User = Depends(deps.get_current_user),
):
    result = HROrchestrator().handle(db, tenant_id, str(user.id), body.message)
    db.commit()
    return result


@router.get("/workflows/{application_id}")
def workflow_history(
    application_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    user: User = Depends(deps.get_current_user),
):
    application = _application(db, tenant_id, application_id)
    from app.models.executive import SideEffectOutbox, WorkflowEvent
    events = []
    outbox = []
    if application.workflow_id:
        events = [
            {"event_type": e.event_type, "created_at": e.created_at.isoformat() if e.created_at else None}
            for e in db.query(WorkflowEvent).filter_by(workflow_id=application.workflow_id).all()
        ]
        outbox = [
            {"capability_id": o.capability_id, "status": o.status, "last_error": o.last_error}
            for o in db.query(SideEffectOutbox).filter_by(workflow_id=application.workflow_id).all()
        ]
    return {"events": events, "outbox": outbox, "workflow_status": db.query(Workflow).filter_by(id=application.workflow_id).first().status if application.workflow_id else None}


@router.post("/lifecycle/backfill")
def run_backfill(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    user: User = Depends(deps.get_current_user),
):
    _require(user, ADMIN_EQ)
    result = backfill_candidates(db)
    db.commit()
    return result


@router.get("/documents/{document_id}")
def read_document(
    document_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    user: User = Depends(deps.get_current_user),
):
    document = db.query(HRDocument).filter_by(id=document_id, tenant_id=tenant_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    if not _policy(user).can_read_document(document.classification):
        raise HTTPException(status_code=403, detail="You cannot read this document.")
    if not document.storage_key:
        raise HTTPException(status_code=404, detail="Document bytes have not been copied to private storage.")
    data = LocalPrivateDocumentStore().open(document.storage_key)
    if document.sha256 and sha256_bytes(data) != document.sha256:
        raise HTTPException(status_code=409, detail="Document checksum mismatch.")
    return {"id": document.id, "classification": document.classification, "sha256": document.sha256, "size": len(data)}


def _queue_external(
    db: Session,
    tenant_id: str,
    user: User,
    application: Application,
    capability_id: str,
    payload: dict,
    title: str,
    risk_class: str,
    subject_id: str | None = None,
) -> dict[str, Any]:
    workflow = ensure_application_anchor(db, tenant_id, application)
    decision = DeterministicGovernanceKernel(db, tenant_id).evaluate(
        capability_id=capability_id,
        capability_version="1.0.0",
        inputs=payload,
        actor_role=user.role or "agent",
        actor_autonomy="L1",
    )
    if decision["decision"] == "DENY":
        raise HTTPException(status_code=403, detail=decision["reason"])
    if decision["decision"] == "ALLOW" and risk_class.startswith("R3"):
        raise HTTPException(status_code=409, detail="external_action_must_be_approved")
    key = hr_idempotency_key(tenant_id, capability_id, subject_id or application.id, payload)
    task = WorkflowTask(
        workflow_id=workflow.id,
        name=title,
        task_type=capability_id,
        status=TaskState.PENDING.value,
        payload={"canonical": payload, "requester_role": user.role or "agent"},
    )
    db.add(task)
    db.flush()
    approval = ApprovalService(db, tenant_id).create_request(
        workflow_id=workflow.id,
        plan_version_id=None,
        task_id=task.id,
        capability_id=capability_id,
        capability_version="1.0.0",
        payload=payload,
        risk_class=risk_class,
        title=title,
        description=title,
        requester_user_id=str(user.id),
        idempotency_key=key,
    )
    if risk_class == "R4_FINANCIAL_CRITICAL":
        approval.required_keys = 2
    db.commit()
    return {"approval_id": approval.id, "idempotency_key": key, "required_keys": approval.required_keys}
