"""
OctaOS Industry Solution Pack Contract.

Defines the formal interface for pluggable, versioned industry packs that extend
the universal platform without leaking industry-specific schemas or terminology
into the core engines.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class PackReadiness(str, Enum):
    CONFIGURATION = "configuration"
    EXTENSIBLE = "extensible"
    PRODUCTION_READY = "production_ready"


class RiskLevel(str, Enum):
    R0_INFORMATIONAL = "R0_INFORMATIONAL"
    R1_INTERNAL_REVERSIBLE = "R1_INTERNAL_REVERSIBLE"
    R2_EXTERNAL_REVERSIBLE = "R2_EXTERNAL_REVERSIBLE"
    R3_EXTERNAL_IRREVERSIBLE = "R3_EXTERNAL_IRREVERSIBLE"
    R4_FINANCIAL_CRITICAL = "R4_FINANCIAL_CRITICAL"


@dataclass
class PackPipelineStage:
    id: str
    label: str
    color: str = "#75AFCB"
    is_terminal: bool = False
    terminal_outcome: Optional[str] = None  # "won", "lost", None
    valid_transitions: List[str] = field(default_factory=list)
    sla_hours: Optional[int] = None
    required_fields: List[str] = field(default_factory=list)


@dataclass
class PackSpecializedAgent:
    agent_id: str
    name: str
    department: str  # marketing, sales, hr, support, orchestrator
    description: str
    system_prompt_template: str
    allowed_tool_ids: List[str] = field(default_factory=list)
    prohibited_actions: List[str] = field(default_factory=list)
    risk_ceiling: RiskLevel = RiskLevel.R1_INTERNAL_REVERSIBLE


@dataclass
class PackWorkflowTemplate:
    template_id: str
    name: str
    category: str
    description: str
    trigger_type: str  # event, webhook, schedule, manual
    dag_graph: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PackApprovalPolicy:
    action_key: str
    threshold_value: float
    threshold_unit: str  # percentage, currency, count
    approver_role: str
    description: str


@dataclass
class IndustryPackManifest:
    """Canonical specification contract for all OctaOS Industry Solution Packs."""

    pack_id: str
    version: str
    name: str
    summary: str
    readiness: PackReadiness = PackReadiness.CONFIGURATION
    target_verticals: List[str] = field(default_factory=list)

    # 1. Terminology Mapping
    terminology: Dict[str, str] = field(default_factory=lambda: {
        "lead": "Lead",
        "leads": "Leads",
        "account": "Account",
        "accounts": "Accounts",
        "contact": "Contact",
        "contacts": "Contacts",
        "opportunity": "Opportunity",
        "opportunities": "Opportunities",
        "pipeline": "Pipeline",
    })

    # 2. Domain Data & Schemas
    domain_models: List[str] = field(default_factory=list)
    custom_fields: List[Dict[str, Any]] = field(default_factory=list)
    pipeline_stages: List[PackPipelineStage] = field(default_factory=list)

    # 3. Specialized Agents
    agents: List[PackSpecializedAgent] = field(default_factory=list)

    # 4. Workflows & Visual DAG Templates
    workflow_templates: List[PackWorkflowTemplate] = field(default_factory=list)

    # 5. Interfaces & External Portals
    external_portals: List[str] = field(default_factory=list)
    record_tabs: List[str] = field(default_factory=lambda: ["Overview", "Qualification", "Activity", "History"])

    # 6. Connectors & Gateways
    required_connectors: List[str] = field(default_factory=list)

    # 7. Rules, Approvals & SLAs
    approval_policies: List[PackApprovalPolicy] = field(default_factory=list)
    ai_guidance_allowed: List[str] = field(default_factory=list)
    ai_guidance_prohibited: List[str] = field(default_factory=list)

    # 8. Operational KPIs
    kpi_metrics: List[Dict[str, Any]] = field(default_factory=list)

    # 9. Pre-seeded RBAC Roles
    roles: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes manifest to a clean JSON-serializable dictionary."""
        return {
            "pack_id": self.pack_id,
            "version": self.version,
            "name": self.name,
            "summary": self.summary,
            "readiness": self.readiness.value if isinstance(self.readiness, PackReadiness) else str(self.readiness),
            "target_verticals": self.target_verticals,
            "terminology": self.terminology,
            "domain_models": self.domain_models,
            "custom_fields": self.custom_fields,
            "pipeline_stages": [
                {
                    "id": s.id,
                    "label": s.label,
                    "color": s.color,
                    "is_terminal": s.is_terminal,
                    "terminal_outcome": s.terminal_outcome,
                    "valid_transitions": s.valid_transitions,
                    "sla_hours": s.sla_hours,
                    "required_fields": s.required_fields,
                }
                for s in self.pipeline_stages
            ],
            "agents": [
                {
                    "agent_id": a.agent_id,
                    "name": a.name,
                    "department": a.department,
                    "description": a.description,
                    "allowed_tool_ids": a.allowed_tool_ids,
                    "prohibited_actions": a.prohibited_actions,
                    "risk_ceiling": a.risk_ceiling.value if isinstance(a.risk_ceiling, RiskLevel) else str(a.risk_ceiling),
                }
                for a in self.agents
            ],
            "workflow_templates": [
                {
                    "template_id": w.template_id,
                    "name": w.name,
                    "category": w.category,
                    "description": w.description,
                    "trigger_type": w.trigger_type,
                }
                for w in self.workflow_templates
            ],
            "external_portals": self.external_portals,
            "record_tabs": self.record_tabs,
            "required_connectors": self.required_connectors,
            "approval_policies": [
                {
                    "action_key": p.action_key,
                    "threshold_value": p.threshold_value,
                    "threshold_unit": p.threshold_unit,
                    "approver_role": p.approver_role,
                    "description": p.description,
                }
                for p in self.approval_policies
            ],
            "ai_guidance": {
                "allowed": self.ai_guidance_allowed,
                "prohibited": self.ai_guidance_prohibited,
            },
            "kpi_metrics": self.kpi_metrics,
            "roles": self.roles,
        }
