from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.event_ledger import EventLedger
from app.core.rbac import normalize_role
from app.models.hr import Application, StageTransition
from app.services.hr.anchors import ensure_application_anchor
from app.services.hr.idempotency import hr_idempotency_key

INTERNAL_EDGES = {
    "sourced": {"screened", "interviewing"},
    "screened": {"interviewing", "sourced"},
    "interviewing": {"offer", "screened"},
    "offer": {"interviewing"},
}
STAGE_MOVERS = {
    "hr_recruiter", "hr_hiring_manager", "hr_admin", "admin", "super_admin",
    "manager", "agent", "organization_admin",
}


class StageService:
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def transition(self, application: Application, to_stage: str, actor_user_id: str, actor_role: str, idempotency_key: str | None = None) -> StageTransition:
        role = normalize_role(actor_role)
        if role not in STAGE_MOVERS and actor_role not in STAGE_MOVERS:
            raise HTTPException(status_code=403, detail="This role cannot move a candidate stage.")
        if to_stage in {"rejected", "hired"}:
            raise HTTPException(status_code=409, detail="Rejection and hire go through an approval.")
        allowed = INTERNAL_EDGES.get(application.current_stage, set())
        if to_stage not in allowed:
            raise HTTPException(status_code=409, detail=f"Cannot move from {application.current_stage} to {to_stage}.")

        payload = {"application_id": application.id, "to_stage": to_stage}
        key = idempotency_key or hr_idempotency_key(self.tenant_id, "hr.application.stage", application.id, payload)
        existing = self.db.query(StageTransition).filter_by(idempotency_key=key).first()
        if existing:
            return existing

        workflow = ensure_application_anchor(self.db, self.tenant_id, application)
        event = EventLedger.append_event(
            db=self.db,
            tenant_id=self.tenant_id,
            workflow_id=workflow.id,
            execution_id=application.id,
            event_type="hr.application.stage_changed",
            actor_type="USER",
            actor_id=actor_user_id or "user",
            payload={"from": application.current_stage, "to": to_stage, "application_id": application.id},
            correlation_id=key,
        )
        row = StageTransition(
            tenant_id=self.tenant_id,
            application_id=application.id,
            from_stage=application.current_stage,
            to_stage=to_stage,
            actor_user_id=actor_user_id,
            idempotency_key=key,
            ledger_event_id=event.id,
            created_at=datetime.now(timezone.utc),
        )
        application.current_stage = to_stage
        self.db.add(row)
        self.db.flush()
        return row

    def apply_approved_rejection(self, application: Application, actor_user_id: str, idempotency_key: str) -> StageTransition:
        if application.current_stage == "rejected":
            existing = self.db.query(StageTransition).filter_by(idempotency_key=idempotency_key).first()
            if existing:
                return existing
        workflow = ensure_application_anchor(self.db, self.tenant_id, application)
        event = EventLedger.append_event(
            db=self.db,
            tenant_id=self.tenant_id,
            workflow_id=workflow.id,
            execution_id=application.id,
            event_type="hr.application.rejection_approved",
            actor_type="USER",
            actor_id=actor_user_id,
            payload={"application_id": application.id},
            correlation_id=idempotency_key,
        )
        row = StageTransition(
            tenant_id=self.tenant_id,
            application_id=application.id,
            from_stage=application.current_stage,
            to_stage="rejected",
            actor_user_id=actor_user_id,
            idempotency_key=idempotency_key,
            ledger_event_id=event.id,
            created_at=datetime.now(timezone.utc),
        )
        application.current_stage = "rejected"
        application.status = "rejected"
        self.db.add(row)
        self.db.flush()
        return row
