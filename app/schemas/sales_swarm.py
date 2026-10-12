"""Schemas for the 20-Agent Autonomous Sales Organization (ASO).

Defines structured input/output contracts for:
- Field Rep Layer: Agents 11 & 12
- Account Executive Layer: Agents 13, 14 & 15
- Sales Manager & RevOps Layer: Agents 16, 17 & 18
- Growth & Learning Layer: Agents 19 & 20
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


# ==============================================================================
# Field Rep Layer (Agents 11 & 12)
# ==============================================================================

class RouteStop(BaseModel):
    account_id: str
    company_name: str
    address: str
    latitude: float
    longitude: float
    contact_name: str
    contact_phone: str
    scheduled_window_start: str  # e.g., "10:30 AM"
    scheduled_window_end: str    # e.g., "11:30 AM"
    priority_score: float        # Derived from Agent 5 timing score
    estimated_meeting_duration_min: int = 45


class TerritoryRoutePlan(BaseModel):
    rep_id: str
    date: str
    total_travel_distance_km: float
    estimated_travel_time_min: float
    stops: List[RouteStop] = Field(default_factory=list)
    unplanned_nearby_prospects: List[Dict[str, Any]] = Field(default_factory=list)
    optimization_metric: str = "minimized_travel_time"


class StructuredMeetingNote(BaseModel):
    attendees: List[str] = Field(default_factory=list)
    client_pain_points: List[str] = Field(default_factory=list)
    competitor_mentions: List[str] = Field(default_factory=list)
    budget_discussed: Optional[float] = None
    timeline_stated: Optional[str] = None
    commitments_made_by_rep: List[str] = Field(default_factory=list)
    commitments_made_by_client: List[str] = Field(default_factory=list)


class FieldVisitSummary(BaseModel):
    deal_room_id: str
    rep_id: str
    audio_language_detected: str = "en-US"
    raw_transcript: str
    structured_note: StructuredMeetingNote
    crm_field_updates: Dict[str, Any] = Field(default_factory=dict)
    follow_up_draft_email: str
    follow_up_draft_whatsapp: str
    recommended_stage_transition: Optional[str] = None


# ==============================================================================
# Account Executive Layer (Agents 13, 14 & 15)
# ==============================================================================

class MEDDPICCDimension(BaseModel):
    dimension: str  # Metrics | Economic Buyer | Decision Criteria | Decision Process | Paper Process | Identify Pain | Champion | Competition
    status: str     # verified | identified | unknown | at_risk
    evidence_snippet: Optional[str] = None
    confidence: float = 1.0
    action_to_verify: Optional[str] = None


class MutualActionMilestone(BaseModel):
    milestone_name: str
    owner: str  # "vendor" | "client" | "joint"
    target_completion_date: str
    status: str = "pending"  # pending | completed | overdue


class DealStrategyReport(BaseModel):
    deal_room_id: str
    meddpicc_score: float  # 0 to 100
    meddpicc_breakdown: List[MEDDPICCDimension] = Field(default_factory=list)
    is_single_threaded: bool = True
    missing_critical_roles: List[str] = Field(default_factory=list)
    mutual_action_plan: List[MutualActionMilestone] = Field(default_factory=list)
    daily_next_best_action: Dict[str, Any] = Field(default_factory=dict)


class LineItem(BaseModel):
    sku: str
    name: str
    unit_price: float
    quantity: int
    discount_pct: float = 0.0
    total_price: float


class ProposalQuote(BaseModel):
    deal_room_id: str
    quote_number: str
    contract_term_months: int = 12
    line_items: List[LineItem] = Field(default_factory=list)
    gross_total_usd: float
    effective_discount_pct: float
    net_total_usd: float
    payment_terms: str = "Net 30"
    roi_model: Dict[str, Any] = Field(default_factory=dict)
    policy_approval_status: str = "approved"  # approved | pending_manager_approval | rejected
    generated_proposal_markdown: str


class RedlineClause(BaseModel):
    section_name: str
    original_text: str
    counterparty_proposed_text: str
    risk_severity: str  # low | medium | high | unacceptable
    playbook_guidance: str
    recommended_concession: str
    trade_off_ask: str
    escalate_to_legal: bool = False


class NegotiationStrategy(BaseModel):
    deal_room_id: str
    document_version: str
    overall_legal_risk_score: float  # 0.0 to 1.0
    clauses_analyzed: List[RedlineClause] = Field(default_factory=list)
    recommended_response_letter: str
    hard_veto_triggered: bool = False


# ==============================================================================
# Sales Manager & RevOps Layer (Agents 16, 17 & 18)
# ==============================================================================

class DealRiskAudit(BaseModel):
    deal_room_id: str
    company_name: str
    current_stage: str
    calibrated_win_prob: float
    days_in_stage: int
    risk_factors: List[str] = Field(default_factory=list)
    projected_close_date: Optional[str] = None


class PipelineForecastReport(BaseModel):
    as_of_date: str
    total_pipeline_usd: float
    commit_usd: float
    best_case_usd: float
    pipeline_coverage_ratio: float
    week_over_week_delta_usd: float
    key_deal_changes: List[Dict[str, Any]] = Field(default_factory=list)
    executive_monday_brief: str


class CallCoachingScorecard(BaseModel):
    call_id: str
    rep_id: str
    rep_name: str
    talk_listen_ratio: float
    discovery_depth_score: float
    objection_handling_score: float
    clear_next_steps_established: bool
    missed_buying_signals: List[str] = Field(default_factory=list)
    coaching_recommendations: List[str] = Field(default_factory=list)


class AISwarmQualityScorecard(BaseModel):
    agent_id: str
    evaluated_samples_count: int
    groundedness_compliance_pct: float
    human_edit_distance_avg: float
    prompt_drift_flags: List[str] = Field(default_factory=list)


class CoachingReport(BaseModel):
    rep_scorecards: List[CallCoachingScorecard] = Field(default_factory=list)
    ai_swarm_evaluations: List[AISwarmQualityScorecard] = Field(default_factory=list)
    team_training_focus: str


class RepCapacityAssignment(BaseModel):
    rep_id: str
    rep_name: str
    assigned_region: str
    assigned_account_count: int
    pipeline_capacity_utilization_pct: float
    recommended_quota_usd: float


class CapacityPlanReport(BaseModel):
    total_addressable_accounts: int
    uncovered_high_potential_accounts: int
    optimal_sales_headcount: int
    assignments: List[RepCapacityAssignment] = Field(default_factory=list)
    ai_agent_allocation_recommendations: Dict[str, int] = Field(default_factory=dict)


# ==============================================================================
# Growth & Learning Layer (Agents 19 & 20)
# ==============================================================================

class AccountHealthDiagnosis(BaseModel):
    account_id: str
    company_name: str
    health_score: float
    churn_probability: float
    risk_drivers: List[str] = Field(default_factory=list)
    upsell_indicators: List[str] = Field(default_factory=list)
    recommended_play: str  # immediate_cs_intervention | expansion_pitch | standard_renewal
    renewal_window_days: int


class ExpansionRetentionReport(BaseModel):
    accounts_audited_count: int
    at_risk_revenue_usd: float
    expansion_pipeline_usd: float
    actionable_plays: List[AccountHealthDiagnosis] = Field(default_factory=list)
    drafted_90_day_renewal_briefs: List[Dict[str, Any]] = Field(default_factory=list)


class WinLossAnalysis(BaseModel):
    closed_deals_analyzed: int
    top_winning_angles: List[str] = Field(default_factory=list)
    top_loss_reasons: List[str] = Field(default_factory=list)
    competitor_displacement_rate: Dict[str, float] = Field(default_factory=dict)


class OptimizationProposal(BaseModel):
    component_type: str  # icp_filter | outreach_prompt | objection_playbook | send_schedule
    current_version: str
    proposed_version: str
    shadow_test_sample_size: int
    improvement_metric: str
    requires_human_approval: bool = True


class LearningReport(BaseModel):
    win_loss_synthesis: WinLossAnalysis
    proposals: List[OptimizationProposal] = Field(default_factory=list)
    evaluation_benchmark_passed: bool = True
