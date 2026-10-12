import uuid
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class StrategistAgent:
    """
    Agent #2: Strategist (Executive Cognitive Layer)
    Trust Level: L0 Read-only (Plan Synthesis)

    Responsibilities:
    - Compiles verified evidence and IntentAST into three distinct DAG variants:
      1. AGGRESSIVE: Maximum velocity and upside ($P90 focus)
      2. BALANCED: Sequenced milestones and balanced risk ($P50 focus)
      3. CONSERVATIVE: Organic validation and low spend ($P10 focus)
    - Emits typed capability IDs from the Capability Registry only
    """
    AGENT_ID = "agent_02_strategist"
    AGENT_NAME = "Strategist"
    DEPARTMENT = "STRATEGY"

    def __init__(self, db: Optional[Session] = None, tenant_id: Optional[str] = None):
        self.db = db
        self.tenant_id = tenant_id

    def compile_candidate_dags(
        self,
        intent_ast: Dict[str, Any],
        verified_evidence: List[Dict[str, Any]],
        budget_cap: float,
        deliberation_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Synthesizes candidate DAG structures for Aggressive, Balanced, and Conservative strategies,
        dynamically tailored to the objective, required agents, and council deliberation.
        """
        objective = intent_ast.get("primary_objective", "Scale business operations")
        pillar = intent_ast.get("strategic_pillar", "REVENUE")
        lower_obj = objective.lower()

        # Check domain involvement
        has_talent = pillar == "TALENT" or any(w in lower_obj for w in ["hire", "recruit", "talent", "headcount", "engineer"])
        has_support = pillar == "CRISIS" or any(w in lower_obj for w in ["support", "ticket", "churn", "retention", "csat"])
        has_cost = pillar == "COST" or any(w in lower_obj for w in ["cost", "spend", "cut", "reduce", "burn"])
        has_growth = not (has_talent or has_support or has_cost) or any(w in lower_obj for w in ["sales", "lead", "market", "campaign", "grow"])

        # 1. Aggressive Variant (High velocity, parallelized outreach, upside focus)
        agg_budget = round(budget_cap * 0.95, 2)
        agg_nodes = self._build_variant_nodes(
            variant="AGGRESSIVE",
            objective=objective,
            budget=agg_budget,
            has_growth=has_growth,
            has_talent=has_talent,
            has_support=has_support,
            has_cost=has_cost
        )

        # 2. Balanced Variant (Milestone-gated, verified ICP, balanced risk)
        bal_budget = round(budget_cap * 0.60, 2)
        bal_nodes = self._build_variant_nodes(
            variant="BALANCED",
            objective=objective,
            budget=bal_budget,
            has_growth=has_growth,
            has_talent=has_talent,
            has_support=has_support,
            has_cost=has_cost
        )

        # 3. Conservative Variant (Risk-averse, low burn, high validation)
        con_budget = round(budget_cap * 0.25, 2)
        con_nodes = self._build_variant_nodes(
            variant="CONSERVATIVE",
            objective=objective,
            budget=con_budget,
            has_growth=has_growth,
            has_talent=has_talent,
            has_support=has_support,
            has_cost=has_cost
        )

        return {
            "AGGRESSIVE": {
                "variant": "AGGRESSIVE",
                "executive_summary": f"High-velocity execution focusing on rapid market capture and maximum upside for '{objective}'.",
                "estimated_budget": agg_budget,
                "max_budget_envelope": budget_cap,
                "nodes": agg_nodes
            },
            "BALANCED": {
                "variant": "BALANCED",
                "executive_summary": f"Milestone-gated execution balancing capital efficiency and growth for '{objective}'.",
                "estimated_budget": bal_budget,
                "max_budget_envelope": budget_cap,
                "nodes": bal_nodes
            },
            "CONSERVATIVE": {
                "variant": "CONSERVATIVE",
                "executive_summary": f"Capital-preserving organic execution safeguarding downside risks for '{objective}'.",
                "estimated_budget": con_budget,
                "max_budget_envelope": budget_cap,
                "nodes": con_nodes
            }
        }

    def _build_variant_nodes(
        self,
        variant: str,
        objective: str,
        budget: float,
        has_growth: bool,
        has_talent: bool,
        has_support: bool,
        has_cost: bool
    ) -> List[Dict[str, Any]]:
        prefix = variant[:3].lower() # agg, bal, con
        nodes: List[Dict[str, Any]] = []

        # Step 1: Capital Allocation & Governance (Finance)
        fin_node_id = f"node-{prefix}-fin-1"
        nodes.append({
            "id": fin_node_id,
            "name": f"Capital Allocation (${budget:,.0f} Budget)",
            "department": "Finance",
            "capability_id": "finance.allocate_budget",
            "capability_version": "1.0.0",
            "parameters": {"amount": budget, "department": "Executive Growth", "objective": objective},
            "depends_on": [],
            "estimated_duration_seconds": 15,
            "is_compensable": True
        })

        if has_talent:
            # HR Talent Pipeline
            hr_node_id = f"node-{prefix}-hr-1"
            nodes.append({
                "id": hr_node_id,
                "name": "Target Talent Sourcing & Screening",
                "department": "HR",
                "capability_id": "hr.source_candidates",
                "capability_version": "1.0.0",
                "parameters": {"role": "Senior Specialist", "count": 10 if variant == "AGGRESSIVE" else 5 if variant == "BALANCED" else 2},
                "depends_on": [fin_node_id],
                "estimated_duration_seconds": 45,
                "is_compensable": True
            })
            nodes.append({
                "id": f"node-{prefix}-hr-2",
                "name": "Candidate Shortlist Review & Outreach",
                "department": "HR",
                "capability_id": "crm.tag_contact",
                "capability_version": "1.0.0",
                "parameters": {"contact_id": f"batch-{prefix}-candidates", "tag": "INTERVIEW_READY"},
                "depends_on": [hr_node_id],
                "estimated_duration_seconds": 30,
                "is_compensable": True
            })

        elif has_support:
            # Customer Support & Retention Pipeline
            sup_node_id = f"node-{prefix}-sup-1"
            nodes.append({
                "id": sup_node_id,
                "name": "Customer Feedback & SLA Audit",
                "department": "Support",
                "capability_id": "support.triage_tickets",
                "capability_version": "1.0.0",
                "parameters": {"focus_area": "Retention & Churn Mitigation", "severity_threshold": "HIGH"},
                "depends_on": [fin_node_id],
                "estimated_duration_seconds": 30,
                "is_compensable": True
            })
            nodes.append({
                "id": f"node-{prefix}-sup-2",
                "name": "VIP Account Retention Categorization",
                "department": "CRM",
                "capability_id": "crm.tag_contact",
                "capability_version": "1.0.0",
                "parameters": {"contact_id": f"batch-{prefix}-accounts", "tag": "RETENTION_PRIORITY"},
                "depends_on": [sup_node_id],
                "estimated_duration_seconds": 25,
                "is_compensable": True
            })

        else:
            # Growth, Marketing, and Sales Outbound Pipeline
            # Step 2: Marketing Research & Positioning
            mktg_node_id = f"node-{prefix}-mktg-1"
            nodes.append({
                "id": mktg_node_id,
                "name": "Audience Persona & Market Positioning",
                "department": "Marketing",
                "capability_id": "marketing.research_audience",
                "capability_version": "1.0.0",
                "parameters": {
                    "topic": objective,
                    "depth": "COMPREHENSIVE" if variant == "AGGRESSIVE" else "FOCUSED",
                    "platforms": ["linkedin", "email"]
                },
                "depends_on": [fin_node_id],
                "estimated_duration_seconds": 35,
                "is_compensable": True
            })

            # Step 3: Sales Prospect Sourcing & CRM Tagging
            sales_source_id = f"node-{prefix}-sales-1"
            lead_count = 100 if variant == "AGGRESSIVE" else 40 if variant == "BALANCED" else 15
            nodes.append({
                "id": sales_source_id,
                "name": f"High-Intent Lead Sourcing ({lead_count} Prospects)",
                "department": "Sales",
                "capability_id": "sales.source_leads",
                "capability_version": "1.0.0",
                "parameters": {
                    "query": objective,
                    "count": lead_count,
                    "min_confidence": 0.75 if variant == "CONSERVATIVE" else 0.60
                },
                "depends_on": [mktg_node_id],
                "estimated_duration_seconds": 45,
                "is_compensable": True
            })

            # Step 4: CRM Tagging & ICP Qualification
            tag_node_id = f"node-{prefix}-tag-1"
            nodes.append({
                "id": tag_node_id,
                "name": "CRM Qualification & Pipeline Staging",
                "department": "CRM",
                "capability_id": "crm.tag_contact",
                "capability_version": "1.0.0",
                "parameters": {
                    "contact_id": f"batch-{prefix}-leads",
                    "tag": "QUALIFIED_ICP" if variant != "AGGRESSIVE" else "HIGH_VELOCITY_TARGET"
                },
                "depends_on": [sales_source_id],
                "estimated_duration_seconds": 20,
                "is_compensable": True
            })

            # Step 5: Multi-Touch Sequence Dispatch
            nodes.append({
                "id": f"node-{prefix}-email-1",
                "name": "Personalized Outreach Sequence",
                "department": "Sales",
                "capability_id": "sales.send_sequence",
                "capability_version": "1.0.0",
                "parameters": {
                    "lead_ids": [f"lead-{prefix}-{i}" for i in range(1, 4 if variant != "CONSERVATIVE" else 2)],
                    "template_id": f"tpl-{prefix}-v1",
                    "channel": "smtp"
                },
                "depends_on": [tag_node_id],
                "estimated_duration_seconds": 60 if variant == "AGGRESSIVE" else 40,
                "is_compensable": False
            })

        return nodes

