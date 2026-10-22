"""Commission ledger service managing multi-milestone broker payouts and approvals."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.real_estate import (
    RealEstateCommissionLedger,
    RealEstateBooking,
    RealEstateBrokerAttribution,
)


class CommissionLedgerService:
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def list_ledgers(
        self,
        booking_id: Optional[str] = None,
        broker_attribution_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List commission milestone entries."""
        query = self.db.query(RealEstateCommissionLedger).filter(
            RealEstateCommissionLedger.tenant_id == self.tenant_id
        )
        if booking_id:
            query = query.filter(RealEstateCommissionLedger.booking_id == booking_id)
        if broker_attribution_id:
            query = query.filter(RealEstateCommissionLedger.broker_attribution_id == broker_attribution_id)
        if status:
            query = query.filter(RealEstateCommissionLedger.status == status)

        entries = query.order_by(RealEstateCommissionLedger.created_at.desc()).all()
        return [
            {
                "id": e.id,
                "booking_id": e.booking_id,
                "broker_attribution_id": e.broker_attribution_id,
                "total_commission_amount": e.total_commission_amount,
                "milestone_number": e.milestone_number,
                "milestone_name": e.milestone_name,
                "payable_amount": e.payable_amount,
                "status": e.status,
                "due_date": e.due_date.isoformat() if e.due_date else None,
                "paid_at": e.paid_at.isoformat() if e.paid_at else None,
                "payout_reference": e.payout_reference,
                "created_at": e.created_at.isoformat(),
            }
            for e in entries
        ]

    def accrue_booking_commissions(self, booking_id: str) -> List[Dict[str, Any]]:
        """
        Creates milestone-based commission ledger entries upon booking creation.
        Splits into:
          Milestone 1 (25%): Token Deposit & Verification
          Milestone 2 (75%): Agreement Registration & Final Handover
        """
        booking = (
            self.db.query(RealEstateBooking)
            .filter(RealEstateBooking.id == booking_id, RealEstateBooking.tenant_id == self.tenant_id)
            .first()
        )
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")

        # Check existing ledgers
        existing = (
            self.db.query(RealEstateCommissionLedger)
            .filter(RealEstateCommissionLedger.booking_id == booking_id, RealEstateCommissionLedger.tenant_id == self.tenant_id)
            .first()
        )
        if existing:
            return self.list_ledgers(booking_id=booking_id)

        # Look up broker attribution for the lead
        attribution = (
            self.db.query(RealEstateBrokerAttribution)
            .filter(RealEstateBrokerAttribution.lead_id == booking.lead_id, RealEstateBrokerAttribution.tenant_id == self.tenant_id)
            .first()
        )
        if not attribution:
            return []  # Direct deal with no broker attribution

        pct = attribution.commission_pct or 2.0
        total_commission = (booking.agreed_price * pct) / 100.0

        m1_amount = round(total_commission * 0.25, 2)
        m2_amount = round(total_commission - m1_amount, 2)

        m1 = RealEstateCommissionLedger(
            tenant_id=self.tenant_id,
            booking_id=booking.id,
            broker_attribution_id=attribution.id,
            total_commission_amount=total_commission,
            milestone_number=1,
            milestone_name="Token Deposit Verified (25%)",
            payable_amount=m1_amount,
            status="approved" if booking.status == "payment_verified" else "accrued",
        )

        m2 = RealEstateCommissionLedger(
            tenant_id=self.tenant_id,
            booking_id=booking.id,
            broker_attribution_id=attribution.id,
            total_commission_amount=total_commission,
            milestone_number=2,
            milestone_name="Sale Agreement Registered (75%)",
            payable_amount=m2_amount,
            status="accrued",
        )

        self.db.add_all([m1, m2])
        self.db.commit()

        return self.list_ledgers(booking_id=booking_id)

    def record_payout(self, ledger_id: str, payout_reference: str, approved_by_user_id: str) -> Dict[str, Any]:
        """Disburse commission payout and audit payment reference."""
        entry = (
            self.db.query(RealEstateCommissionLedger)
            .filter(
                RealEstateCommissionLedger.id == ledger_id,
                RealEstateCommissionLedger.tenant_id == self.tenant_id,
            )
            .with_for_update()
            .first()
        )
        if not entry:
            raise HTTPException(status_code=404, detail="Commission entry not found")

        entry.status = "paid"
        entry.paid_at = datetime.now(timezone.utc)
        entry.payout_reference = payout_reference
        entry.approved_by_user_id = approved_by_user_id

        self.db.commit()
        return {
            "id": entry.id,
            "status": "paid",
            "payable_amount": entry.payable_amount,
            "payout_reference": payout_reference,
            "paid_at": entry.paid_at.isoformat(),
        }

    def reverse_commissions_for_booking(self, booking_id: str, reason: str = "Booking cancelled") -> int:
        """Reverse all unpaid commissions if booking is cancelled."""
        unpaid = (
            self.db.query(RealEstateCommissionLedger)
            .filter(
                RealEstateCommissionLedger.booking_id == booking_id,
                RealEstateCommissionLedger.tenant_id == self.tenant_id,
                RealEstateCommissionLedger.status.in_(["accrued", "approved"]),
            )
            .all()
        )
        for e in unpaid:
            e.status = "reversed"

        if unpaid:
            self.db.commit()
        return len(unpaid)
