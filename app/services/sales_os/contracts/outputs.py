"""Canonical sales outputs. Recommendations and executable actions stay separate."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ICPProfile(BaseModel):
    target_segments: list[str] = Field(default_factory=list)
    required_criteria: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    confidence: Optional[float] = None
    narrative: str = ""


class SearchPlan(BaseModel):
    query_families: list[dict] = Field(default_factory=list)
    allowed_sources: list[str] = Field(default_factory=list)
    budget_inr: float
    spent_estimate_inr: float = 0.0
    stop_conditions: list[str] = Field(default_factory=list)
    expected_outcomes: str
    notes: list[str] = Field(default_factory=list)


class SalesSignal(BaseModel):
    signal_type: str
    source: str
    observation_time: Optional[datetime] = None
    expiry_policy: str
    evidence: list[str] = Field(default_factory=list)
    fact: str
    inference: Optional[str] = None
    confidence: Optional[float] = None
    strength: Optional[float] = None


class QualificationDecision(BaseModel):
    fit_score: Optional[float] = None
    intent_score: Optional[float] = None
    evidence_quality: Optional[float] = None
    contact_readiness: Optional[float] = None
    expected_value: Optional[float] = None
    confidence: Optional[float] = None
    decision: Literal["qualified", "disqualified", "needs_review", "nurture", "suppressed", "insufficient_evidence"]
    disqualifiers: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    rationale: str
    inputs: dict = Field(default_factory=dict)
    score_version: str = "sales-os-qualification-v1"


class EvidenceAssessment(BaseModel):
    status: Literal["verified", "inference", "conflicting", "unavailable"]
    supported_claims: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    allowed_uses: list[str] = Field(default_factory=list)
    confidence: Optional[float] = None


class OutreachDraft(BaseModel):
    subject: str = ""
    body: str = ""
    channel: str = "email"
    evidence_refs: list[str] = Field(default_factory=list)
    policy_status: Literal["not_submitted", "allow", "deny", "require_approval"] = "not_submitted"
    sent: bool = False


class ReplyAssessment(BaseModel):
    intent: str
    objection: Optional[str] = None
    opt_out: bool = False
    requested_action: str
    confidence: Optional[float] = None
    normalized: bool = True


class PolicyDecisionContract(BaseModel):
    decision: Literal["allow", "deny", "require_approval"]
    rule_ids: list[str]
    scope: str = "tenant"
    reasons: list[str] = Field(default_factory=list)
    expires_at: Optional[datetime] = None
    llm_may_override: bool = False


class DealRoomAction(BaseModel):
    current_state: str
    proposed_transition: str
    destination: Optional[str] = None
    preconditions: list[str] = Field(default_factory=list)
    idempotency_key: str
    applied: bool = False
    reason: str = ""


class SourceOutcome(BaseModel):
    source: str
    cost: Optional[float] = None
    currency: str = "INR"
    meetings: int = 0
    opportunities: int = 0
    revenue: Optional[float] = None
    revenue_confidence: Optional[float] = None
    sample_size: int = 0
    counted_deal_ids: list[str] = Field(default_factory=list)
    attribution_is_causal: bool = False


class ExperimentReport(BaseModel):
    experiment_id: str
    sample_size: int
    recommendation: str
    uncertainty: str
    sufficient_sample: bool


class BuyingCommitteeMap(BaseModel):
    members: list[dict] = Field(default_factory=list)
    missing_roles: list[str] = Field(default_factory=list)
    single_threaded: bool = True
    confidence: Optional[float] = None


class CadenceDecision(BaseModel):
    eligible: bool
    next_action: str
    reason: str
    idempotency_key: str


class MeetingHandoff(BaseModel):
    scheduling_status: Literal["needs_confirmation", "insufficient_detail", "suppressed"]
    attendees: list[str] = Field(default_factory=list)
    agenda: list[str] = Field(default_factory=list)
    owner: Optional[str] = None
    calendar_written: bool = False


class ReconciliationResult(BaseModel):
    proposed_changes: list[dict] = Field(default_factory=list)
    conflicts: list[dict] = Field(default_factory=list)
    applied: list[dict] = Field(default_factory=list)
    status: Literal["applied", "pending", "quarantined", "unchanged"]


class SalesRiskIncident(BaseModel):
    severity: Literal["info", "warning", "critical"]
    scope: str
    evidence: list[str] = Field(default_factory=list)
    containment: str


class EvaluationReport(BaseModel):
    metric_changes: list[str] = Field(default_factory=list)
    failed_cases: list[str] = Field(default_factory=list)
    severity: Literal["none", "low", "high"]
    release_recommendation: Literal["promote_candidate", "hold"]


class PlaybookUpdate(BaseModel):
    status: Literal["review_required", "pending_approval", "rejected"]
    source_refs: list[str] = Field(default_factory=list)
    applied: bool = False
    reason: str
