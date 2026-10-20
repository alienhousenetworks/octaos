from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from decimal import Decimal
from enum import Enum


class FindingSeverity(str, Enum):
    CRITICAL = "critical"      # Releases strictly blocked
    HIGH = "high"              # Requires explicit executive override
    MEDIUM = "medium"          # Requires HR note / review
    LOW = "low"                # Advisory telemetry
    INFO = "info"              # Audit information


class FindingStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    REVIEW_REQUIRED = "review_required"
    UNAVAILABLE = "unavailable"  # Never defaults to pass on service failure


class VerificationFinding(BaseModel):
    finding_id: str
    rule_id: str
    category: str  # "schema_tokens", "salary_band", "clause_integrity", "cross_document"
    severity: FindingSeverity
    status: FindingStatus
    explanation: str
    expected_value: Optional[str] = None
    observed_value: Optional[str] = None
    source_references: List[str] = []
    policy_version: Optional[str] = None
    remediation: Optional[str] = None


class VerificationReport(BaseModel):
    packet_id: str
    artifact_sha256: str
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)
    overall_eligibility: Literal["BLOCKED", "REVIEW_REQUIRED", "ELIGIBLE_FOR_APPROVAL"]
    findings: List[VerificationFinding] = []
    engine_metadata: Dict[str, Any] = {}


class CompensationSnapshot(BaseModel):
    currency: str = "USD"
    annual_base: Decimal
    variable_compensation: Optional[Decimal] = None
    effective_date: str
    approved_band_id: Optional[str] = None


class TemplateUploadRequest(BaseModel):
    document_type: str  # 'offer_letter', 'appointment_letter', 'employment_contract', 'nda'
    name: str
    description: Optional[str] = None
    format: str = "html"  # 'html', 'markdown', 'docx'
    raw_content: Optional[str] = None


class TemplateVersionSummary(BaseModel):
    id: str
    template_id: str
    tenant_id: str
    version: int
    format: str
    status: str
    content_sha256: str
    published_at: Optional[datetime] = None
    created_at: datetime


class GeneratePacketRequest(BaseModel):
    candidate_id: str
    application_id: Optional[str] = None
    requisition_id: Optional[str] = None
    override_variables: Dict[str, Any] = {}



class ArtifactApprovalRequest(BaseModel):
    packet_id: str
    artifact_id: str
    expected_artifact_sha256: str
    decision: Literal["approved", "rejected"] = "approved"
    rationale: Optional[str] = None


class CandidateAcceptRequest(BaseModel):
    token: str
    confirmed: bool = True
