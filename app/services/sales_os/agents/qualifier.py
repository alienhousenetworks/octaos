"""Capability 10: Multi-Factor Lead & Account Qualifier.

Evaluates:
- Firmographic Fit (Industry, Employee Count, Revenue Band)
- Budget Capacity Fit
- Timing Score (Recency and velocity of buying signals)
- Evidence Coverage
Produces an explainable qualification decision without artificial leniency.
"""
import time
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.services.sales_os.agents.base import BaseSalesAgent, AgentResult, EvidenceItem
from app.models.deal_room import DealRoom, CompanySalesContext
from app.services.sales_os.aso.qualification import qualify_account
from app.services.sales_os.aso.state_machine import apply_transition


class QualifierAgent(BaseSalesAgent):
    def __init__(self, db: Session, tenant_id: str):
        super().__init__(db, tenant_id, "agent_10_qualifier")

    async def execute(self, deal_room_id: str, parameters: Dict[str, Any] = None) -> AgentResult:
        start_time = time.time()
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
                reasoning_summary="DealRoom not found",
                recommended_next_step="discover_account",
            )

        # Fetch active Company Sales Context
        ctx = (
            self.db.query(CompanySalesContext)
            .filter(
                CompanySalesContext.tenant_id == self.tenant_id,
                CompanySalesContext.is_active == True,  # noqa: E712
            )
            .first()
        )
        icp = ctx.icp_definitions if ctx else {}
        target_industries = list(icp.get("industries") or ["saas", "technology", "manufacturing", "healthcare"])
        decision_record = qualify_account(
            industry=deal_room.industry,
            employee_count=deal_room.employee_count,
            annual_revenue_usd=deal_room.annual_revenue_usd,
            target_industries=target_industries,
            timing_score=deal_room.timing_score,
        )
        missing_info = list(decision_record.unknowns)
        scores = decision_record.inputs
        icp_fit = decision_record.fit_score
        timing = deal_room.timing_score
        evidence_cov = decision_record.confidence or 0.0
        if icp_fit is None:
            priority = 0.0
        elif timing:
            priority = round(icp_fit * timing * evidence_cov, 3)
        else:
            priority = round(icp_fit * evidence_cov, 3)
        deal_room.icp_fit_score = 0.0 if icp_fit is None else round(icp_fit, 3)
        deal_room.priority_index = priority

        if decision_record.decision == "qualified":
            event = "qualify_pass"
        elif decision_record.decision == "needs_review":
            event = "qualify_review"
        else:
            event = "qualify_fail"
        transition = apply_transition(
            deal_room,
            event,
            actor="sales.qualifier",
            reason=decision_record.rationale,
        )
        self.db.commit()

        decision = decision_record.decision
        reasoning = decision_record.rationale
        fit_text = "unknown" if icp_fit is None else f"{icp_fit:.2f}"

        elapsed = int((time.time() - start_time) * 1000)
        return AgentResult(
            agent_id=self.agent_id,
            tenant_id=self.tenant_id,
            deal_room_id=deal_room.id,
            contract_id="sales.qualifier",
            decision=decision,
            confidence=round(evidence_cov, 2),
            evidence=[
                EvidenceItem(
                    claim=f"Company {deal_room.company_name} ICP fit is {fit_text}. {reasoning}",
                    source="icp_evaluator",
                    confidence=evidence_cov,
                )
            ],
            source="deal_room_evaluator",
            reasoning_summary=reasoning,
            missing_information=missing_info,
            recommended_next_step="account_research" if decision == "qualified" else "enrich_further",
            data={
                "icp_fit_score": None if icp_fit is None else round(icp_fit, 3),
                "timing_score": None if timing is None else round(timing, 3),
                "priority_index": priority,
                "dimension_scores": scores,
                "qualification": decision_record.model_dump(),
                "transition": transition,
            },
            execution_time_ms=elapsed,
        )
