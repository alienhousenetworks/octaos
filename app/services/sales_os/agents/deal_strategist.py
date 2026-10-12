"""Agent 13: Deal Strategist & MEDDPICC Auditor.

Responsibilities:
1. Audits deal conversations, emails, and notes across all 8 MEDDPICC dimensions.
2. Identifies single-threaded deals and flags missing committee stakeholders.
3. Synthesizes a structured Mutual Action Plan (MAP) with clear milestone owners.
4. Generates an auditable Daily Next Best Action per active opportunity.
"""
import time
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.services.sales_os.agents.base import BaseSalesAgent, AgentResult, EvidenceItem
from app.models.deal_room import DealRoom, BuyingCommitteeMember, DealActivity, CompanySalesContext
from app.schemas.sales_swarm import (
    DealStrategyReport,
    MEDDPICCDimension,
    MutualActionMilestone,
)

logger = logging.getLogger(__name__)


class DealStrategistAgent(BaseSalesAgent):
    def __init__(self, db: Session, tenant_id: str):
        super().__init__(db, tenant_id, "agent_13_deal_strategist")

    async def execute(self, deal_room_id: str, parameters: Dict[str, Any] = None) -> AgentResult[DealStrategyReport]:
        start_time = time.time()
        params = parameters or {}

        deal_room = (
            self.db.query(DealRoom)
            .filter(DealRoom.id == deal_room_id, DealRoom.tenant_id == self.tenant_id)
            .first()
        )
        if not deal_room:
            return AgentResult(
                agent_id=self.agent_id,
                tenant_id=self.tenant_id,
                decision="error",
                confidence=0.0,
                reasoning_summary=f"DealRoom '{deal_room_id}' not found.",
                recommended_next_step="discover_account",
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

        committee = (
            self.db.query(BuyingCommitteeMember)
            .filter(BuyingCommitteeMember.deal_room_id == deal_room_id)
            .all()
        )
        activities = (
            self.db.query(DealActivity)
            .filter(DealActivity.deal_room_id == deal_room_id)
            .order_by(DealActivity.created_at.desc())
            .limit(20)
            .all()
        )

        has_eb = any(m.role_type == "economic_buyer" for m in committee)
        has_champion = any(m.role_type == "champion" for m in committee)
        has_tech = any(m.role_type == "technical" for m in committee)
        is_single_threaded = len(committee) <= 1

        missing_roles = []
        if not has_eb:
            missing_roles.append("Economic Buyer")
        if not has_champion:
            missing_roles.append("Champion")
        if not has_tech:
            missing_roles.append("Technical Evaluator")

        pains = list(deal_room.pain_hypotheses or [])
        metrics_identified = bool(deal_room.solution_matches or any("kpi" in (a.content or "").lower() for a in activities))

        # MEDDPICC Dimension Auditing
        dimensions = [
            MEDDPICCDimension(
                dimension="Metrics",
                status="verified" if metrics_identified else "identified",
                evidence_snippet="Identified target ROI and cost metrics" if metrics_identified else None,
                confidence=0.9 if metrics_identified else 0.5,
                action_to_verify="Quantify annualized cost of current manual workflow during next discovery call.",
            ),
            MEDDPICCDimension(
                dimension="Economic Buyer",
                status="verified" if has_eb else "at_risk",
                evidence_snippet="Economic buyer confirmed in committee" if has_eb else None,
                confidence=0.95 if has_eb else 0.2,
                action_to_verify="Identify budget authority holder (VP/C-Suite) and schedule multi-thread touchpoint." if not has_eb else None,
            ),
            MEDDPICCDimension(
                dimension="Decision Criteria",
                status="identified" if deal_room.tech_stack else "unknown",
                evidence_snippet=f"Tech stack: {', '.join(deal_room.tech_stack[:3])}" if deal_room.tech_stack else None,
                confidence=0.7 if deal_room.tech_stack else 0.3,
            ),
            MEDDPICCDimension(
                dimension="Decision Process",
                status="identified" if len(activities) >= 3 else "unknown",
                confidence=0.6 if len(activities) >= 3 else 0.2,
            ),
            MEDDPICCDimension(
                dimension="Paper Process",
                status="identified" if deal_room.stage in ("proposal", "closing") else "unknown",
                confidence=0.8 if deal_room.stage in ("proposal", "closing") else 0.1,
                action_to_verify="Clarify procurement timeline, infosec questionnaire review SLA, and standard MSA terms.",
            ),
            MEDDPICCDimension(
                dimension="Identify Pain",
                status="verified" if pains else "unknown",
                evidence_snippet=str(pains[0]) if pains else None,
                confidence=0.9 if pains else 0.3,
            ),
            MEDDPICCDimension(
                dimension="Champion",
                status="verified" if has_champion else "at_risk",
                confidence=0.9 if has_champion else 0.2,
                action_to_verify="Test champion strength by asking for internal architecture or procurement intro." if not has_champion else None,
            ),
            MEDDPICCDimension(
                dimension="Competition",
                status="identified" if any("competitor" in (a.content or "").lower() for a in activities) else "unknown",
                confidence=0.7 if any("competitor" in (a.content or "").lower() for a in activities) else 0.4,
            ),
        ]

        verified_count = sum(1 for d in dimensions if d.status == "verified")
        identified_count = sum(1 for d in dimensions if d.status == "identified")
        score = round((verified_count * 12.5) + (identified_count * 6.25), 1)

        # Standard Mutual Action Plan
        map_milestones = [
            MutualActionMilestone(milestone_name="Initial Discovery & Alignment Call", owner="joint", target_completion_date="Day 1", status="completed"),
            MutualActionMilestone(milestone_name="Architecture & Security Review", owner="vendor", target_completion_date="Day 7", status="pending" if has_tech else "pending"),
            MutualActionMilestone(milestone_name="Executive Value Presentation (EB)", owner="joint", target_completion_date="Day 14", status="pending"),
            MutualActionMilestone(milestone_name="Commercial Proposal & MSA Review", owner="client", target_completion_date="Day 21", status="pending"),
            MutualActionMilestone(milestone_name="Target Go-Live Target Milestone", owner="joint", target_completion_date="Day 30", status="pending"),
        ]

        # Formulate Next Best Action
        if not has_eb and deal_room.stage not in ("discovered", "nurtured"):
            nba = {
                "action": "multi_thread_economic_buyer",
                "target_persona": "VP Finance / CTO / CFO",
                "reason": "Deal is single-threaded without confirmed Economic Buyer. Risk of stall at proposal stage.",
                "confidence": 0.92,
            }
        elif is_single_threaded:
            nba = {
                "action": "introduce_technical_evaluator",
                "target_persona": "Head of Engineering / Security",
                "reason": "Single-threaded contact. Introduce technical peer to accelerate validation.",
                "confidence": 0.88,
            }
        else:
            nba = {
                "action": "confirm_paper_process",
                "target_persona": "Champion",
                "reason": "Committee engaged. Confirm legal and procurement timeline for closing.",
                "confidence": 0.85,
            }

        report = DealStrategyReport(
            deal_room_id=deal_room.id,
            meddpicc_score=score,
            meddpicc_breakdown=dimensions,
            is_single_threaded=is_single_threaded,
            missing_critical_roles=missing_roles,
            mutual_action_plan=map_milestones,
            daily_next_best_action=nba,
        )

        # Persist updates into DealRoom
        flags = list(deal_room.risk_flags or [])
        if is_single_threaded and "single_threaded" not in flags:
            flags.append("single_threaded")
        elif not is_single_threaded and "single_threaded" in flags:
            flags.remove("single_threaded")
        deal_room.risk_flags = flags
        deal_room.is_multi_threaded = not is_single_threaded
        deal_room.next_best_action = nba
        self.db.commit()

        evidence_items = [
            EvidenceItem(
                claim=f"Committee multi-threading: {len(committee)} stakeholders verified",
                source="deal_room_committee",
                confidence=1.0,
            )
        ]

        return AgentResult(
            agent_id=self.agent_id,
            tenant_id=self.tenant_id,
            deal_room_id=deal_room.id,
            decision="action_required" if is_single_threaded else "ready",
            confidence=round(score / 100.0, 2),
            evidence=evidence_items,
            source="deal_strategist",
            reasoning_summary=f"MEDDPICC score {score}/100. Single-threaded={is_single_threaded}. Missing: {', '.join(missing_roles) or 'None'}.",
            missing_information=missing_roles,
            recommended_next_step=nba["action"],
            data=report,
            execution_time_ms=int((time.time() - start_time) * 1000),
        )
