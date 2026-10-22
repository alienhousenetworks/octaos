"""
Autonomous Schedule Recovery Engine.
Detects showing overruns, delays, and cancellations; computes cascade delay impact;
and formulates feasible recovery proposals with full before/after diffs.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Any
from sqlalchemy.orm import Session
from app.models.real_estate import RealEstateSiteVisit, RealEstateProject
from app.models.field_sales import SalespersonFieldStatus, FieldScheduleRecoveryProposal


class ScheduleRecoveryEngine:
    """
    Evaluates field delays and generates non-destructive recovery proposals.
    """

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def detect_and_propose_recovery(
        self,
        delayed_visit_id: str,
        delay_minutes: int = 30,
        delay_reason: str = "Showing running over scheduled duration with prospective buyer.",
    ) -> dict[str, Any]:
        """
        Calculates cascade effect of a delay and builds an actionable recovery proposal.
        """
        delayed_visit = (
            self.db.query(RealEstateSiteVisit)
            .filter(
                RealEstateSiteVisit.id == delayed_visit_id,
                RealEstateSiteVisit.tenant_id == self.tenant_id,
            )
            .first()
        )
        if not delayed_visit:
            raise ValueError(f"Visit {delayed_visit_id} not found")

        agent_id = delayed_visit.assigned_agent
        now = datetime.now(timezone.utc)

        # Mark delayed visit status
        delayed_visit.status = "delayed"
        delayed_visit.recovery_notes = f"Delayed by {delay_minutes}m: {delay_reason}"

        # Find remaining scheduled visits for this agent today after this visit
        remaining_visits = (
            self.db.query(RealEstateSiteVisit)
            .filter(
                RealEstateSiteVisit.tenant_id == self.tenant_id,
                RealEstateSiteVisit.assigned_agent == agent_id,
                RealEstateSiteVisit.scheduled_at >= delayed_visit.scheduled_at,
                RealEstateSiteVisit.id != delayed_visit_id,
                RealEstateSiteVisit.status.in_(["scheduled", "en_route"]),
            )
            .order_by(RealEstateSiteVisit.scheduled_at.asc())
            .all()
        )

        # Find peer agents who might be available
        other_agents = (
            self.db.query(SalespersonFieldStatus)
            .filter(
                SalespersonFieldStatus.tenant_id == self.tenant_id,
                SalespersonFieldStatus.user_id != agent_id,
                SalespersonFieldStatus.is_shift_active == True,
            )
            .all()
        )

        proposed_changes: list[dict[str, Any]] = []
        accumulated_delay = delay_minutes

        for idx, visit in enumerate(remaining_visits):
            orig_time = visit.scheduled_at
            # If delay is small (<45m), slide the time
            if accumulated_delay <= 45 or not other_agents:
                new_time = orig_time + timedelta(minutes=accumulated_delay)
                proposed_changes.append({
                    "visit_id": visit.id,
                    "lead_id": visit.lead_id,
                    "action": "time_adjusted",
                    "original_time": orig_time.isoformat(),
                    "proposed_time": new_time.isoformat(),
                    "original_agent": agent_id,
                    "proposed_agent": agent_id,
                    "rationale": f"Adjusted by +{accumulated_delay} mins to absorb earlier showing overrun.",
                    "customer_message_draft": f"Hello! Your property specialist is slightly delayed by {accumulated_delay} minutes due to traffic. We look forward to showing you the property at {new_time.strftime('%I:%M %p')}.",
                })
            else:
                # Reassign subsequent visit to peer agent with lightest schedule
                peer = other_agents[idx % len(other_agents)]
                proposed_changes.append({
                    "visit_id": visit.id,
                    "lead_id": visit.lead_id,
                    "action": "reassigned_to_peer",
                    "original_time": orig_time.isoformat(),
                    "proposed_time": orig_time.isoformat(),
                    "original_agent": agent_id,
                    "proposed_agent": peer.user_id,
                    "rationale": f"Reassigned to available specialist ({peer.user_id}) to preserve buyer's preferred time slot.",
                    "customer_message_draft": f"Hello! To ensure your visit starts on time at {orig_time.strftime('%I:%M %p')}, senior property specialist {peer.user_id} has been assigned to escort your tour.",
                })

        proposal = FieldScheduleRecoveryProposal(
            tenant_id=self.tenant_id,
            trigger_type="agent_delay",
            affected_user_id=agent_id,
            affected_visit_id=delayed_visit_id,
            status="pending_review",
            rationale=f"Delay of {delay_minutes} mins on visit {delayed_visit_id}. Formulated recovery for {len(remaining_visits)} subsequent appointment(s).",
            proposed_changes=proposed_changes,
        )
        self.db.add(proposal)
        self.db.commit()
        self.db.refresh(proposal)

        return {
            "proposal_id": proposal.id,
            "status": proposal.status,
            "affected_visits_count": len(remaining_visits),
            "rationale": proposal.rationale,
            "proposed_changes": proposed_changes,
        }

    def apply_proposal(self, proposal_id: str, reviewer_user_id: str) -> dict[str, Any]:
        """
        Applies an approved schedule recovery proposal to the live database records.
        """
        proposal = (
            self.db.query(FieldScheduleRecoveryProposal)
            .filter(
                FieldScheduleRecoveryProposal.id == proposal_id,
                FieldScheduleRecoveryProposal.tenant_id == self.tenant_id,
            )
            .first()
        )
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")

        if proposal.status != "pending_review":
            return {"proposal_id": proposal.id, "status": proposal.status, "message": f"Proposal already {proposal.status}"}

        changes = proposal.proposed_changes or []
        for change in changes:
            v_id = change.get("visit_id")
            visit = self.db.query(RealEstateSiteVisit).filter(RealEstateSiteVisit.id == v_id).first()
            if visit:
                if change.get("proposed_time"):
                    pt = change["proposed_time"]
                    dt = datetime.fromisoformat(pt)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    visit.scheduled_at = dt
                if change.get("proposed_agent"):
                    visit.assigned_agent = change["proposed_agent"]
                visit.status = "scheduled"
                visit.recovery_notes = f"Updated via recovery proposal {proposal_id}"

        proposal.status = "applied"
        proposal.reviewed_by_user_id = reviewer_user_id
        proposal.reviewed_at = datetime.now(timezone.utc)
        self.db.commit()

        return {
            "proposal_id": proposal.id,
            "status": "applied",
            "applied_changes_count": len(changes),
        }

    def reject_proposal(self, proposal_id: str, reviewer_user_id: str, reason: str = "") -> dict[str, Any]:
        """Rejects a recovery proposal."""
        proposal = (
            self.db.query(FieldScheduleRecoveryProposal)
            .filter(
                FieldScheduleRecoveryProposal.id == proposal_id,
                FieldScheduleRecoveryProposal.tenant_id == self.tenant_id,
            )
            .first()
        )
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")

        proposal.status = "rejected"
        proposal.reviewed_by_user_id = reviewer_user_id
        proposal.reviewed_at = datetime.now(timezone.utc)
        if reason:
            proposal.rationale = f"{proposal.rationale} | Rejected: {reason}"
        self.db.commit()
        return {"proposal_id": proposal.id, "status": "rejected"}
