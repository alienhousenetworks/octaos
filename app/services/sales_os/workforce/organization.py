"""Group the canonical sales agents. Status comes from the contract registry."""
from __future__ import annotations

from typing import Any

from app.services.sales_os.contracts.registry import capability_matrix

CANONICAL_GROUPS: list[dict[str, Any]] = [
    {
        "id": "research",
        "name": "Research & qualification",
        "summary": "Account research, discovery, enrichment, qualification, buying signals, evidence, and the buying committee.",
        "agents": [
            "sales.account_researcher",
            "sales.search_strategy",
            "sales.qualifier",
            "sales.lightweight_score",
            "sales.buying_signals",
            "sales.evidence_verifier",
            "sales.buying_committee",
        ],
    },
    {
        "id": "engagement",
        "name": "Engagement & execution",
        "summary": "Copy, conversations, cadence, policy, meetings, field work, and campaign steps.",
        "agents": [
            "sales.composer",
            "sales.conversation",
            "sales.policy_controller",
            "sales.cadence_optimizer",
            "sales.meeting_handoff",
            "sales.field_copilot",
            "sales.territory_route",
        ],
    },
    {
        "id": "commercial",
        "name": "Commercial operations",
        "summary": "Deal strategy, CPQ, deal desk, approvals, and CRM reconciliation.",
        "agents": [
            "sales.deal_strategist",
            "sales.proposal_cpq",
            "sales.deal_desk",
            "sales.crm_reconciliation",
        ],
    },
    {
        "id": "revenue",
        "name": "Revenue intelligence",
        "summary": "Forecasting, attribution, coaching, deliverability risk, and playbook proposals.",
        "agents": [
            "sales.pipeline_forecaster",
            "sales.attribution",
            "sales.sales_manager",
            "sales.risk_monitor",
            "sales.playbook_curator",
        ],
    },
]

CONTROL_PLANE = [
    {
        "id": "tenant_authorization",
        "name": "Tenant authorization",
        "status": "present",
        "note": "Tenant id is taken from the signed-in user, not from the request body.",
    },
    {
        "id": "evidence_gate",
        "name": "Evidence gate",
        "status": "partial",
        "note": "Groundedness checks exist. They do not wrap every agent response yet.",
    },
    {
        "id": "policy_engine",
        "name": "Policy engine",
        "status": "present",
        "note": "SalesPolicyEngine can allow, deny, or require approval. A model flag cannot override it.",
    },
    {
        "id": "budget_controller",
        "name": "Budget controller",
        "status": "partial",
        "note": "Search v4 reserves monthly spend. It is not a budget for every connector.",
    },
    {
        "id": "approval_service",
        "name": "Approval service",
        "status": "present",
        "note": "Enterprise approvals exist. Not every sales write is routed through them yet.",
    },
    {
        "id": "audit_log",
        "name": "Audit log",
        "status": "partial",
        "note": "Platform audit endpoints exist. This copilot does not write a new audit row per answer.",
    },
    {
        "id": "tool_registry",
        "name": "Tool registry",
        "status": "present",
        "note": "Sales tools are registered. The record copilot does not execute them.",
    },
    {
        "id": "run_state",
        "name": "Run-state manager",
        "status": "partial",
        "note": "Workflow status is stored on the business profile. A durable run-state machine is not unified here.",
    },
]


def organization() -> dict[str, Any]:
    matrix = {row["agent_id"]: row for row in capability_matrix()}
    departments = []
    registered = 0
    for group in CANONICAL_GROUPS:
        agents = []
        for agent_id in group["agents"]:
            row = matrix.get(agent_id)
            if row:
                registered += 1
            agents.append(
                {
                    "agent_id": agent_id,
                    "present": row is not None,
                    "readiness": row["readiness"] if row else "missing",
                    "lifecycle_status": row["lifecycle_status"] if row else "missing",
                    "uses_llm": row["uses_llm"] if row else "no",
                    "purpose": row["purpose"] if row else "Contract is not registered.",
                }
            )
        departments.append(
            {
                "id": group["id"],
                "name": group["name"],
                "summary": group["summary"],
                "agents": agents,
            }
        )
    orchestrator = matrix.get("sales.orchestrator")
    if orchestrator:
        registered += 1
    return {
        "orchestrator": {
            "agent_id": "sales.orchestrator",
            "tagline": "Intent, then a plan, then authorized tasks, then verified results.",
            "present": orchestrator is not None,
            "readiness": orchestrator["readiness"] if orchestrator else "missing",
            "lifecycle_status": orchestrator["lifecycle_status"] if orchestrator else "missing",
            "purpose": orchestrator["purpose"] if orchestrator else "",
        },
        "departments": departments,
        "control_plane": CONTROL_PLANE,
        "canonical_count": 24,
        "registered_canonical_count": registered,
        "extra_contracts": [
            {"agent_id": "sales.evaluation", "note": "Release-gate skill. It is not one of the 24 canonical agents."}
        ],
    }
