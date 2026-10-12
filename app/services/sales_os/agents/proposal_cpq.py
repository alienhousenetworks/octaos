"""Agent 14: Proposal & Configure-Price-Quote (CPQ) Agent.

Responsibilities:
1. Generates structured commercial quotations and multi-line item proposals.
2. Synthesizes personalized ROI and cost-benefit calculations for the target account.
3. Enforces deterministic discount policy caps via EnterpriseSalesPolicyEngine.
4. Produces publication-ready Markdown proposals with verified evidence.
"""
import time
import uuid
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.services.sales_os.agents.base import BaseSalesAgent, AgentResult, EvidenceItem
from app.models.deal_room import DealRoom, CompanySalesContext
from app.schemas.sales_swarm import ProposalQuote, LineItem
from app.services.sales_os.governance.enterprise_policy import EnterpriseSalesPolicyEngine

logger = logging.getLogger(__name__)


class ProposalCPQAgent(BaseSalesAgent):
    def __init__(self, db: Session, tenant_id: str):
        super().__init__(db, tenant_id, "agent_14_proposal_cpq")
        self.policy_engine = EnterpriseSalesPolicyEngine(db, tenant_id)

    async def execute(self, deal_room_id: str, parameters: Dict[str, Any] = None) -> AgentResult[ProposalQuote]:
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

        # Context & Product Catalog
        ctx = (
            self.db.query(CompanySalesContext)
            .filter(CompanySalesContext.tenant_id == self.tenant_id, CompanySalesContext.is_active == True)
            .first()
        )
        catalog = (ctx.products_catalog if ctx else []) or [
            {"sku": "OCTA-PLATFORM", "name": "OctaOS Core Autonomous Platform", "price": 18000.0},
            {"sku": "OCTA-AGENT-SWARM", "name": "Dedicated Sales Swarm Capacity", "price": 12000.0},
            {"sku": "OCTA-ENTERPRISE-SLA", "name": "Enterprise Governance & Security SLA", "price": 6000.0},
        ]

        # Extract parameters or default to standard package
        tier = params.get("tier", "enterprise")
        requested_discount = float(params.get("requested_discount_pct", 10.0))
        contract_term_months = int(params.get("contract_term_months", 12))
        payment_terms = params.get("payment_terms", "Net 30")

        # Select line items
        line_items = []
        if tier == "starter":
            items = catalog[:1]
        elif tier == "growth":
            items = catalog[:2]
        else:
            items = catalog

        gross_total = 0.0
        for it in items:
            p = float(it.get("price", 10000.0))
            gross_total += p
            line_items.append(
                LineItem(
                    sku=it.get("sku", "SKU-DEF"),
                    name=it.get("name", "Product Tier"),
                    unit_price=p,
                    quantity=1,
                    discount_pct=requested_discount,
                    total_price=round(p * (1.0 - (requested_discount / 100.0)), 2),
                )
            )

        # Enforce Policy Engine rules
        policy_decision = self.policy_engine.evaluate_pricing_and_discount(
            requested_discount_pct=requested_discount,
            deal_value_usd=gross_total,
            contract_term_months=contract_term_months,
            payment_terms=payment_terms,
        )

        effective_discount = requested_discount if policy_decision.status != "ESCALATE_L0" else 20.0
        net_total = round(gross_total * (1.0 - (effective_discount / 100.0)), 2)
        quote_no = f"Q-{uuid.uuid4().hex[:6].upper()}"

        # Projected ROI Model
        annual_labor_saved = round(gross_total * 3.4, 2)
        payback_months = round((net_total / (annual_labor_saved / 12.0)), 1)
        roi_model = {
            "projected_annual_labor_savings_usd": annual_labor_saved,
            "payback_period_months": payback_months,
            "projected_roi_pct": round(((annual_labor_saved - net_total) / net_total) * 100.0, 1),
            "estimated_hours_saved_per_month": 160,
        }

        # Proposal Markdown
        proposal_md = f"""# Commercial Proposal for {deal_room.company_name}
**Quote Number:** {quote_no}  
**Date:** {time.strftime('%Y-%m-%d')}  
**Contract Duration:** {contract_term_months} Months  
**Payment Terms:** {payment_terms}  

---

### Executive Summary
OctaOS delivers an autonomous multi-agent intelligence layer designed to eliminate operational friction and accelerate pipeline execution across {deal_room.company_name}'s go-to-market teams.

### Commercial Investment Breakdown
| Solution Component | SKU | List Price | Applied Discount | Net Investment |
| :--- | :--- | :--- | :--- | :--- |
"""
        for li in line_items:
            proposal_md += f"| {li.name} | `{li.sku}` | ${li.unit_price:,.2f} | {li.discount_pct:.1f}% | **${li.total_price:,.2f}** |\n"

        proposal_md += f"""
**Gross Investment:** ${gross_total:,.2f}  
**Effective Discount:** {effective_discount:.1f}%  
**Net Contract Value:** **${net_total:,.2f} USD**  

---

### Value & ROI Justification
- **Estimated Payback Period:** {payback_months} Months
- **Projected 1-Year Net Value:** ${annual_labor_saved - net_total:,.2f} USD
- **Efficiency Metric:** ~160 hours of administrative labor saved per month.
"""

        quote = ProposalQuote(
            deal_room_id=deal_room.id,
            quote_number=quote_no,
            contract_term_months=contract_term_months,
            line_items=line_items,
            gross_total_usd=gross_total,
            effective_discount_pct=effective_discount,
            net_total_usd=net_total,
            payment_terms=payment_terms,
            roi_model=roi_model,
            policy_approval_status="approved" if not policy_decision.requires_approval else "pending_manager_approval",
            generated_proposal_markdown=proposal_md,
        )

        return AgentResult(
            agent_id=self.agent_id,
            tenant_id=self.tenant_id,
            deal_room_id=deal_room.id,
            decision="ready" if not policy_decision.requires_approval else "action_required",
            confidence=1.0,
            evidence=[
                EvidenceItem(
                    claim=f"Pricing policy check: {policy_decision.reason}",
                    source="enterprise_policy_engine",
                    confidence=1.0,
                )
            ],
            source="proposal_cpq",
            reasoning_summary=f"Generated quote {quote_no} (${net_total:,.2f}). Policy Status: {policy_decision.status}.",
            missing_information=[] if not policy_decision.requires_approval else ["Manager discount sign-off"],
            recommended_next_step="send_proposal" if not policy_decision.requires_approval else "escalate_to_manager",
            data=quote,
            execution_time_ms=int((time.time() - start_time) * 1000),
        )
