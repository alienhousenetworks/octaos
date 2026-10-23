"""Durable Cadence Runner Service for Enterprise Sales AI.

Orchestrates multi-channel cadences across Email, WhatsApp, and LinkedIn:
1. Detects pending cadence touches across both discrete SalesOutboxItem rows and Lead outreach_schedules.
2. Evaluates pre-send gates (SuppressionService, frequency caps, active opt-outs, and inbound replies).
3. Executes real delivery via multi-channel dispatchers (Gmail/SMTP, WhatsApp Cloud API, LinkedIn HITL).
4. Atomically halts and cancels future touches upon prospect reply, meeting booking, or explicit opt-out.
5. Records durable AgentRun and AgentTask execution records via AgentRuntime kernel.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.agent_runtime import AgentRun, AgentTask
from app.models.base import Tenant, APICredential
from app.models.deal_room import DealRoom, SalesOutboxItem
from app.models.verticals import Lead
from app.services.sales.outbox_service import SalesOutboxService
from app.services.sales.touch_dispatcher import dispatch_sales_touch
from app.services.sales_os.governance.suppression import SuppressionService

logger = logging.getLogger(__name__)


class DurableCadenceRunner:
    """Enterprise-grade durable cadence execution service."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.suppression = SuppressionService(db, tenant_id)
        self.outbox = SalesOutboxService(db, tenant_id)

    def is_sending_paused(self) -> bool:
        """Check if tenant sending is paused by safety switch."""
        return self.outbox.is_sending_paused()

    def get_cadence_stats(self) -> Dict[str, Any]:
        """Calculates live cadence execution metrics for this tenant."""
        now = datetime.now(timezone.utc)
        leads = self.db.query(Lead).filter(
            Lead.tenant_id == self.tenant_id,
            Lead.status.in_(["contacted", "in_cadence", "qualified", "replied"]),
        ).all()

        enrolled_count = 0
        pending_touches_count = 0
        completed_touches_count = 0
        suppressed_count = 0
        halted_replies_count = 0

        for lead in leads:
            data = lead.data or {}
            schedule = list(data.get("outreach_schedule") or [])
            if schedule:
                enrolled_count += 1
                for step in schedule:
                    st = step.get("status")
                    if st == "pending":
                        pending_touches_count += 1
                    elif st == "sent":
                        completed_touches_count += 1
                    elif st == "suppressed":
                        suppressed_count += 1
                    elif st in ("halted_reply_received", "cancelled"):
                        halted_replies_count += 1

        outbox_pending = self.db.query(SalesOutboxItem).filter(
            SalesOutboxItem.tenant_id == self.tenant_id,
            SalesOutboxItem.status.in_(["scheduled", "pending_review"]),
        ).count()

        outbox_sent = self.db.query(SalesOutboxItem).filter(
            SalesOutboxItem.tenant_id == self.tenant_id,
            SalesOutboxItem.status == "sent",
        ).count()

        return {
            "tenant_id": self.tenant_id,
            "active_enrolled_leads": enrolled_count,
            "pending_touches": pending_touches_count + outbox_pending,
            "completed_touches": completed_touches_count + outbox_sent,
            "suppressed_touches": suppressed_count,
            "halted_on_reply": halted_replies_count,
            "sending_paused": self.is_sending_paused(),
            "checked_at": now.isoformat(),
        }

    def run_tenant_cadence(self, max_touches: int = 50) -> Dict[str, Any]:
        """
        Executes pending touches across all eligible leads for the tenant.
        Ensures strict idempotency and durable audit logging.
        """
        now = datetime.now(timezone.utc)
        run_record = AgentRun(
            tenant_id=self.tenant_id,
            agent_id="agent.cadence_optimizer",
            goal=f"Execute scheduled sales cadence touches (limit {max_touches})",
            status="running",
            started_at=now,
            input_payload={"limit": max_touches, "started_at": now.isoformat()},
        )
        self.db.add(run_record)
        self.db.commit()
        self.db.refresh(run_record)

        stats = {
            "run_id": run_record.id,
            "evaluated_leads": 0,
            "touches_sent": 0,
            "touches_suppressed": 0,
            "cadences_halted_on_reply": 0,
            "action_required": 0,
            "failures": 0,
            "details": [],
        }

        if self.is_sending_paused():
            run_record.status = "completed"
            run_record.finished_at = datetime.now(timezone.utc)
            run_record.output_payload = {
                "reason": "Sending is paused via tenant safety kill-switch",
            }
            self.db.commit()
            stats["details"].append("Sending is currently paused for this tenant.")
            return stats

        try:
            # 1. Drain due outbox items
            try:
                drained = self.outbox.drain_due_items(limit=max_touches // 2, max_jitter_sec=1)
                # SalesOutboxService historically returned `dispatched`; it
                # now also exposes `sent` for compatibility. Prefer the
                # explicit sent count so cadence limits and audit metrics do
                # not silently under-count outbox deliveries.
                stats["touches_sent"] += drained.get("sent", drained.get("dispatched", 0))
                stats["failures"] += drained.get("failed", 0)
                stats["touches_suppressed"] += drained.get("suppressed", 0)
            except Exception as drain_err:
                logger.error(f"Error draining outbox in DurableCadenceRunner: {drain_err}", exc_info=True)

            # 2. Process pending Lead.data["outreach_schedule"]
            leads = (
                self.db.query(Lead)
                .filter(
                    Lead.tenant_id == self.tenant_id,
                    Lead.status.in_(["contacted", "in_cadence", "qualified", "replied"]),
                )
                .all()
            )

            budget = max_touches - stats["touches_sent"]

            for lead in leads:
                if budget <= 0:
                    break

                stats["evaluated_leads"] += 1
                data = dict(lead.data or {})
                schedule = list(data.get("outreach_schedule") or [])
                if not schedule:
                    continue

                # Check if lead has already replied, booked meeting, or closed
                has_replied = lead.status in ("replied", "meeting_scheduled", "closed_won", "closed_lost")
                if not has_replied:
                    # Check conversation array for inbound reply
                    convs = data.get("conversations") or data.get("conversation") or []
                    for msg in convs:
                        if isinstance(msg, dict) and msg.get("direction") == "inbound":
                            has_replied = True
                            lead.status = "replied"
                            break

                if has_replied:
                    # Automatically halt all remaining pending steps
                    halted_any = False
                    for step in schedule:
                        if step.get("status") == "pending":
                            step["status"] = "halted_reply_received"
                            step["halted_at"] = now.isoformat()
                            halted_any = True

                    if halted_any:
                        stats["cadences_halted_on_reply"] += 1
                        self.outbox.cancel_pending_for_lead(lead_id=lead.id, reason="prospect_replied")
                        data["outreach_schedule"] = schedule
                        lead.data = data
                        self.db.commit()
                    continue

                # Calculate days elapsed since initial touch or creation
                sent_at_str = data.get("outreach_sent_at")
                if sent_at_str:
                    try:
                        sent_at = datetime.fromisoformat(sent_at_str)
                        if sent_at.tzinfo is None:
                            sent_at = sent_at.replace(tzinfo=timezone.utc)
                    except Exception:
                        sent_at = lead.created_at or now
                else:
                    sent_at = lead.created_at or now

                days_elapsed = max(0.0, (now - sent_at).total_seconds() / 86400.0)
                lead_updated = False

                for step in schedule:
                    if budget <= 0:
                        break

                    if step.get("status") == "pending" and step.get("day", 1) > 1:
                        target_day = float(step.get("day", 1))
                        # Check if scheduled trigger time has arrived
                        if days_elapsed >= target_day - 0.1:  # small margin of tolerance
                            # Suppression check
                            is_supp, supp_reason = self.suppression.is_suppressed(
                                email=lead.email,
                                phone=lead.phone,
                            )
                            if is_supp:
                                step["status"] = "suppressed"
                                step["suppression_reason"] = supp_reason
                                stats["touches_suppressed"] += 1
                                lead_updated = True
                                continue

                            channel = (step.get("channel") or "email").lower()
                            content = step.get("content", "")
                            step_num = int(step.get("day", 1))
                            subject = step.get("subject") or f"Following up: {lead.company or 'Partnership'}"

                            # Execute the touch via touch_dispatcher
                            # Execute the touch via touch_dispatcher
                            task_record = AgentTask(
                                run_id=run_record.id,
                                tenant_id=self.tenant_id,
                                agent_id="agent.cadence_optimizer",
                                task_type=f"dispatch_{channel}_touch_step_{step_num}",
                                status="executing",
                                input_data={
                                    "lead_id": lead.id,
                                    "channel": channel,
                                    "step": step_num,
                                    "company": lead.company,
                                },
                            )
                            self.db.add(task_record)
                            self.db.commit()

                            res = dispatch_sales_touch(
                                self.db,
                                self.tenant_id,
                                lead,
                                channel=channel,
                                body=content,
                                subject=subject,
                                step_number=step_num,
                            )

                            if res.get("sent"):
                                step["status"] = "sent"
                                step["sent_at"] = now.isoformat()
                                step["delivery_details"] = res.get("message")
                                stats["touches_sent"] += 1
                                budget -= 1
                                lead_updated = True

                                # Append to conversations
                                conv = list(data.get("conversation") or data.get("conversations") or [])
                                conv.append({
                                    "direction": "outbound",
                                    "channel": channel,
                                    "content": content,
                                    "subject": subject,
                                    "author": "Sales AI Agent",
                                    "at": now.isoformat(),
                                    "day": step_num,
                                    "sent": True,
                                    "delivery_details": res.get("message"),
                                })
                                data["conversation"] = conv
                                data["conversations"] = conv

                                # Update deal room stage if present
                                room = self.db.query(DealRoom).filter(
                                    DealRoom.tenant_id == self.tenant_id,
                                    DealRoom.lead_id == lead.id,
                                ).first()
                                if room and room.stage == "outreach_ready":
                                    room.stage = "in_cadence"

                                task_record.status = "verified"
                                task_record.output_data = res
                                self.db.commit()

                            elif res.get("requires_action"):
                                step["status"] = "action_required"
                                step["approval_id"] = res.get("approval_id")
                                step["action_url"] = res.get("linkedin_url")
                                step["status_message"] = res.get("message")
                                stats["action_required"] += 1
                                lead_updated = True

                                task_record.status = "waiting_for_approval"
                                task_record.output_data = res
                                self.db.commit()
                            else:
                                step["status"] = "failed"
                                step["error"] = res.get("message") or res.get("reason") or "Delivery failed"
                                step["attempted_at"] = now.isoformat()
                                stats["failures"] += 1
                                lead_updated = True

                                task_record.status = "failed"
                                task_record.error = step["error"]
                                self.db.commit()

                if lead_updated:
                    data["outreach_schedule"] = schedule
                    lead.data = data
                    self.db.commit()

            run_record.status = "completed"
            run_record.finished_at = datetime.now(timezone.utc)
            run_record.output_payload = stats
            self.db.commit()

        except Exception as e:
            logger.error(f"Cadence execution failed for tenant {self.tenant_id}: {e}", exc_info=True)
            run_record.status = "failed"
            run_record.finished_at = datetime.now(timezone.utc)
            run_record.error_summary = str(e)
            self.db.commit()
            stats["failures"] += 1
            stats["details"].append(f"Error: {e}")

        return stats

    @classmethod
    def run_all_tenants_cadence(cls, db: Session, max_touches_per_tenant: int = 50) -> Dict[str, Any]:
        """Runs cadence runner across all active tenants (invoked by Celery beat)."""
        tenants = db.query(Tenant).filter(Tenant.is_active == True).all()
        aggregated = {
            "tenants_processed": 0,
            "total_sent": 0,
            "total_suppressed": 0,
            "total_halted": 0,
            "total_failures": 0,
        }
        for tenant in tenants:
            try:
                runner = cls(db, tenant.id)
                res = runner.run_tenant_cadence(max_touches=max_touches_per_tenant)
                aggregated["tenants_processed"] += 1
                aggregated["total_sent"] += res.get("touches_sent", 0)
                aggregated["total_suppressed"] += res.get("touches_suppressed", 0)
                aggregated["total_halted"] += res.get("cadences_halted_on_reply", 0)
                aggregated["total_failures"] += res.get("failures", 0)
            except Exception as t_err:
                logger.error(f"Error in cadence runner for tenant {tenant.id}: {t_err}", exc_info=True)

        return aggregated
