"""
Pydantic schemas for the Enterprise HR Agentic AI System.
Defines typed contracts for agent tasks, evidence provenance, risk classification, and copilot dialogue.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


class RiskTier(str, Enum):
    R0_READ_ONLY = "R0"
    R1_LOW_IMPACT = "R1"
    R2_REVERSIBLE = "R2"
    R3_MATERIAL = "R3"
    R4_HIGH_CONSEQUENCE = "R4"
    R5_PROHIBITED = "R5"


class AutonomyLevel(str, Enum):
    L0_INFORMATIONAL = "L0"
    L1_SUGGESTIVE = "L1"
    L2_BOUNDED_EXECUTION = "L2"
    L3_APPROVAL_GATED = "L3"
    L4_RESTRICTED = "L4"


class EvidenceReference(BaseModel):
    source_type: str = Field(..., description="policy_document, database_record, timesheet, scorecard")
    source_id: str
    citation: str
    confidence: float = 1.0


class Finding(BaseModel):
    severity: str = "info"  # info, warning, critical
    code: str
    message: str
    field: Optional[str] = None


class ProposedAction(BaseModel):
    action_type: str  # e.g., "leave.approve", "policy.update", "employee.onboard"
    title: str
    resource_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    risk_tier: RiskTier = RiskTier.R1_LOW_IMPACT
    requires_approval: bool = False
    approval_request_id: Optional[str] = None
    executed: bool = False


class AgentTaskResult(BaseModel):
    task_id: str
    agent_id: str
    intent: str
    status: str = "completed"  # pending, in_progress, completed, awaiting_approval, failed
    summary: str
    evidence: List[EvidenceReference] = Field(default_factory=list)
    findings: List[Finding] = Field(default_factory=list)
    proposed_actions: List[ProposedAction] = Field(default_factory=list)
    risk_assessment: Dict[str, Any] = Field(default_factory=dict)


class LeaveCoverageEvaluation(BaseModel):
    employee_id: str
    employee_name: str
    leave_type: str
    start_date: str
    end_date: str
    days_requested: float
    current_balance: float
    projected_balance: float
    coverage_score: float  # 0.0 to 1.0
    is_staffing_adequate: bool
    conflicting_leaves_count: int
    department_team_size: int
    active_in_office_count: int
    risk_tier: RiskTier
    requires_approval: bool
    explanation: str


class CopilotMessage(BaseModel):
    role: str  # user, assistant, system
    content: str
    context_submodule: Optional[str] = None
    resource_id: Optional[str] = None


class CopilotChatRequest(BaseModel):
    message: str
    messages: Optional[List[Dict[str, Any]]] = None
    context_pillar: Optional[str] = "people"  # people, talent, compensation, culture
    context_submodule: Optional[str] = "employees"
    resource_id: Optional[str] = None


class CopilotChatResponse(BaseModel):
    conversation_id: str
    reply: str
    specialist_agent: str
    autonomy_level: AutonomyLevel
    task_result: Optional[AgentTaskResult] = None
