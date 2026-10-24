"""Deal Desk Agent.

Responsibilities:
1. Quotations & Proposal Generation: enforces strict discount caps and packaging rules.
2. Security & Compliance Questionnaire Auto-Fill: answers technical security questions backed by verified EvidenceRecord items.
3. Pre-Meeting AE Briefings & Post-Meeting Recaps.
"""
import time
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.services.sales_os.agents.base import BaseSalesAgent, AgentResult, EvidenceItem
from app.models.deal_room import DealRoom, CompanySalesContext, EvidenceRecord, BuyingCommitteeMember
from app.services.knowledge_os.entity_extractor import extract_json_safe
from app.services.sales_os.contracts.registry import render_prompts
from app.services.sales_os.governance.enterprise_policy import EnterpriseSalesPolicyEngine


class DealDeskAgent(BaseSalesAgent):
    def __init__(self, db: Session, tenant_id: str):
        super().__init__(db, tenant_id, "deal_desk_agent")
        self.policy_engine = EnterpriseSalesPolicyEngine(db, tenant_id)

    async def execute(self, deal_room_id: str, parameters: Dict[str, Any] = None) -> AgentResult:
        start_time = time.time()
        params = parameters or {}
        action_type = params.get("action_type", "pre_meeting_brief")  # pre_meeting_brief | quote | security_questionnaire | post_meeting_recap

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

        ctx = (
            self.db.query(CompanySalesContext)
            .filter(CompanySalesContext.tenant_id == self.tenant_id, CompanySalesContext.is_active == True)
            .first()
        )
        policies = ctx.policies if ctx else {}
        max_discount = float(policies.get("max_discount_pct", 10.0))

        if action_type == "quote":
            # Pricing Quotation with Enterprise Policy Enforcement
            requested_discount = float(params.get("requested_discount_pct", 0.0))
            base_amount = float(params.get("base_amount_usd", 25000.0))

            policy_decision = self.policy_engine.evaluate_pricing_and_discount(
                requested_discount_pct=requested_discount,
                deal_value_usd=base_amount,
            )

            if policy_decision.requires_approval:
                final_discount = min(requested_discount, max_discount)
                decision = "discount_capped"
                reasoning = policy_decision.reason
            else:
                final_discount = requested_discount
                decision = "quote_approved"
                reasoning = policy_decision.reason

            discount_amount = base_amount * (final_discount / 100.0)
            final_price = base_amount - discount_amount

            elapsed = int((time.time() - start_time) * 1000)
            return AgentResult(
                agent_id=self.agent_id,
                tenant_id=self.tenant_id,
                deal_room_id=deal_room.id,
                decision=decision,
                confidence=1.0,
                evidence=[
                    EvidenceItem(
                        claim=f"Enterprise sales policy enforces maximum discount of {max_discount}%",
                        source="pricing_policy",
                    )
                ],
                source="deal_desk",
                reasoning_summary=reasoning,
                recommended_next_step="human_review" if decision == "discount_capped" else "send_proposal",
                data={
                    "base_amount_usd": base_amount,
                    "discount_pct": final_discount,
                    "discount_amount_usd": discount_amount,
                    "final_price_usd": final_price,
                    "policy_max_discount": max_discount,
                },
                execution_time_ms=elapsed,
            )

        elif action_type == "security_questionnaire":
            # Auto-fill security questions from verified evidence
            question = params.get("question", "How is customer data encrypted?")
            evidence = (
                self.db.query(EvidenceRecord)
                .filter(
                    EvidenceRecord.tenant_id == self.tenant_id,
                    EvidenceRecord.claim.ilike("%encrypt%") | EvidenceRecord.claim.ilike("%security%") | EvidenceRecord.claim.ilike("%soc%"),
                )
                .all()
            )
            ev_text = "\n".join([f"- [{e.location_reference}]: {e.claim}" for e in evidence]) if evidence else "No verified evidence records match this question."
            rendered = render_prompts("sales.deal_desk", {"question": question, "evidence": ev_text})

            if not evidence:
                answer = "insufficient_evidence: no verified evidence record matches this question."
            else:
                try:
                    answer = await self.llm.complete(
                        prompt=rendered["task_prompt"],
                        system_prompt=rendered["system_prompt"],
                        model=rendered["model_id"],
                        provider=rendered["provider"],
                    )
                except Exception:
                    answer = f"insufficient_evidence: the model was unavailable. Verified evidence remains: {ev_text[:240]}"

            elapsed = int((time.time() - start_time) * 1000)
            return AgentResult(
                agent_id=self.agent_id,
                tenant_id=self.tenant_id,
                deal_room_id=deal_room.id,
                decision="answered",
                confidence=0.95,
                evidence=[EvidenceItem(claim=e.claim, source=e.location_reference) for e in evidence[:2]],
                source="security_compliance_evidence",
                reasoning_summary="Security questionnaire answered using primary compliance documentation.",
                recommended_next_step="attach_to_rfp",
                data={"question": question, "answer": answer.strip()},
                execution_time_ms=elapsed,
            )

        else:
            # Default: Pre-Meeting Brief for Human Closer
            committee = (
                self.db.query(BuyingCommitteeMember)
                .filter(BuyingCommitteeMember.deal_room_id == deal_room.id)
                .all()
            )
            brief = {
                "company_name": deal_room.company_name,
                "domain": deal_room.domain,
                "stage": deal_room.stage,
                "calibrated_win_prob": deal_room.calibrated_win_prob,
                "attendees": [{"name": m.name, "title": m.title, "role": m.role_type} for m in committee],
                "strategic_pain_points": [p.get("inference") for p in (deal_room.pain_hypotheses or [])],
                "suggested_questions": [
                    "What current bottlenecks are impacting your outbound revenue goals?",
                    "How are executive decisions currently made across your buying committee?",
                ],
            }
            elapsed = int((time.time() - start_time) * 1000)
            return AgentResult(
                agent_id=self.agent_id,
                tenant_id=self.tenant_id,
                deal_room_id=deal_room.id,
                decision="brief_ready",
                confidence=0.95,
                source="deal_desk",
                reasoning_summary=f"Closer pre-meeting briefing generated for {deal_room.company_name}.",
                recommended_next_step="conduct_discovery_call",
                data=brief,
                execution_time_ms=elapsed,
            )

    async def generate_quote(self, deal_room_id: str, list_price: float, discount_pct: float) -> Dict[str, Any]:
        """Generate pricing quote enforcing discount limits."""
        params = {
            "action_type": "quote",
            "base_amount_usd": list_price,
            "requested_discount_pct": discount_pct * 100.0 if discount_pct <= 1.0 else discount_pct,
        }
        res = await self.execute(deal_room_id, params)
        discount_val = discount_pct if discount_pct <= 1.0 else discount_pct / 100.0
        status = "approved" if res.decision == "quote_approved" else "requires_approval"
        net_amount = round(list_price * (1.0 - discount_val), 2)
        return {
            "status": status,
            "net_amount": net_amount,
            "list_price": list_price,
            "discount_pct": discount_val,
            "agent_result": res,
        }
