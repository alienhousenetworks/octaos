from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.governance import DeterministicGovernanceKernel
from app.models.executive import BudgetEnvelope
from app.models.hr import Offer, SalaryBand


@dataclass
class OfferCheck:
    status: str
    risk_class: str = "R3_EXTERNAL_IRREVERSIBLE"
    required_keys: int = 1


class OfferPolicy:
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def active_band(self, requisition_id: str, currency: str, now: datetime | None = None) -> SalaryBand | None:
        now = _as_utc(now or datetime.now(timezone.utc))
        rows = (
            self.db.query(SalaryBand)
            .filter_by(tenant_id=self.tenant_id, requisition_id=requisition_id, currency=currency)
            .all()
        )
        for row in rows:
            start = _as_utc(row.effective_from)
            end = _as_utc(row.effective_to)
            if start and start <= now and (end is None or now < end):
                return row
        return None

    def check(
        self,
        offer: Offer,
        dry: bool,
        envelope_id: str | None = None,
        workflow_id: str | None = None,
        task_id: str | None = None,
        idempotency_key: str | None = None,
        hold_until: datetime | None = None,
    ) -> OfferCheck:
        amount = Decimal(str(offer.base_amount))
        if amount <= 0:
            return OfferCheck(status="non_positive_amount")
        band = self._band_for_offer(offer)
        if band is None:
            return OfferCheck(status="band_not_configured")
        offer.band_id = band.id
        inside = Decimal(str(band.min_amount)) <= amount <= Decimal(str(band.max_amount))
        risk = "R3_EXTERNAL_IRREVERSIBLE" if inside else "R4_FINANCIAL_CRITICAL"
        keys = 1 if inside else 2
        if dry:
            return OfferCheck(status="ok", risk_class=risk, required_keys=keys)
        if not envelope_id or not workflow_id or not task_id or not idempotency_key or not hold_until:
            return OfferCheck(status="budget_unavailable", risk_class=risk, required_keys=keys)
        kernel = DeterministicGovernanceKernel(self.db, self.tenant_id)
        reserved = kernel.reserve_envelope(envelope_id, workflow_id, task_id, amount, idempotency_key, hold_until)
        if reserved is None:
            return OfferCheck(status="budget_unavailable", risk_class=risk, required_keys=keys)
        return OfferCheck(status="ok", risk_class=risk, required_keys=keys)

    def _band_for_offer(self, offer: Offer) -> SalaryBand | None:
        from app.models.hr import Application
        application = self.db.query(Application).filter_by(id=offer.application_id, tenant_id=self.tenant_id).first()
        if not application:
            return None
        return self.active_band(application.requisition_id, offer.currency)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def hr_envelope(db: Session, tenant_id: str, currency: str) -> BudgetEnvelope | None:
    return (
        db.query(BudgetEnvelope)
        .filter_by(tenant_id=tenant_id, department="hr", currency=currency, is_active=True)
        .first()
    )
