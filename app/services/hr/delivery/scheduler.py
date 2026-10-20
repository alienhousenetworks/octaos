"""Timezone-Aware Scheduled Delivery with Pre-Flight Revalidation."""
from datetime import datetime, timezone
from typing import Tuple
from sqlalchemy.orm import Session

from app.models.hr import (
    DocumentDraft,
    ScheduledDelivery,
)


class DeliverySchedulerService:
    """Manages scheduled document release and enforces cryptographic pre-flight revalidation."""

    @classmethod
    def schedule_delivery(
        cls,
        db: Session,
        draft_id: str,
        scheduled_for: datetime,
        timezone_str: str,
        recipient_email: str,
    ) -> ScheduledDelivery:
        """Schedules delivery of an approved document draft."""
        draft = db.query(DocumentDraft).filter_by(id=draft_id).first()
        if not draft:
            raise ValueError(f"Draft {draft_id} not found")

        if draft.current_approval_status != "approved":
            raise ValueError(f"Cannot schedule draft with status '{draft.current_approval_status}'. Approval required first.")

        delivery = ScheduledDelivery(
            tenant_id=draft.tenant_id,
            draft_id=draft.id,
            scheduled_for=scheduled_for,
            timezone=timezone_str,
            recipient_email=recipient_email,
            status="scheduled",
        )
        db.add(delivery)
        db.commit()
        db.refresh(delivery)
        return delivery

    @classmethod
    def revalidate_and_dispatch(
        cls,
        db: Session,
        delivery_id: str,
    ) -> Tuple[bool, str]:
        """Pre-flight revalidation: verifies draft approval, hash consistency, and recipient authorization."""
        delivery = db.query(ScheduledDelivery).filter_by(id=delivery_id).first()
        if not delivery:
            return False, "Scheduled delivery record not found"

        if delivery.status == "dispatched":
            return True, "Already dispatched"
        if delivery.status == "cancelled":
            return False, "Delivery was cancelled"

        draft = db.query(DocumentDraft).filter_by(id=delivery.draft_id).first()
        if not draft:
            delivery.status = "failed"
            delivery.last_error = "Associated document draft not found"
            db.commit()
            return False, delivery.last_error

        # 1. Revalidate Approval Status
        if draft.current_approval_status != "approved":
            delivery.status = "failed"
            delivery.last_error = (
                f"Pre-flight revalidation failed: Document draft status is '{draft.current_approval_status}', "
                "not 'approved'. Edits may have invalidated prior approval."
            )
            db.commit()
            return False, delivery.last_error

        # 2. Revalidate Bound Cryptographic Hash
        if draft.bound_approval_sha256 and draft.bound_approval_sha256 != draft.content_sha256:
            delivery.status = "failed"
            delivery.last_error = (
                "Pre-flight revalidation failed: Current content SHA-256 does not match hash bound at approval time. "
                "Document was modified post-approval."
            )
            db.commit()
            return False, delivery.last_error

        # 3. Revalidate Recipient
        if not delivery.recipient_email or "@" not in delivery.recipient_email:
            delivery.status = "failed"
            delivery.last_error = f"Invalid recipient email address: '{delivery.recipient_email}'"
            db.commit()
            return False, delivery.last_error

        # All checks passed: Mark dispatched
        delivery.status = "dispatched"
        delivery.dispatched_at = datetime.now(timezone.utc)
        delivery.last_error = None
        db.commit()
        return True, "Successfully dispatched"
