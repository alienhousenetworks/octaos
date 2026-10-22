"""Payment reconciliation service with strict idempotency and deposit verification."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.real_estate import (
    RealEstatePaymentTransaction,
    RealEstateBooking,
    RealEstateUnitHold,
)


class PaymentReconciliationService:
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def list_transactions(
        self,
        booking_id: Optional[str] = None,
        lead_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List verified and pending payment transactions."""
        query = self.db.query(RealEstatePaymentTransaction).filter(
            RealEstatePaymentTransaction.tenant_id == self.tenant_id
        )
        if booking_id:
            query = query.filter(RealEstatePaymentTransaction.booking_id == booking_id)
        if lead_id:
            query = query.filter(RealEstatePaymentTransaction.lead_id == lead_id)
        if status:
            query = query.filter(RealEstatePaymentTransaction.status == status)

        txs = query.order_by(RealEstatePaymentTransaction.created_at.desc()).all()
        return [
            {
                "id": t.id,
                "booking_id": t.booking_id,
                "hold_id": t.hold_id,
                "lead_id": t.lead_id,
                "transaction_type": t.transaction_type,
                "amount": t.amount,
                "currency": t.currency,
                "status": t.status,
                "payment_method": t.payment_method,
                "payment_reference": t.payment_reference,
                "idempotency_key": t.idempotency_key,
                "proof_document_url": t.proof_document_url,
                "verified_by_user_id": t.verified_by_user_id,
                "verified_at": t.verified_at.isoformat() if t.verified_at else None,
                "created_at": t.created_at.isoformat(),
            }
            for t in txs
        ]

    def record_payment_event(
        self,
        idempotency_key: str,
        lead_id: str,
        amount: float,
        payment_method: str,
        payment_reference: Optional[str] = None,
        transaction_type: str = "token_deposit",
        booking_id: Optional[str] = None,
        hold_id: Optional[str] = None,
        proof_document_url: Optional[str] = None,
        auto_verify: bool = False,
        verified_by_user_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Record a payment transaction with idempotency deduplication.
        If auto_verify is true (e.g. signed gateway webhook), immediately reconciles booking balances.
        """
        # Idempotency check
        existing = (
            self.db.query(RealEstatePaymentTransaction)
            .filter(
                RealEstatePaymentTransaction.idempotency_key == idempotency_key,
                RealEstatePaymentTransaction.tenant_id == self.tenant_id,
            )
            .first()
        )
        if existing:
            return {
                "transaction_id": existing.id,
                "status": existing.status,
                "amount": existing.amount,
                "idempotent_duplicate": True,
            }

        now = datetime.now(timezone.utc)
        initial_status = "verified" if auto_verify else "pending"

        tx = RealEstatePaymentTransaction(
            tenant_id=self.tenant_id,
            booking_id=booking_id,
            hold_id=hold_id,
            lead_id=lead_id,
            transaction_type=transaction_type,
            amount=amount,
            currency="INR",
            status=initial_status,
            payment_method=payment_method,
            payment_reference=payment_reference,
            idempotency_key=idempotency_key,
            proof_document_url=proof_document_url,
            verified_by_user_id=verified_by_user_id if auto_verify else None,
            verified_at=now if auto_verify else None,
            notes=notes,
        )
        self.db.add(tx)

        # Reconcile booking if verified
        if auto_verify and booking_id:
            self._apply_payment_to_booking(booking_id, amount)

        # Reconcile hold if hold_id provided
        if auto_verify and hold_id:
            hold = self.db.query(RealEstateUnitHold).filter(RealEstateUnitHold.id == hold_id).first()
            if hold:
                hold.deposit_verified = True
                hold.deposit_amount = (hold.deposit_amount or 0.0) + amount
                hold.status = "confirmed"

        self.db.commit()
        self.db.refresh(tx)

        return {
            "transaction_id": tx.id,
            "status": tx.status,
            "amount": tx.amount,
            "payment_reference": tx.payment_reference,
            "idempotent_duplicate": False,
        }

    def verify_transaction(self, transaction_id: str, verified_by_user_id: str) -> Dict[str, Any]:
        """Manually verify a pending payment transaction (e.g., finance approval of wire/cheque)."""
        tx = (
            self.db.query(RealEstatePaymentTransaction)
            .filter(
                RealEstatePaymentTransaction.id == transaction_id,
                RealEstatePaymentTransaction.tenant_id == self.tenant_id,
            )
            .with_for_update()
            .first()
        )
        if not tx:
            raise HTTPException(status_code=404, detail="Transaction not found")

        if tx.status == "verified":
            return {"transaction_id": tx.id, "status": "verified", "already_verified": True}

        tx.status = "verified"
        tx.verified_by_user_id = verified_by_user_id
        tx.verified_at = datetime.now(timezone.utc)

        if tx.booking_id:
            self._apply_payment_to_booking(tx.booking_id, tx.amount)

        if tx.hold_id:
            hold = self.db.query(RealEstateUnitHold).filter(RealEstateUnitHold.id == tx.hold_id).first()
            if hold:
                hold.deposit_verified = True
                hold.deposit_amount = (hold.deposit_amount or 0.0) + tx.amount
                hold.status = "confirmed"

        self.db.commit()
        return {"transaction_id": tx.id, "status": "verified", "amount": tx.amount}

    def _apply_payment_to_booking(self, booking_id: str, amount: float) -> None:
        booking = (
            self.db.query(RealEstateBooking)
            .filter(RealEstateBooking.id == booking_id, RealEstateBooking.tenant_id == self.tenant_id)
            .first()
        )
        if not booking:
            return

        booking.deposit_paid = (booking.deposit_paid or 0.0) + amount
        booking.balance_due = max(0.0, (booking.agreed_price or 0.0) - booking.deposit_paid)
        if booking.status == "pending_payment" and booking.deposit_paid > 0:
            booking.status = "payment_verified"
