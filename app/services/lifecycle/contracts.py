"""Typed Pydantic Contracts and Execution Envelope for OctaOS Customer Lifecycle Workforce (E1-E8).

Standardizes communication across Sales OS, Marketing Campaign OS, and Shared Lifecycle Services.
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class ExecutionStatus(str, Enum):
    COMPLETED = "COMPLETED"
    NEEDS_APPROVAL = "NEEDS_APPROVAL"
    NEEDS_INPUT = "NEEDS_INPUT"
    BLOCKED = "BLOCKED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class CampaignMode(str, Enum):
    MARKETING = "MARKETING"
    SALES = "SALES"


class ReengagementMode(str, Enum):
    SALES_REACTIVATION = "SALES_REACTIVATION"
    CUSTOMER_WINBACK = "CUSTOMER_WINBACK"
    REFERRAL = "REFERRAL"


class SuppressionDecision(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    REVIEW = "REVIEW"
    RETRY_CHECK = "RETRY_CHECK"


class ExecutedAction(BaseModel):
    action: str
    status: str = "CONFIRMED"
    external_ref: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class AgentExecutionEnvelope(BaseModel):
    """Canonical outer envelope for all Workforce E agents."""
    tenant_id: str
    request_id: str
    workflow_id: str
    agent_id: str
    agent_version: str = "1.0.0"
    actor_id: Optional[str] = None
    objective: str
    input_refs: List[str] = Field(default_factory=list)
    policy_context: Dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str
    deadline: Optional[str] = None
    status: ExecutionStatus = ExecutionStatus.COMPLETED
    output: Dict[str, Any] = Field(default_factory=dict)
    evidence_refs: List[str] = Field(default_factory=list)
    actions_executed: List[ExecutedAction] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    error_code: Optional[str] = None
    audit_ref: Optional[str] = None


# ── Agent 1: Lead Capture & Routing I/O ────────────────────────────────────
class LeadCaptureInput(BaseModel):
    source_type: str
    source_event_id: str
    lead_payload: Dict[str, Any]
    attribution_metadata: Dict[str, Any] = Field(default_factory=dict)
    existing_record_refs: List[str] = Field(default_factory=list)
    routing_policy_ref: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)


class LeadCaptureOutput(BaseModel):
    lead_id: Optional[str] = None
    match_status: str  # "NEW_RECORD", "EXACT_MATCH", "PROBABLE_DUPLICATE", "AMBIGUOUS"
    routing_decision: str  # "ASSIGNED", "ESCALATED", "FALLBACK_QUEUE", "REJECTED"
    assigned_owner: Optional[str] = None
    attribution: Dict[str, Any] = Field(default_factory=dict)
    validation_errors: List[str] = Field(default_factory=list)
    next_action: Optional[str] = None


# ── Agent 2: Lead Enrichment & Qualification I/O ──────────────────────────
class LeadEnrichmentInput(BaseModel):
    lead_id: str
    lead_record: Dict[str, Any]
    icp_profile: Dict[str, Any] = Field(default_factory=dict)
    qualification_rubric: Dict[str, Any] = Field(default_factory=dict)
    permitted_sources: List[str] = Field(default_factory=list)
    research_budget: float = 1.0


class LeadEnrichmentOutput(BaseModel):
    lead_id: str
    enrichment_fields: Dict[str, Any] = Field(default_factory=dict)
    evidence_refs: List[str] = Field(default_factory=list)
    field_provenance: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    fit_score: float = Field(0.0, ge=0.0, le=100.0)
    intent_score: float = Field(0.0, ge=0.0, le=100.0)
    completeness_score: float = Field(0.0, ge=0.0, le=100.0)
    score_breakdown: Dict[str, Any] = Field(default_factory=dict)
    qualification_status: str  # "QUALIFIED", "NURTURE", "DISQUALIFIED", "INSUFFICIENT_EVIDENCE"
    reason_codes: List[str] = Field(default_factory=list)
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    recommended_next_action: str


# ── Agent 3: Email Campaign Architect I/O ─────────────────────────────────
class EmailCampaignInput(BaseModel):
    campaign_mode: CampaignMode
    objective: str
    audience_ref: str
    audience_summary: Dict[str, Any] = Field(default_factory=dict)
    product_or_offer_refs: List[str] = Field(default_factory=list)
    brand_guidelines: Dict[str, Any] = Field(default_factory=dict)
    approved_claims: List[str] = Field(default_factory=list)
    prohibited_claims: List[str] = Field(default_factory=list)
    locale: str = "en-US"
    timezone: str = "UTC"


class EmailMessageVariant(BaseModel):
    variant_id: str
    subject_line: str
    preview_text: str
    body_markdown: str
    cta_copy: str
    cta_url_placeholder: str
    personalization_fields: List[str] = Field(default_factory=list)


class EmailCampaignOutput(BaseModel):
    campaign_mode: CampaignMode
    campaign_brief: str
    audience_ref: str
    message_variants: List[EmailMessageVariant] = Field(default_factory=list)
    personalization_schema: List[str] = Field(default_factory=list)
    approved_claim_refs: List[str] = Field(default_factory=list)
    experiment_plan: Optional[Dict[str, Any]] = None
    success_metrics: List[str] = Field(default_factory=list)
    compliance_review_requirements: List[str] = Field(default_factory=list)


# ── Agent 4: Lifecycle & Nurture Journey I/O ──────────────────────────────
class LifecycleJourneyInput(BaseModel):
    contact_ref: str
    lifecycle_state: str
    triggering_event: Dict[str, Any]
    journey_type: str  # "SALES_NURTURE", "MARKETING_NURTURE", "ONBOARDING", "ADOPTION", "RENEWAL", "WINBACK"
    journey_definition_ref: Optional[str] = None
    active_journey_refs: List[str] = Field(default_factory=list)
    timezone: str = "UTC"


class LifecycleJourneyOutput(BaseModel):
    contact_ref: str
    journey_type: str
    journey_ref: str
    previous_state: str
    new_state: str
    triggering_event_ref: Optional[str] = None
    next_action: str
    scheduled_step_refs: List[str] = Field(default_factory=list)
    eligibility_decision: str  # "ELIGIBLE", "PAUSED", "EXITED", "REDIRECTED"
    exit_reason: Optional[str] = None
    blocked_reason: Optional[str] = None


# ── Agent 5: Customer Segmentation I/O ────────────────────────────────────
class CustomerSegmentationInput(BaseModel):
    segment_objective: str
    requested_audience: Dict[str, Any]
    permitted_fields: List[str] = Field(default_factory=list)
    intended_use: str  # "marketing_email", "sales_sequence", "retargeting", "analytics"
    segment_type: str = "DYNAMIC_RULE"  # "DYNAMIC_RULE", "SNAPSHOT", "EVENT_TRIGGERED"


class CustomerSegmentationOutput(BaseModel):
    segment_ref: str
    segment_version: str = "1.0"
    segment_type: str
    normalized_definition: Dict[str, Any]
    source_fields: List[str] = Field(default_factory=list)
    inclusion_rules: List[Dict[str, Any]] = Field(default_factory=list)
    exclusion_rules: List[Dict[str, Any]] = Field(default_factory=list)
    matched_count: Optional[int] = None
    evaluated_at: str
    freshness_status: str = "FRESH"


# ── Agent 6: Deliverability & Suppression I/O ─────────────────────────────
class SuppressionCheckInput(BaseModel):
    recipient_ref: str
    recipient_email: str
    channel: str = "email"
    communication_purpose: str = "marketing"  # "marketing", "sales", "transactional"
    sender_identity_ref: Optional[str] = None
    campaign_or_sequence_ref: Optional[str] = None


class SuppressionCheckOutput(BaseModel):
    decision: SuppressionDecision  # ALLOW, BLOCK, REVIEW, RETRY_CHECK
    recipient_ref: str
    channel: str
    communication_purpose: str
    reason_codes: List[str] = Field(default_factory=list)
    suppression_match: bool = False
    frequency_capped: bool = False
    provider_health_summary: Dict[str, Any] = Field(default_factory=dict)
    checked_at: str


# ── Agent 7: Retention & Churn Signal I/O ─────────────────────────────────
class RetentionRiskInput(BaseModel):
    customer_ref: str
    account_ref: Optional[str] = None
    observation_window_days: int = 30
    usage_events: List[Dict[str, Any]] = Field(default_factory=list)
    support_events: List[Dict[str, Any]] = Field(default_factory=list)
    renewal_date: Optional[str] = None


class RetentionRiskOutput(BaseModel):
    customer_ref: str
    account_ref: Optional[str] = None
    risk_band: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL", "INSUFFICIENT_EVIDENCE"
    risk_score: Optional[float] = None
    model_version: str = "1.0"
    contributing_signals: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    recommended_intervention: str
    recommended_owner: str  # "account_executive", "customer_success", "support", "marketing_retention"
    urgency: str  # "low", "medium", "high", "immediate"


# ── Agent 8: Re-engagement & Referral I/O ─────────────────────────────────
class ReengagementInput(BaseModel):
    campaign_mode: ReengagementMode
    audience_ref: str
    customer_or_lead_refs: List[str] = Field(default_factory=list)
    approved_offers: List[Dict[str, Any]] = Field(default_factory=list)
    referral_program_ref: Optional[str] = None


class ReengagementOutput(BaseModel):
    campaign_mode: ReengagementMode
    audience_ref: str
    eligible_record_refs: List[str] = Field(default_factory=list)
    excluded_record_refs: List[str] = Field(default_factory=list)
    exclusion_reasons: Dict[str, str] = Field(default_factory=dict)
    reactivation_signals: List[Dict[str, Any]] = Field(default_factory=list)
    proposed_strategy: str
    content_refs: List[str] = Field(default_factory=list)
    offer_ref: Optional[str] = None
    approval_requirements: List[str] = Field(default_factory=list)
    success_metrics: List[str] = Field(default_factory=list)
