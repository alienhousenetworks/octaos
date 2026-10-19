from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.event_ledger import EventLedger
from app.core.governance import DeterministicGovernanceKernel
from app.models.hr import Employee, JobRequisition, OnboardingTask, Application
from app.services.hr.anchors import ensure_application_anchor


def complete_hire(db: Session, tenant_id: str, offer, application: Application, offer_idempotency_key: str) -> Employee | None:
    now = datetime.now(timezone.utc)
    expires = offer.expires_at
    if expires is not None and expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    kernel = DeterministicGovernanceKernel(db, tenant_id)
    if expires is not None and now > expires:
        kernel.release_hr_hold(offer_idempotency_key)
        return None
    if offer.signature_state != "signed":
        return None
    if not kernel.consume_hr_hold(offer_idempotency_key):
        return None
    employee = Employee(
        tenant_id=tenant_id,
        application_id=application.id,
        candidate_id=application.candidate_id,
        status="active",
        hired_at=now,
    )
    db.add(employee)
    db.flush()
    for title in ("Confirm start date", "Collect documents", "Provision accounts"):
        db.add(OnboardingTask(
            tenant_id=tenant_id,
            employee_id=employee.id,
            title=title,
            verification_required=True,
            status="open",
        ))
    application.status = "hired"
    application.current_stage = "hired"
    requisition = db.query(JobRequisition).filter_by(id=application.requisition_id).first()
    if requisition is not None:
        requisition.headcount_filled = (requisition.headcount_filled or 0) + 1
    workflow = ensure_application_anchor(db, tenant_id, application)
    EventLedger.append_event(
        db=db,
        tenant_id=tenant_id,
        workflow_id=workflow.id,
        execution_id=employee.id,
        event_type="hr.employee.hired",
        actor_type="SYSTEM",
        actor_id="hr.employee.hire",
        payload={"employee_id": employee.id, "application_id": application.id},
        correlation_id=offer_idempotency_key,
    )
    db.flush()
    return employee


def complete_task(db: Session, task: OnboardingTask, verified: bool) -> None:
    if task.verification_required and not verified:
        raise ValueError("verification_required")
    task.status = "done"
    task.verified_at = datetime.now(timezone.utc)
    db.flush()
