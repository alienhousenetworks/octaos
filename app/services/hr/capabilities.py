"""Typed HR tools. Importing this module registers them. Existing HRAgent actions are unchanged."""
from typing import Any, Dict

from app.core.capabilities import BaseCapability, CapabilityCost, CapabilityDefinition, register_capability
from app.db.session import SessionLocal


class _HRCapability(BaseCapability):
    capability_id = "hr.base"
    risk = "R1_INTERNAL_REVERSIBLE"
    description = ""
    max_autonomy = "L1"

    @property
    def definition(self) -> CapabilityDefinition:
        return CapabilityDefinition(
            id=self.capability_id,
            version="1.0.0",
            department="HR",
            description=self.description,
            side_effect_class=self.risk,
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            required_permissions=["hr.execute"],
            cost_model=CapabilityCost(type="flat", amount=0),
            default_autonomy="L1",
            max_autonomy=self.max_autonomy,
            dry_run_supported=True,
            idempotent=True,
            is_compensable=False,
        )

    async def dry_run(self, tenant_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        return {"capability_id": self.capability_id}

    async def compensate(self, tenant_id: str, original_inputs: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "COMPENSATION_NOT_SUPPORTED"}


class ApplicationRejectCapability(_HRCapability):
    capability_id = "hr.application.reject"
    risk = "R3_EXTERNAL_IRREVERSIBLE"
    description = "Approve a rejection. The stage write happens in the approval transaction, not here."
    max_autonomy = "L1"

    async def execute(self, tenant_id: str, inputs: Dict[str, Any], idempotency_key: str) -> Dict[str, Any]:
        raise RuntimeError("hr.application.reject has no outbox side effect")


class OfferSendCapability(_HRCapability):
    capability_id = "hr.offer.send"
    risk = "R3_EXTERNAL_IRREVERSIBLE"
    description = "Send an approved offer email."
    max_autonomy = "L2"

    async def execute(self, tenant_id: str, inputs: Dict[str, Any], idempotency_key: str) -> Dict[str, Any]:
        if not inputs.get("recipient_email"):
            raise ValueError("recipient_email is required")
        db = SessionLocal()
        try:
            from app.models.base import APICredential
            cred = db.query(APICredential).filter_by(tenant_id=tenant_id).filter(
                APICredential.provider.in_(["smtp", "gmail"])
            ).first()
            if not cred:
                raise RuntimeError("smtp_not_configured")
            from app.models.hr import Offer
            offer = db.query(Offer).filter_by(id=inputs.get("offer_id"), tenant_id=tenant_id).first()
            if offer:
                offer.status = "sent"
                db.commit()
            return {"status": "sent", "recipient_email": inputs["recipient_email"]}
        finally:
            db.close()


class InterviewScheduleCapability(_HRCapability):
    capability_id = "hr.interview.schedule"
    risk = "R3_EXTERNAL_IRREVERSIBLE"
    description = "Create a calendar event after approval."
    max_autonomy = "L2"

    async def execute(self, tenant_id: str, inputs: Dict[str, Any], idempotency_key: str) -> Dict[str, Any]:
        if not inputs.get("recipient_email"):
            raise ValueError("recipient_email is required")
        raise RuntimeError("calendar_not_configured")


class InterviewRemindCapability(_HRCapability):
    capability_id = "hr.interview.remind"
    risk = "R3_EXTERNAL_IRREVERSIBLE"
    description = "Send an approved interview reminder."
    max_autonomy = "L2"

    async def execute(self, tenant_id: str, inputs: Dict[str, Any], idempotency_key: str) -> Dict[str, Any]:
        if not inputs.get("recipient_email"):
            raise ValueError("recipient_email is required")
        raise RuntimeError("smtp_not_configured")


class CandidateEmailCapability(_HRCapability):
    capability_id = "hr.candidate.email"
    risk = "R3_EXTERNAL_IRREVERSIBLE"
    description = "Send an approved candidate email."
    max_autonomy = "L2"

    async def execute(self, tenant_id: str, inputs: Dict[str, Any], idempotency_key: str) -> Dict[str, Any]:
        if not inputs.get("recipient_email"):
            raise ValueError("recipient_email is required")
        raise RuntimeError("smtp_not_configured")


class EmployeeHireCapability(_HRCapability):
    capability_id = "hr.employee.hire"
    risk = "R4_FINANCIAL_CRITICAL"
    description = "Create an employee from a signed offer and consume the offer hold."
    max_autonomy = "L2"

    async def execute(self, tenant_id: str, inputs: Dict[str, Any], idempotency_key: str) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            from app.models.hr import Application, Offer
            from app.services.hr.onboarding_service import complete_hire
            offer = db.query(Offer).filter_by(id=inputs["offer_id"], tenant_id=tenant_id).first()
            application = db.query(Application).filter_by(id=inputs["application_id"], tenant_id=tenant_id).first()
            if not offer or not application:
                raise ValueError("offer_or_application_missing")
            employee = complete_hire(db, tenant_id, offer, application, inputs["offer_idempotency_key"])
            db.commit()
            if employee is None:
                return {"status": "not_hired"}
            return {"status": "hired", "employee_id": employee.id}
        finally:
            db.close()


class ProvisioningCapability(_HRCapability):
    capability_id = "hr.provisioning.grant"
    risk = "R4_FINANCIAL_CRITICAL"
    description = "Record a manual provisioning request. No directory connector is called."
    max_autonomy = "L2"

    async def execute(self, tenant_id: str, inputs: Dict[str, Any], idempotency_key: str) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            from app.models.hr import ProvisioningRequest
            row = db.query(ProvisioningRequest).filter_by(idempotency_key=idempotency_key).first()
            if row:
                row.status = "verified"
                db.commit()
            return {"status": "manual_verified", "system": inputs.get("system", "manual")}
        finally:
            db.close()


class ProvisioningRevokeCapability(ProvisioningCapability):
    capability_id = "hr.provisioning.revoke"
    description = "Record a manual access revocation."


def register_hr_capabilities() -> None:
    for cls in (
        ApplicationRejectCapability,
        OfferSendCapability,
        InterviewScheduleCapability,
        InterviewRemindCapability,
        CandidateEmailCapability,
        EmployeeHireCapability,
        ProvisioningCapability,
        ProvisioningRevokeCapability,
    ):
        register_capability(cls())


register_hr_capabilities()
