"""Pydantic Contracts for the 9-Role Campaign Creative Operating System.

Workstream B:
- Typed input/output contracts between all pipeline stages
- Guaranteed schema validation and serializability
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator

from app.services.marketing.compiler.prompt_compiler import CreativeIntentJSON, VideoShotPlan


class BrandStrategyBrief(BaseModel):
    """Output from Role 1: Brand Strategist."""
    core_narrative: str = Field(..., description="Central thematic narrative for the campaign")
    tone_keywords: List[str] = Field(default_factory=list, description="Authoritative tone adjectives")
    target_persona: str = Field(..., description="Target buyer or audience segment")
    key_differentiators: List[str] = Field(default_factory=list, description="Defensible product advantages")
    approved_evidence_ids: List[str] = Field(default_factory=list, description="Referenced evidence records")
    prohibited_topics: List[str] = Field(default_factory=list, description="Taboos or non-approved claims")

    @field_validator("tone_keywords", "key_differentiators", "approved_evidence_ids", "prohibited_topics", mode="before")
    @classmethod
    def normalize_lists(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        if isinstance(v, list):
            return [str(item) for item in v]
        return []


class VisualIdentityTokens(BaseModel):
    """Output from Role 2: Visual Director."""
    primary_color: str = "#059669"
    secondary_color: str = "#0F172A"
    accent_color: str = "#38BDF8"
    aesthetic_mood: str = "Cinematic architectural minimalism, high-contrast authentic textures"
    photography_archetype: str = "35mm corporate editorial lookbook"
    sref_url: Optional[str] = None


class CampaignDayOutline(BaseModel):
    """Single-day narrative step in the campaign arc."""
    day: int
    theme: str
    narrative_focus: str  # e.g., "Problem Agitation", "Case Study Proof", "Product Teardown", "Executive Vision"
    suggested_hook_angle: str
    target_cta_intent: str


class CampaignNarrativeArc(BaseModel):
    """Output from Role 3: Narrative Architect."""
    campaign_title: str
    total_days: int
    days_outline: List[CampaignDayOutline]


class PlatformPostDraft(BaseModel):
    """Output from Role 4: Platform Adapter."""
    platform: str
    day: int
    hook: str
    body_content: str
    cta_sentence: str
    hashtags: List[str] = Field(default_factory=list)
    formatted_full_post: str

    @field_validator("hashtags", mode="before")
    @classmethod
    def normalize_hashtags(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            return [h.strip() for h in v.replace(",", " ").split() if h.strip()]
        if isinstance(v, list):
            return [str(item) for item in v]
        return []


class CallToActionSpec(BaseModel):
    """Output from Role 5: Offer/CTA Engineer."""
    cta_copy: str
    action_type: str = "demo_request"  # demo_request, audit_signup, resource_download, comment_dialogue
    friction_level: str = "low"


class BrandDNAProfile(BaseModel):
    """Output from Agent 1: Brand DNA & Tone Synthesizer."""
    company_name: str
    brand_voice_summary: str
    tone_keywords: List[str] = Field(default_factory=list)
    vocabulary_allowed: List[str] = Field(default_factory=list)
    banned_words: List[str] = Field(default_factory=list)
    core_values: List[str] = Field(default_factory=list)

    @field_validator("tone_keywords", "vocabulary_allowed", "banned_words", "core_values", mode="before")
    @classmethod
    def normalize_str_lists(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        if isinstance(v, list):
            return [str(x) for x in v if x]
        return []


class ProductCatalogSnapshot(BaseModel):
    """Output from Agent 2: Product & Service Catalog Specialist."""
    products_count: int = 0
    products: List[Dict[str, Any]] = Field(default_factory=list)
    core_usps: List[str] = Field(default_factory=list)
    highlighted_offers: List[str] = Field(default_factory=list)


class AudiencePersonaSpec(BaseModel):
    """Output from Agent 3: ICP Persona & Audience Intelligence Agent."""
    target_persona: str
    acute_pain_points: List[str] = Field(default_factory=list)
    desired_outcomes: List[str] = Field(default_factory=list)
    buying_objections: List[str] = Field(default_factory=list)
    resonance_triggers: List[str] = Field(default_factory=list)


class EvidenceProofCurator(BaseModel):
    """Output from Agent 4: Evidence & Truth Claim Curator."""
    approved_evidence_ids: List[str] = Field(default_factory=list)
    approved_claims: List[Dict[str, Any]] = Field(default_factory=list)
    verified_metrics: List[str] = Field(default_factory=list)
    prohibited_claims: List[str] = Field(default_factory=list)


class ContextRadarSignal(BaseModel):
    """Output from Agent 5: Context Radar & Cultural Horizon Sentinel."""
    upcoming_calendar_events: List[Dict[str, Any]] = Field(default_factory=list)
    active_news_signals: List[Dict[str, Any]] = Field(default_factory=list)
    timely_hooks: List[str] = Field(default_factory=list)


class BrandContextAnchor(BaseModel):
    """Consolidated immutable brand & promotional grounding anchor from Agents 1-5."""
    company_name: str
    website: str = ""
    industry: str
    promo_goal: str
    brand_dna: BrandDNAProfile
    product_catalog: ProductCatalogSnapshot
    audience_persona: AudiencePersonaSpec
    proof_points: EvidenceProofCurator
    context_radar: ContextRadarSignal
    visual_tokens: VisualIdentityTokens
    compliance_rules: List[str] = Field(default_factory=list)


class TimeSlotSpec(BaseModel):
    """Specification for a distinct publication time slot within a campaign day."""
    day: int
    slot_index: int
    slot_label: str  # e.g., "Morning Anchor (09:00 UTC)", "Evening Deep-Dive (17:00 UTC)"
    scheduled_time_utc: str
    platform: str
    thematic_angle: str
    target_action: str
    product_feature_focus: Optional[str] = None


class TimeSlotSchedulePlan(BaseModel):
    """Output from Agent 7: Chronological Time-Slot Cadence Scheduler."""
    total_days: int
    posts_per_day: int
    slots: List[TimeSlotSpec] = Field(default_factory=list)


class HookAngleVariant(BaseModel):
    """Output from Agent 9: Viral Hook & Headline Engineer."""
    winning_hook: str
    hook_variants: List[Dict[str, str]] = Field(default_factory=list)
    angle_type: str = "contrarian_insight"  # contrarian_insight, proof_metric, curiosity_gap


class FactCheckAuditResult(BaseModel):
    """Output from Agent 13: Deterministic Fact-Checking & Claim Grounding Verifier."""
    groundedness_score: float = Field(..., ge=0.0, le=1.0)
    all_claims_grounded: bool = True
    unsupported_claims: List[str] = Field(default_factory=list)
    cited_evidence_ids: List[str] = Field(default_factory=list)


class ComplianceAuditResult(BaseModel):
    """Output from Agent 14: Brand Voice & Compliance Sentinel."""
    compliance_passed: bool = True
    violations: List[str] = Field(default_factory=list)
    brand_voice_score: float = Field(..., ge=0.0, le=1.0)
    banned_words_detected: List[str] = Field(default_factory=list)


class CMOExecutiveVerdict(BaseModel):
    """Output from Agent 15: Chief Marketing Officer (CMO / Top-Level Orchestrator Agent)."""
    campaign_title: str
    overall_confidence: float = Field(..., ge=0.0, le=1.0)
    is_approved: bool = True
    executive_summary: str = ""
    total_slots_planned: int = 0
    approved_slots_count: int = 0
    needs_review_count: int = 0


class CritiqueScoreCard(BaseModel):
    """Output from Role 9: Critic / Judge."""
    groundedness_score: float = Field(..., ge=0.0, le=1.0)
    unsupported_claims: List[str] = Field(default_factory=list)
    platform_fit_score: float = Field(..., ge=0.0, le=1.0)
    brand_voice_score: float = Field(..., ge=0.0, le=1.0)
    compliance_passed: bool = True
    compliance_issues: List[str] = Field(default_factory=list)
    overall_confidence: float = Field(..., ge=0.0, le=1.0)
    is_approved: bool = True
    critique_notes: str = ""

    @field_validator("critique_notes", mode="before")
    @classmethod
    def normalize_critique_notes(cls, v: Any) -> str:
        if isinstance(v, list):
            return "\n".join(str(item) for item in v if item)
        if v is None:
            return ""
        return str(v)

    @field_validator("unsupported_claims", "compliance_issues", mode="before")
    @classmethod
    def normalize_string_lists(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            return [v] if v.strip() else []
        if isinstance(v, list):
            return [str(item) for item in v]
        return []
