"""Versioned contracts for the parallel search pipeline.

These models are the boundary between search, evidence, and the existing
Sales OS. Retrieved page text is data. It is never a source of permissions.
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


class IntentCategory(str, Enum):
    DIRECT_BUYING_INTENT = "DIRECT_BUYING_INTENT"
    ACTIVE_VENDOR_EVALUATION = "ACTIVE_VENDOR_EVALUATION"
    EXPRESSED_BUSINESS_PROBLEM = "EXPRESSED_BUSINESS_PROBLEM"
    RELEVANT_TRIGGER_EVENT = "RELEVANT_TRIGGER_EVENT"
    GENERAL_INTEREST = "GENERAL_INTEREST"
    IRRELEVANT = "IRRELEVANT"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class CampaignIntentSpec(BaseModel):
    schema_version: str = "1.0"
    campaign_id: str
    tenant_id: str
    correlation_id: str = Field(default_factory=new_id)
    query: str
    industries: list[str] = Field(default_factory=list)
    buyer_roles: list[str] = Field(default_factory=list)
    geography: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)
    freshness: str = "30_days"
    budget_inr: float = 700.0
    monthly_limit_inr: float = 700.0
    evidence_required: bool = True
    offer: str = ""
    seed_urls: list[str] = Field(default_factory=list)


class SearchTask(BaseModel):
    schema_version: str = "1.0"
    task_id: str = Field(default_factory=new_id)
    correlation_id: str
    campaign_id: str
    tenant_id: str
    method: str
    provider: str
    operation: str
    query: str
    intent_hypothesis: str
    freshness_window: str
    exclusions: list[str] = Field(default_factory=list)
    estimated_cost_inr: float = 0.0
    stop_condition: str
    priority: int = 50
    idempotency_key: str
    status: str = "planned"
    reason: str = ""
    selection_reason: str = ""
    parent_record_id: Optional[str] = None
    depth: int = 0
    attempt: int = 0
    retry_limit: int = 2
    failure_class: Optional[str] = None
    prompt_version: str = "search-strategy-v1-deterministic"


class DiscoveryRecord(BaseModel):
    schema_version: str = "1.0"
    record_id: str = Field(default_factory=new_id)
    correlation_id: str
    task_id: str
    tenant_id: str
    method: str
    provider: str
    original_url: str
    canonical_url: str
    title: str = ""
    snippet: str = ""
    page_excerpt: str = ""
    published_at: Optional[datetime] = None
    retrieved_at: datetime = Field(default_factory=utcnow)
    provider_native_id: Optional[str] = None
    dedupe_key: str
    company_name: str = ""
    company_domain: Optional[str] = None
    contact_name: str = ""
    contact_email: str = ""


class LeadEvidence(BaseModel):
    schema_version: str = "1.0"
    record_id: str
    claim: str
    passage: str
    source_url: str
    provider: str
    published_at: Optional[datetime] = None
    retrieved_at: datetime
    verification_state: str
    explicit: bool = False
    freshness_ok: Optional[bool] = None
    notes: list[str] = Field(default_factory=list)


class QualificationAssessment(BaseModel):
    schema_version: str = "1.0"
    record_id: str
    rule_version: str = "score-rules-v1"
    intent: IntentCategory
    intent_strength: float
    icp_fit: float
    freshness: float
    evidence_quality: float
    contactability: float
    composite: float
    hard_disqualifiers: list[str] = Field(default_factory=list)
    decision: str
    rationale: str
    uncertainty: list[str] = Field(default_factory=list)


class UsageLedgerEntry(BaseModel):
    schema_version: str = "1.0"
    entry_id: str = Field(default_factory=new_id)
    tenant_id: str
    correlation_id: str
    provider: str
    operation: str
    estimated_cost_inr: float
    actual_cost_inr: float = 0.0
    currency: str = "INR"
    status: str
    task_id: Optional[str] = None


class SkillDefinition(BaseModel):
    schema_version: str = "1.0"
    skill_id: str
    name: str
    version: str
    description: str
    owner: str
    agent_class: Optional[str] = None
    deterministic: bool = False
    required_permissions: list[str] = Field(default_factory=list)
    side_effects: list[str] = Field(default_factory=list)
    approval_required: bool = False
    contract_id: Optional[str] = None


class QualifiedCandidate(BaseModel):
    record: DiscoveryRecord
    evidence: LeadEvidence
    assessment: QualificationAssessment


class SearchBatch(BaseModel):
    schema_version: str = "1.0"
    job_id: str
    correlation_id: str
    tenant_id: str
    status: str
    tasks: list[SearchTask]
    records: list[DiscoveryRecord]
    candidates: list[QualifiedCandidate]
    qualified: list[QualifiedCandidate]
    rejected: list[QualifiedCandidate]
    ledger: list[UsageLedgerEntry]
    report: str
    resumed: bool = False

    def model_dump_public(self) -> dict[str, Any]:
        payload = self.model_dump(mode="json")
        for record in payload.get("records") or []:
            record.pop("page_excerpt", None)
        return payload
