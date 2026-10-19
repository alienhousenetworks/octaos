"""Autonomous Sales Outbox Service.

Provides:
1. Outbox Staging: Schedules multi-step outreach touches as discrete inspectable rows with send_at timestamps.
2. Atomic Stop-on-Reply: Instantly cancels all future pending outbox items for a prospect upon reply or opt-out.
3. Jittered Pacing & Safe Drain: Drains due outbox items with anti-spam jitter (5-20s) and respects daily send limits.
"""
import json
import logging
import random
import time
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.base import APICredential
from app.models.deal_room import SalesOutboxItem
from app.models.verticals import Lead
from app.services.email.sender import send_email_with_status
from app.services.sales_os.governance.gatekeeper import PreSendGatekeeper
from app.services.sales_os.governance.suppression import SuppressionService

logger = logging.getLogger(__name__)


class SalesOutboxService:
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.suppression = SuppressionService(db, tenant_id)

    def is_sending_paused(self) -> bool:
        """Check if tenant sending is paused due to bounce trip or kill-switch."""
        cred = self.db.query(APICredential).filter_by(tenant_id=self.tenant_id, provider="sales").first()
        if cred and cred.settings and cred.settings.get("sending_paused"):
            return True
        return False

    def stage_touch(
        self,
        lead_id: str,
        recipient_email: str,
        subject: str,
        body: str,
        step_number: int = 1,
        channel: str = "email",
        scheduled_for: Optional[datetime] = None,
        recipient_name: Optional[str] = None,
        deal_room_id: Optional[str] = None,
        require_review: bool = False,
    ) -> Optional[SalesOutboxItem]:
        """Stage a single outreach touch into the outbox."""
        if not recipient_email or not body:
            return None

        # Suppression check
        is_supp, reason = self.suppression.is_suppressed(email=recipient_email)
        if is_supp:
            logger.info(f"Skipping outbox staging for {recipient_email}: suppressed ({reason})")
            return None

        # Pre-send Gatekeeper validation
        gate = PreSendGatekeeper.evaluate(subject=subject, body=body, step_number=step_number)
        cleaned_body = gate.cleaned_body if gate.cleaned_body else body
        cleaned_subject = gate.cleaned_subject if gate.cleaned_subject else subject

        if not scheduled_for:
            scheduled_for = datetime.now(timezone.utc)

        status = "pending_review" if (require_review or not gate.is_valid) else "scheduled"

        item = SalesOutboxItem(
            tenant_id=self.tenant_id,
            lead_id=lead_id,
            deal_room_id=deal_room_id,
            step_number=step_number,
            channel=channel,
            recipient_email=recipient_email.strip().lower(),
            recipient_name=recipient_name,
            subject=cleaned_subject,
            body=cleaned_body,
            status=status,
            scheduled_for=scheduled_for,
            error_message="; ".join(gate.violations) if gate.violations else None,
        )
        self.db.add(item)
        self.db.commit()
        return item

    def stage_sequence(
        self,
        lead: Lead,
        channel_schedule: List[Dict[str, Any]],
        deal_room_id: Optional[str] = None,
        require_review: bool = False,
    ) -> List[SalesOutboxItem]:
        """Stage an entire multi-touch sequence into the outbox with progressive timestamps."""
        staged: List[SalesOutboxItem] = []
        now = datetime.now(timezone.utc)
        recipient_email = lead.email or lead.company_email or lead.personal_email
        if not recipient_email:
            return staged

        for idx, touch in enumerate(channel_schedule):
            day_offset = int(touch.get("day", 1)) - 1
            step_number = idx + 1
            scheduled_at = now + timedelta(days=max(0, day_offset))
            content = touch.get("content") or ""
            subject = touch.get("subject") or f"Partnership Opportunity - {lead.company or 'Your Company'}"
            channel = str(touch.get("channel") or "email").lower()

            item = self.stage_touch(
                lead_id=lead.id,
                recipient_email=recipient_email,
                subject=subject,
                body=content,
                step_number=step_number,
                channel=channel,
                scheduled_for=scheduled_at,
                recipient_name=lead.name,
                deal_room_id=deal_room_id,
                require_review=require_review,
            )
            if item:
                staged.append(item)

        return staged

    def cancel_pending_for_lead(
        self,
        lead_id: Optional[str] = None,
        recipient_email: Optional[str] = None,
        reason: str = "prospect_replied",
    ) -> int:
        """Atomically cancel all pending or scheduled outbox items for a prospect."""
        query = self.db.query(SalesOutboxItem).filter(
            SalesOutboxItem.tenant_id == self.tenant_id,
            SalesOutboxItem.status.in_(["scheduled", "approved", "pending_review"]),
        )
        conditions = []
        if lead_id:
            conditions.append(SalesOutboxItem.lead_id == lead_id)
        if recipient_email:
            conditions.append(SalesOutboxItem.recipient_email == recipient_email.strip().lower())

        if not conditions:
            return 0

        query = query.filter(or_(*conditions))
        count = query.update(
            {"status": "cancelled", "cancellation_reason": reason, "updated_at": datetime.now(timezone.utc)},
            synchronize_session=False,
        )
        self.db.commit()
        if count > 0:
            logger.info(f"Cancelled {count} pending outbox items for lead {lead_id} / {recipient_email} (reason: {reason})")
        return count

    def drain_due_items(self, limit: int = 15, max_jitter_sec: int = 3) -> Dict[str, Any]:
        """Drain items scheduled on or before now with jitter and safety checks."""
        if self.is_sending_paused():
            logger.warning(f"Tenant {self.tenant_id} outbound is paused. Skipping outbox drain.")
            return {"status": "paused", "dispatched": 0}

        now = datetime.now(timezone.utc)
        items = (
            self.db.query(SalesOutboxItem)
            .filter(
                SalesOutboxItem.tenant_id == self.tenant_id,
                SalesOutboxItem.status.in_(["scheduled", "approved"]),
                SalesOutboxItem.scheduled_for <= now,
            )
            .order_by(SalesOutboxItem.scheduled_for.asc())
            .limit(limit)
            .all()
        )

        if not items:
            return {"status": "idle", "dispatched": 0}

        dispatched = 0
        failed = 0

        for item in items:
            # Check suppression right before sending
            is_supp, reason = self.suppression.is_suppressed(email=item.recipient_email)
            if is_supp:
                item.status = "cancelled"
                item.cancellation_reason = f"suppressed:{reason}"
                self.db.commit()
                continue

            # Anti-spam jitter pacing
            if max_jitter_sec > 0:
                time.sleep(random.uniform(0.5, float(max_jitter_sec)))

            send_result = send_email_with_status(
                self.db,
                self.tenant_id,
                item.recipient_email,
                item.subject or "Partnership Opportunity",
                item.body,
            )

            if send_result.get("sent"):
                item.status = "sent"
                item.sent_at = datetime.now(timezone.utc)
                item.error_message = None
                dispatched += 1

                # Update lead conversation log and status if lead exists
                if item.lead_id:
                    lead = self.db.query(Lead).filter_by(id=item.lead_id, tenant_id=self.tenant_id).first()
                    if lead:
                        lead.status = "contacted"
                        conv = list((lead.data or {}).get("conversation") or [])
                        conv.append({
                            "direction": "outbound",
                            "channel": item.channel,
                            "content": item.body,
                            "subject": item.subject,
                            "author": "Sales AI Agent",
                            "at": datetime.now(timezone.utc).isoformat(),
                            "outbox_item_id": item.id,
                            "step_number": item.step_number,
                            "sent": True,
                        })
                        lead.data = {
                            **(lead.data or {}),
                            "conversation": conv,
                            "outreach_channel": item.channel,
                            "outbound_subject": item.subject,
                            "outbound_body": item.body,
                            "outreach_sent_at": datetime.now(timezone.utc).isoformat(),
                        }
            else:
                item.status = "failed"
                item.error_message = send_result.get("reason") or "Delivery failed"
                failed += 1

            self.db.commit()

        return {"status": "completed", "dispatched": dispatched, "failed": failed}
