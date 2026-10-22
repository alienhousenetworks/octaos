"""
Natural Language Planning & Dispatch Agent for Sales Directors and Dispatchers.
Parses executive instructions into structured scheduling and recovery operations.
"""
from __future__ import annotations
import re
from datetime import datetime, date, timedelta, timezone
from typing import Any
from sqlalchemy.orm import Session
from app.services.sales_os.field_sales.engine.optimizer import ScheduleOptimizer
from app.services.sales_os.field_sales.engine.recovery import ScheduleRecoveryEngine
from app.models.real_estate import RealEstateSiteVisit, RealEstateProject
from app.models.verticals import Lead


class NaturalLanguageDispatchAgent:
    """
    Parses conversational dispatch commands into deterministic scheduling actions.
    """

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.optimizer = ScheduleOptimizer(db, tenant_id)
        self.recovery = ScheduleRecoveryEngine(db, tenant_id)

    async def execute_command(self, prompt: str, user_id: str) -> dict[str, Any]:
        """
        Interprets natural language dispatch prompt and returns structured plan preview.
        """
        p_lower = (prompt or "").lower().strip()

        # 1. Plan tomorrow's property visits
        if "tomorrow" in p_lower and ("plan" in p_lower or "optimize" in p_lower or "schedule" in p_lower):
            target_date = date.today() + timedelta(days=1)
            result = await self.optimizer.optimize_day_schedule(target_date)
            return {
                "intent": "PLAN_TOMORROW",
                "summary": f"Analyzed {result.get('visits_count', 0)} scheduled property visits for tomorrow ({target_date.isoformat()}). Computed road travel matrices and ordered stops to minimize transit time.",
                "data": result,
                "suggested_actions": ["Approve Tomorrow's Route", "Export to Calendar"],
            }

        # 2. Plan today's visits / optimize today
        if ("today" in p_lower or "current day" in p_lower) and ("plan" in p_lower or "optimize" in p_lower):
            target_date = date.today()
            result = await self.optimizer.optimize_day_schedule(target_date)
            return {
                "intent": "PLAN_TODAY",
                "summary": f"Optimized today's route across all active salespeople. Balanced travel windows and inspection durations.",
                "data": result,
                "suggested_actions": ["Publish Route to Mobile Apps"],
            }

        # 3. Rearrange / delay recovery
        if "rearrange" in p_lower or "delay" in p_lower or "running late" in p_lower or "recover" in p_lower:
            # Find the most recently delayed or active visit
            active_visit = (
                self.db.query(RealEstateSiteVisit)
                .filter(
                    RealEstateSiteVisit.tenant_id == self.tenant_id,
                    RealEstateSiteVisit.status.in_(["scheduled", "en_route", "delayed"]),
                )
                .order_by(RealEstateSiteVisit.scheduled_at.asc())
                .first()
            )
            if not active_visit:
                return {
                    "intent": "RECOVER_SCHEDULE",
                    "summary": "No active visits currently eligible for recovery.",
                    "data": None,
                }

            # Propose recovery with 30 min delay
            res = self.recovery.detect_and_propose_recovery(
                delayed_visit_id=active_visit.id,
                delay_minutes=30,
                delay_reason="Traffic / extended buyer showing",
            )
            return {
                "intent": "RECOVER_SCHEDULE",
                "summary": f"Detected potential showing overrun. Generated recovery proposal adjusting {res.get('affected_visits_count', 0)} subsequent appointments to protect buyer commitments.",
                "data": res,
                "suggested_actions": ["Approve Recovery Proposal", "Reject Proposal"],
            }

        # 4. Find high-priority leads / families near property
        if "nearby" in p_lower or "high-priority" in p_lower or "families" in p_lower or "priority" in p_lower:
            high_score_leads = (
                self.db.query(Lead)
                .filter(
                    Lead.tenant_id == self.tenant_id,
                    Lead.score >= 70,
                )
                .limit(5)
                .all()
            )
            leads_summary = [
                {
                    "lead_id": l.id,
                    "name": l.name,
                    "score": l.score,
                    "phone": l.phone or l.mobile_no,
                    "budget": l.need_of_what or "Premium",
                    "status": l.status,
                }
                for l in high_score_leads
            ]
            return {
                "intent": "FIND_NEARBY_PRIORITY",
                "summary": f"Identified {len(leads_summary)} high-intent buyers eligible for same-day showings near active project hubs.",
                "data": {"leads": leads_summary},
                "suggested_actions": ["Book Showing", "Send WhatsApp Invite"],
            }

        # General dispatch plan fallback
        target_date = date.today()
        result = await self.optimizer.optimize_day_schedule(target_date)
        return {
            "intent": "GENERAL_DISPATCH_PLAN",
            "summary": f"Generated comprehensive dispatch analysis for {target_date.isoformat()}.",
            "data": result,
            "suggested_actions": ["Apply Route Optimization"],
        }
