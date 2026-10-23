"""Booking lifecycle management service with transactional inventory locking."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.real_estate import (
    RealEstateBooking,
    RealEstateUnit,
    RealEstateUnitHold,
    RealEstateProject,
)
from app.services.sales_os.real_estate.concurrency import inventory_unit_lock


class BookingService:
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def list_bookings(
        self,
        project_id: Optional[str] = None,
        lead_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List tenant-scoped bookings with optional filters."""
        query = self.db.query(RealEstateBooking).filter(
            RealEstateBooking.tenant_id == self.tenant_id
        )
        if project_id:
            query = query.filter(RealEstateBooking.project_id == project_id)
        if lead_id:
            query = query.filter(RealEstateBooking.lead_id == lead_id)
        if status:
            query = query.filter(RealEstateBooking.status == status)

        bookings = query.order_by(RealEstateBooking.created_at.desc()).all()
        return [
            {
                "id": b.id,
                "booking_reference": b.booking_reference,
                "unit_id": b.unit_id,
                "project_id": b.project_id,
                "lead_id": b.lead_id,
                "hold_id": b.hold_id,
                "base_price": b.base_price,
                "agreed_price": b.agreed_price,
                "deposit_paid": b.deposit_paid,
                "balance_due": b.balance_due,
                "currency": b.currency,
                "status": b.status,
                "buyer_legal_name": b.buyer_legal_name,
                "buyer_id_number": b.buyer_id_number,
                "co_buyers": b.co_buyers or [],
                "payment_plan": b.payment_plan or {},
                "sales_rep_id": b.sales_rep_id,
                "approved_at": b.approved_at.isoformat() if b.approved_at else None,
                "created_at": b.created_at.isoformat() if b.created_at else None,
            }
            for b in bookings
        ]

    def get_booking(self, booking_id: str) -> Dict[str, Any]:
        """Fetch a specific booking record."""
        b = (
            self.db.query(RealEstateBooking)
            .filter(
                RealEstateBooking.id == booking_id,
                RealEstateBooking.tenant_id == self.tenant_id,
            )
            .first()
        )
        if not b:
            raise HTTPException(status_code=404, detail="Booking not found")

        unit = self.db.query(RealEstateUnit).filter(RealEstateUnit.id == b.unit_id).first()
        project = self.db.query(RealEstateProject).filter(RealEstateProject.id == b.project_id).first()

        return {
            "id": b.id,
            "booking_reference": b.booking_reference,
            "unit_id": b.unit_id,
            "unit_number": unit.unit_number if unit else None,
            "unit_type": unit.unit_type if unit else None,
            "project_id": b.project_id,
            "project_name": project.name if project else None,
            "lead_id": b.lead_id,
            "hold_id": b.hold_id,
            "base_price": b.base_price,
            "agreed_price": b.agreed_price,
            "deposit_paid": b.deposit_paid,
            "balance_due": b.balance_due,
            "currency": b.currency,
            "status": b.status,
            "buyer_legal_name": b.buyer_legal_name,
            "buyer_id_number": b.buyer_id_number,
            "co_buyers": b.co_buyers or [],
            "payment_plan": b.payment_plan or {},
            "sales_rep_id": b.sales_rep_id,
            "approved_by_user_id": b.approved_by_user_id,
            "approved_at": b.approved_at.isoformat() if b.approved_at else None,
            "cancellation_reason": b.cancellation_reason,
            "created_at": b.created_at.isoformat() if b.created_at else None,
        }

    def create_booking_application(
        self,
        lead_id: str,
        unit_id: str,
        agreed_price: float,
        buyer_legal_name: str,
        buyer_id_number: Optional[str] = None,
        co_buyers: Optional[List[Dict[str, Any]]] = None,
        payment_plan: Optional[Dict[str, Any]] = None,
        deposit_paid: float = 0.0,
        sales_rep_id: Optional[str] = None,
        hold_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Creates an authoritative booking application.
        Atomically locks unit row using distributed lock and transitions unit state to 'booked'.
        """
        with inventory_unit_lock(unit_id):
            unit = (
                self.db.query(RealEstateUnit)
                .filter(
                    RealEstateUnit.id == unit_id,
                    RealEstateUnit.tenant_id == self.tenant_id,
                )
                .with_for_update()
                .first()
            )
            if not unit:
                raise HTTPException(status_code=404, detail="Unit not found")

            # Check existing active hold
            if hold_id:
                hold = (
                    self.db.query(RealEstateUnitHold)
                    .filter(
                        RealEstateUnitHold.id == hold_id,
                        RealEstateUnitHold.tenant_id == self.tenant_id,
                        RealEstateUnitHold.unit_id == unit.id,
                    )
                    .first()
                )
                if not hold:
                    raise HTTPException(status_code=404, detail="Specified hold not found for unit")
                if hold.lead_id != lead_id:
                    raise HTTPException(status_code=403, detail="Hold belongs to another prospective inquiry")
            else:
                # If not held, unit must be available
                if unit.status != "available":
                    raise HTTPException(
                        status_code=409,
                        detail=f"Unit {unit.unit_number} is currently {unit.status.replace('_', ' ')} and cannot be booked directly.",
                    )

            year = datetime.now(timezone.utc).year
            unique_suffix = str(uuid.uuid4())[:6].upper()
            ref = f"BK-{year}-{unique_suffix}"

            balance_due = max(0.0, agreed_price - deposit_paid)
            initial_status = "payment_verified" if deposit_paid > 0 else "pending_payment"

            booking = RealEstateBooking(
                tenant_id=self.tenant_id,
                booking_reference=ref,
                unit_id=unit.id,
                project_id=unit.project_id,
                lead_id=lead_id,
                hold_id=hold_id,
                base_price=unit.base_price,
                agreed_price=agreed_price,
                deposit_paid=deposit_paid,
                balance_due=balance_due,
                currency="INR",
                status=initial_status,
                buyer_legal_name=buyer_legal_name,
                buyer_id_number=buyer_id_number,
                co_buyers=co_buyers or [],
                payment_plan=payment_plan or {},
                sales_rep_id=sales_rep_id,
            )

            # Transition unit to booked
            unit.status = "booked"
            unit.version += 1

            # If hold was used, mark it converted
            if hold_id:
                hold = self.db.query(RealEstateUnitHold).filter(RealEstateUnitHold.id == hold_id).first()
                if hold:
                    hold.status = "converted_to_booking"

            # Update project unit counts if holding didn't already decrement
            project = self.db.query(RealEstateProject).filter(RealEstateProject.id == unit.project_id).first()
            if project and not hold_id and project.available_units and project.available_units > 0:
                project.available_units -= 1

            self.db.add(booking)
            self.db.commit()
            self.db.refresh(booking)

            return {
                "id": booking.id,
                "booking_reference": booking.booking_reference,
                "unit_id": unit.id,
                "unit_number": unit.unit_number,
                "agreed_price": booking.agreed_price,
                "deposit_paid": booking.deposit_paid,
                "balance_due": booking.balance_due,
                "status": booking.status,
                "buyer_legal_name": booking.buyer_legal_name,
                "created_at": booking.created_at.isoformat(),
            }


    def cancel_booking(self, booking_id: str, reason: str, refund_amount: float = 0.0) -> Dict[str, Any]:
        """
        Cancels an active booking, audits reason, and safely reverts the unit to 'available'.
        """
        booking = (
            self.db.query(RealEstateBooking)
            .filter(
                RealEstateBooking.id == booking_id,
                RealEstateBooking.tenant_id == self.tenant_id,
            )
            .with_for_update()
            .first()
        )
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")

        if booking.status in ("cancelled", "refunded"):
            raise HTTPException(status_code=400, detail="Booking is already cancelled or refunded")

        booking.status = "cancelled"
        booking.cancellation_reason = reason

        # Free the unit
        unit = self.db.query(RealEstateUnit).filter(RealEstateUnit.id == booking.unit_id).first()
        if unit:
            unit.status = "available"
            unit.version += 1
            project = self.db.query(RealEstateProject).filter(RealEstateProject.id == unit.project_id).first()
            if project:
                project.available_units = (project.available_units or 0) + 1

        self.db.commit()
        return {
            "booking_id": booking.id,
            "booking_reference": booking.booking_reference,
            "status": "cancelled",
            "unit_status": "available",
            "refund_amount": refund_amount,
            "cancellation_reason": reason,
        }
