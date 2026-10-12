"""
boardroom.py — Pydantic schemas for boardroom V2.

These schemas are used to:
1. Validate LLM JSON output (agents must return conforming objects)
2. Provide typed API response shapes for the frontend
3. Enable the grounding check (evidence_ids must reference real evidence)
"""
from __future__ import annotations

from typing import Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime


# ---------------------------------------------------------------------------
# Agent output schemas (validated after each LLM call)
# ---------------------------------------------------------------------------

class Finding(BaseModel):
    """A single claim made by a specialist agent, grounded to evidence."""
    claim: str
    evidence_ids: list[str] = Field(default_factory=list)  # must reference MeetingEvidence.source_ref
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class ProposedAction(BaseModel):
    """An action recommended by a specialist."""
    assigned_to: str
    description: str
    evidence_ids: list[str] = Field(default_factory=list)


class SpecialistAnalysis(BaseModel):
    """Validated output from a single specialist agent's analysis phase."""
    agent: str
    stance: Literal["support", "oppose", "neutral"] = "neutral"
    summary: str
    findings: list[Finding] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    confidence_rationale: Optional[str] = None


class AgentCritique(BaseModel):
    """Validated output from a specialist agent's critique of other analyses."""
    agent: str
    agreement_points: list[str] = Field(default_factory=list)
    objections: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)


class SynthesisActionItem(BaseModel):
    """An action item in the CEO synthesis output."""
    assigned_to: str
    description: str
    sources: list[str] = Field(default_factory=list)


class CEOSynthesis(BaseModel):
    """Validated output from the CEO AI synthesis phase."""
    executive_summary: str
    key_findings: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    financial_impact: list[str] = Field(default_factory=list)
    operational_impact: list[str] = Field(default_factory=list)
    risk_matrix: list[str] = Field(default_factory=list)
    alternative_options: list[str] = Field(default_factory=list)
    expert_disagreements: list[str] = Field(default_factory=list)
    data_gaps: list[str] = Field(default_factory=list)
    recommended_action: str = ""
    sources: list[str] = Field(default_factory=list)
    action_items: list[SynthesisActionItem] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# API response schemas (frontend consumption)
# ---------------------------------------------------------------------------

class MeetingEventOut(BaseModel):
    id: str
    meeting_id: str
    seq: int
    event_type: str
    phase: Optional[str] = None
    actor: Optional[str] = None
    payload: dict = Field(default_factory=dict)
    created_at: datetime

    class Config:
        from_attributes = True


class MeetingEvidenceOut(BaseModel):
    id: str
    meeting_id: str
    source_ref: str
    source_type: str
    trust_score: Optional[int] = None
    freshness_score: Optional[int] = None
    reliability_score: Optional[int] = None
    completeness_score: Optional[int] = None
    excerpt: Optional[str] = None
    redacted: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class MeetingActionOut(BaseModel):
    id: str
    meeting_id: str
    action_type: str
    assigned_to: str
    description: str
    risk_tier: str
    status: str
    idempotency_key: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejected_by: Optional[str] = None
    rejected_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    result: Optional[dict] = None
    evidence_ids: list[str] = Field(default_factory=list)
    created_at: datetime

    class Config:
        from_attributes = True


class MeetingActionApprove(BaseModel):
    approved_by: str = "user"  # user ID or username


class MeetingActionReject(BaseModel):
    rejected_by: str = "user"
    reason: Optional[str] = None


class ConfidenceBreakdown(BaseModel):
    """Derived confidence score with per-component breakdown for UI display."""
    overall: int = Field(ge=0, le=100)
    evidence_trust: int = Field(ge=0, le=100)
    evidence_freshness: int = Field(ge=0, le=100)
    agent_agreement: int = Field(ge=0, le=100)
    grounding_pass_rate: int = Field(ge=0, le=100)
    rationale: str = ""


# ---------------------------------------------------------------------------
# 12-Stage Boardroom V3 Schemas (Charter, Options, Positions, ADR)
# ---------------------------------------------------------------------------

class DecisionCharterOut(BaseModel):
    id: str
    meeting_id: str
    decision_type: str
    question: str
    decision_owner: str
    approvers: list[str] = Field(default_factory=list)
    deadline: Optional[datetime] = None
    cost_of_delay_per_week: float = 0.0
    criteria_weights: list[dict] = Field(default_factory=list)
    created_at: datetime

    class Config:
        from_attributes = True


class MeetingOptionOut(BaseModel):
    id: str
    meeting_id: str
    option_code: str
    title: str
    description: str
    is_do_nothing: bool = False
    is_pilot: bool = False
    reversibility: str = "medium"
    financial_model: dict = Field(default_factory=dict)
    weighted_score: float = 0.0
    created_at: datetime

    class Config:
        from_attributes = True


class MeetingPositionOut(BaseModel):
    id: str
    meeting_id: str
    round: int = 1
    agent: str
    preferred_option: Optional[str] = None
    position_statement: str
    evidence_ids: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    confidence: int = Field(default=50, ge=0, le=100)
    what_would_change_mind: Optional[str] = None
    is_veto: bool = False
    veto_reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DissentRecordOut(BaseModel):
    id: str
    meeting_id: str
    agent: str
    dissent_position: str
    preferred_option: Optional[str] = None
    addressed: bool = False
    override_rationale: Optional[str] = None
    requires_human_signoff: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class DecisionOutcomeOut(BaseModel):
    id: str
    meeting_id: str
    review_milestone: str
    review_date: datetime
    tripwires: list[str] = Field(default_factory=list)
    tripwire_triggered: bool = False
    predicted_metrics: dict = Field(default_factory=dict)
    actual_metrics: dict = Field(default_factory=dict)
    agent_brier_scores: dict = Field(default_factory=dict)
    reviewed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ChairmanInterventionRequest(BaseModel):
    """Directive or constraint injected by the human Chair mid-deliberation."""
    directive: str
    target_agent: Optional[str] = None  # None = all board members
    override_veto: bool = False

