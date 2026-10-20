"""Pydantic schemas for the Dynamic HR Document Intelligence & Workflow Builder Platform."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# --- TEMPLATE HUB SCHEMAS ---

class TemplateUploadRequest(BaseModel):
    category: str = Field(default="onboarding", description="e.g. offer, agreement, compliance, nda, custom")
    name: str
    description: Optional[str] = None
    folder_path: str = "/"
    tags: List[str] = Field(default_factory=list)
    format: str = Field(default="docx", description="'docx' or 'html'")
    raw_content: Optional[str] = None  # for HTML / text


class DetectedPlaceholder(BaseModel):
    expression: str
    inferred_key: str
    context_type: str  # 'paragraph', 'table', 'header', 'content_control'
    location_index: int
    sample_text: Optional[str] = None


class ProposedFieldMapping(BaseModel):
    template_expression: str
    canonical_key: str  # e.g. 'candidate.full_name', 'compensation.annual_ctc'
    data_type: str  # 'string', 'money', 'date', 'integer', 'boolean'
    source_requirement: str  # 'candidate', 'hr_input', 'system_generated', 'company_policy'
    is_required: bool = True
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    validation_rule: Optional[str] = None


class DetectedClause(BaseModel):
    clause_type: str  # 'confidentiality', 'non_compete', 'governing_law', 'clawback', 'probation'
    title: str
    paragraph_index: int
    is_standard: bool
    summary: str


class TemplateAnalysisResponse(BaseModel):
    template_id: str
    version_id: str
    format: str
    content_sha256: str
    placeholders: List[DetectedPlaceholder]
    proposed_mappings: List[ProposedFieldMapping]
    detected_clauses: List[DetectedClause]
    table_count: int
    paragraph_count: int


class TemplatePublishRequest(BaseModel):
    approved_mappings: List[ProposedFieldMapping]


# --- WORKFLOW BUILDER SCHEMAS ---

class WorkflowNode(BaseModel):
    id: str
    name: str
    type: str  # 'candidate_intake', 'evidence_extraction', 'condition_branch', 'document_generation', 'approval_gate', 'delivery_dispatch'
    config: Dict[str, Any] = Field(default_factory=dict)
    position: Optional[Dict[str, float]] = None  # UI graph coordinates (x, y)


class WorkflowEdge(BaseModel):
    id: str
    source: str
    target: str
    source_handle: str = "default"
    target_handle: str = "default"
    condition: Optional[str] = None  # e.g. "context.employment_type == 'permanent'"
    label: Optional[str] = None


class TemplateVersionRef(BaseModel):
    template_id: str
    version_id: str
    template_name: str
    content_sha256: str


class WorkflowGraphSchema(BaseModel):
    nodes: List[WorkflowNode]
    edges: List[WorkflowEdge]


class WorkflowGraphContract(BaseModel):
    name: str
    description: Optional[str] = None
    nodes: List[WorkflowNode]
    edges: List[WorkflowEdge]
    template_references: List[TemplateVersionRef] = Field(default_factory=list)
    provenance: Dict[str, Any] = Field(default_factory=dict)  # {"generator": "ai" | "rule_based_fallback", "model": str}


class AIPipelineGenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=2000)
    job_role: Optional[str] = None
    requisition_id: Optional[str] = None


class AIPipelineGenerateResponse(BaseModel):
    graph: WorkflowGraphContract
    is_valid: bool
    warnings: List[str] = Field(default_factory=list)
    validation_errors: List[str] = Field(default_factory=list)
    generator_used: str  # "llm" | "rule_based_fallback"


class NodeTypeMetadata(BaseModel):
    node_type: str
    label: str
    category: str
    description: str
    icon: str
    default_config: Dict[str, Any] = Field(default_factory=dict)
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)


class WorkflowDefinitionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    graph_schema: WorkflowGraphSchema


class WorkflowDefinitionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    graph_schema: Optional[WorkflowGraphSchema] = None


class WorkflowTestRunRequest(BaseModel):
    graph_schema: WorkflowGraphSchema
    sample_context: Dict[str, Any]


class WorkflowTestRunResponse(BaseModel):
    is_valid: bool
    traversed_path: List[str]
    evaluated_documents: List[str]
    required_candidate_fields: List[str]
    validation_errors: List[str] = Field(default_factory=list)


# --- CANDIDATE PORTAL & INTAKE SCHEMAS ---

class SynthesizedIntakeField(BaseModel):
    canonical_key: str
    label: str
    data_type: str
    is_required: bool
    description: Optional[str] = None
    sample_placeholder: Optional[str] = None


class RequiredDocumentItem(BaseModel):
    document_category: str  # 'passport', 'national_id', 'resume', 'tax_form', 'degree_certificate'
    title: str
    description: str
    is_mandatory: bool = True
    accepted_mimes: List[str] = Field(default_factory=lambda: ["application/pdf", "image/jpeg", "image/png"])


class CandidatePortalSessionResponse(BaseModel):
    instance_id: str
    candidate_name: str
    role_title: str
    company_name: str
    status: str
    expires_at: datetime
    synthesized_fields: List[SynthesizedIntakeField]
    required_documents: List[RequiredDocumentItem]
    uploaded_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    field_values: Dict[str, Any] = Field(default_factory=dict)


class CandidateIntakeSubmitRequest(BaseModel):
    field_values: Dict[str, Any]


# --- EVIDENCE RECONCILIATION SCHEMAS ---

class EvidenceExtractionResult(BaseModel):
    document_id: str
    document_category: str
    extracted_fields: Dict[str, Dict[str, Any]]  # canonical_key -> {value, confidence, page, snippet}


class FieldConflictItem(BaseModel):
    canonical_key: str
    candidate_value: Optional[Any] = None
    extracted_value: Optional[Any] = None
    source_snippet: Optional[str] = None
    confidence: float
    reason: str


class ReconciliationSummary(BaseModel):
    total_fields: int
    reconciled_count: int
    conflict_count: int
    missing_required_count: int
    conflicts: List[FieldConflictItem]
    is_blocked: bool


# --- REVIEW STUDIO SCHEMAS ---

class DraftPreviewPage(BaseModel):
    page_number: int
    html_content: str
    editable_paragraph_indices: List[int] = Field(default_factory=list)


class DraftPreviewResponse(BaseModel):
    draft_id: str
    document_name: str
    template_version_id: str
    current_approval_status: str
    content_sha256: str
    field_values: Dict[str, Any]
    pages: List[DraftPreviewPage]
    conflicts: List[FieldConflictItem]
    revisions: List[Dict[str, Any]]
    comments: List[Dict[str, Any]]


class DraftEditRequest(BaseModel):
    field_overrides: Optional[Dict[str, Any]] = None
    paragraph_updates: Optional[Dict[int, str]] = None  # paragraph_idx -> new text content
    edit_summary: str = "User edited document text"


class AddReviewCommentRequest(BaseModel):
    paragraph_index: Optional[int] = None
    comment_text: str


class DraftApprovalRequest(BaseModel):
    approver_role: str
    rationale: Optional[str] = None


class DraftScheduleRequest(BaseModel):
    scheduled_for: datetime
    timezone: str = "UTC"
    recipient_email: str
