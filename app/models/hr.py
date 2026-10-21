"""HR lifecycle tables. People stay on candidates. A role candidacy is an application."""
import uuid
from sqlalchemy import (
    Column, String, Boolean, DateTime, ForeignKey, Integer, Text, JSON,
    Numeric, UniqueConstraint, CheckConstraint,
)
from sqlalchemy.sql import func
from app.models.base import Base


def _id() -> str:
    return str(uuid.uuid4())


class JobRequisition(Base):
    __tablename__ = "job_requisitions"
    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    organization_id = Column(String, nullable=True, index=True)
    title = Column(String, nullable=False)
    status = Column(String, nullable=False, default="draft")
    headcount_approved = Column(Integer, nullable=False, default=1)
    headcount_filled = Column(Integer, nullable=False, default=0)
    opened_at = Column(DateTime(timezone=True), nullable=True)
    opened_at_confirmed = Column(Boolean, nullable=False, default=False)
    legacy_opened_at_is_first_candidate = Column(Boolean, nullable=False, default=False)
    legacy_role_missing = Column(Boolean, nullable=False, default=False)
    legacy_salary_text = Column(String, nullable=True)
    hiring_manager_user_id = Column(String, nullable=True)
    recruiter_user_id = Column(String, nullable=True)
    target_fill_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Application(Base):
    __tablename__ = "applications"
    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    candidate_id = Column(String, ForeignKey("candidates.id"), nullable=False)
    requisition_id = Column(String, ForeignKey("job_requisitions.id"), nullable=False)
    workflow_id = Column(String, ForeignKey("workflows.id"), nullable=True)
    current_stage = Column(String, nullable=False, default="sourced")
    status = Column(String, nullable=False, default="active")
    source = Column(String, nullable=True)
    applied_at = Column(DateTime(timezone=True), nullable=True)
    applied_at_confirmed = Column(Boolean, nullable=False, default=False)
    consent_status = Column(String, nullable=False, default="unknown_legacy")
    consent_text_version = Column(String, nullable=True)
    lawful_basis = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "candidate_id", "requisition_id", name="uq_application_person_req"),
    )


class ApplicationLegacySource(Base):
    __tablename__ = "application_legacy_sources"
    id = Column(String, primary_key=True, default=_id)
    application_id = Column(String, ForeignKey("applications.id"), nullable=False, index=True)
    legacy_candidate_id = Column(String, ForeignKey("candidates.id"), nullable=False, unique=True)
    legacy_status = Column(String, nullable=True)
    source_email = Column(String, nullable=True)


class StageTransition(Base):
    __tablename__ = "stage_transitions"
    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    application_id = Column(String, ForeignKey("applications.id"), nullable=False)
    from_stage = Column(String, nullable=True)
    to_stage = Column(String, nullable=False)
    actor_user_id = Column(String, nullable=True)
    idempotency_key = Column(String(64), nullable=False, unique=True)
    ledger_event_id = Column(String, ForeignKey("workflow_events.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Assessment(Base):
    __tablename__ = "assessments"
    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    application_id = Column(String, ForeignKey("applications.id"), nullable=False)
    requisition_id = Column(String, ForeignKey("job_requisitions.id"), nullable=False)
    interview_id = Column(String, nullable=True)
    kind = Column(String, nullable=False, default="resume_screen")
    version = Column(Integer, nullable=False, default=1)
    status = Column(String, nullable=False, default="current")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("application_id", "kind", "version", name="uq_assessment_version"),
    )


class EvidenceFact(Base):
    __tablename__ = "evidence_facts"
    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    assessment_id = Column(String, ForeignKey("assessments.id"), nullable=False)
    application_id = Column(String, ForeignKey("applications.id"), nullable=False)
    source = Column(String, nullable=False)
    fact_type = Column(String, nullable=False)
    value = Column(Text, nullable=False)
    evaluative = Column(Boolean, nullable=False, default=True)
    reusable = Column(Boolean, nullable=False, default=False)
    extracted_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Inference(Base):
    __tablename__ = "inferences"
    id = Column(String, primary_key=True, default=_id)
    assessment_id = Column(String, ForeignKey("assessments.id"), nullable=False, index=True)
    label = Column(String, nullable=True)
    narrative = Column(Text, nullable=True)
    model_id = Column(String, nullable=True)
    heuristic_id = Column(String, nullable=True)
    prompt_version = Column(String, nullable=True)
    supporting_fact_ids = Column(JSON, nullable=False, default=list)
    model_output_untrusted = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AssessmentOverride(Base):
    __tablename__ = "assessment_overrides"
    id = Column(String, primary_key=True, default=_id)
    assessment_id = Column(String, ForeignKey("assessments.id"), nullable=False)
    inference_id = Column(String, ForeignKey("inferences.id"), nullable=True)
    actor_id = Column(String, nullable=False)
    before = Column(Text, nullable=True)
    after = Column(Text, nullable=True)
    reason = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class InterviewKit(Base):
    __tablename__ = "interview_kits"
    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    requisition_id = Column(String, ForeignKey("job_requisitions.id"), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    criteria = Column(JSON, nullable=False, default=list)

    __table_args__ = (
        UniqueConstraint("requisition_id", "version", name="uq_interview_kit_version"),
    )


class Interview(Base):
    __tablename__ = "interviews"
    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    application_id = Column(String, ForeignKey("applications.id"), nullable=False)
    requisition_id = Column(String, ForeignKey("job_requisitions.id"), nullable=False)
    status = Column(String, nullable=False, default="proposed")
    tz = Column(String, nullable=False, default="UTC")
    meeting_url = Column(String, nullable=True)
    unconfirmed_legacy_link = Column(Boolean, nullable=False, default=False)
    round_name = Column(String, nullable=True)
    duration_minutes = Column(Integer, nullable=False, default=45)
    calendar_uid = Column(String, nullable=True, index=True)
    calendar_sequence = Column(Integer, nullable=False, default=0)
    custom_notes = Column(Text, nullable=True)
    starts_at = Column(DateTime(timezone=True), nullable=True)
    ends_at = Column(DateTime(timezone=True), nullable=True)
    feedback_due_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class InterviewPanelist(Base):
    __tablename__ = "interview_panelists"
    id = Column(String, primary_key=True, default=_id)
    interview_id = Column(String, ForeignKey("interviews.id"), nullable=False, index=True)
    user_id = Column(String, nullable=True)
    email = Column(String, nullable=True)
    name = Column(String, nullable=True)
    role = Column(String, nullable=False, default="interviewer")
    response_status = Column(String, nullable=False, default="needs_action")  # 'needs_action', 'accepted', 'tentative', 'declined'

    __table_args__ = (
        UniqueConstraint("interview_id", "email", name="uq_interview_panelist_email"),
    )


class InterviewDelivery(Base):
    """Tracks per-recipient calendar invite and notification deliveries."""
    __tablename__ = "interview_deliveries"
    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    interview_id = Column(String, ForeignKey("interviews.id"), nullable=False, index=True)
    recipient_email = Column(String, nullable=False)
    recipient_type = Column(String, nullable=False, default="candidate")  # 'candidate', 'interviewer', 'organizer'
    delivery_channel = Column(String, nullable=False, default="smtp")  # 'smtp', 'gmail', 'calendar_sync'
    status = Column(String, nullable=False, default="pending")  # 'pending', 'sent', 'failed'
    attempts = Column(Integer, nullable=False, default=0)
    provider_message_id = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class InterviewFeedback(Base):
    __tablename__ = "interview_feedback"
    id = Column(String, primary_key=True, default=_id)
    interview_id = Column(String, ForeignKey("interviews.id"), nullable=False)
    author_user_id = Column(String, nullable=False)
    assessment_id = Column(String, ForeignKey("assessments.id"), nullable=True)
    ratings = Column(JSON, nullable=False, default=dict)
    notes = Column(Text, nullable=True)
    recommendation = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("interview_id", "author_user_id", name="uq_interview_feedback_author"),
    )


class SalaryBand(Base):
    __tablename__ = "salary_bands"
    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    requisition_id = Column(String, ForeignKey("job_requisitions.id"), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    min_amount = Column(Numeric(12, 2), nullable=False)
    mid_amount = Column(Numeric(12, 2), nullable=False)
    max_amount = Column(Numeric(12, 2), nullable=False)
    effective_from = Column(DateTime(timezone=True), nullable=False)
    effective_to = Column(DateTime(timezone=True), nullable=True)
    created_by_user_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("min_amount <= mid_amount AND mid_amount <= max_amount", name="chk_salary_band_order"),
    )


class OfferTemplateVersion(Base):
    __tablename__ = "offer_template_versions"
    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    template_key = Column(String, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Offer(Base):
    __tablename__ = "offers"
    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    application_id = Column(String, ForeignKey("applications.id"), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    currency = Column(String(3), nullable=False, default="USD")
    base_amount = Column(Numeric(12, 2), nullable=False)
    band_id = Column(String, ForeignKey("salary_bands.id"), nullable=True)
    template_version_id = Column(String, ForeignKey("offer_template_versions.id"), nullable=True)
    document_sha256 = Column(String(64), nullable=True)
    variables = Column(JSON, nullable=False, default=dict)
    payload_hash = Column(String(64), nullable=True)
    approval_request_id = Column(String, nullable=True)
    signature_state = Column(String, nullable=False, default="none")
    status = Column(String, nullable=False, default="draft")
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_by_user_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("application_id", "version", name="uq_offer_version"),
    )


class Employee(Base):
    __tablename__ = "employees"
    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    application_id = Column(String, ForeignKey("applications.id"), nullable=False)
    candidate_id = Column(String, ForeignKey("candidates.id"), nullable=False)
    user_id = Column(String, nullable=True)
    manager_employee_id = Column(String, ForeignKey("employees.id"), nullable=True)
    status = Column(String, nullable=False, default="active")
    hired_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class OnboardingTask(Base):
    __tablename__ = "onboarding_tasks"
    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    employee_id = Column(String, ForeignKey("employees.id"), nullable=False)
    title = Column(String, nullable=False)
    status = Column(String, nullable=False, default="open")
    verification_required = Column(Boolean, nullable=False, default=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    due_at = Column(DateTime(timezone=True), nullable=True)


class ProvisioningRequest(Base):
    __tablename__ = "provisioning_requests"
    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    employee_id = Column(String, ForeignKey("employees.id"), nullable=False)
    action = Column(String, nullable=False)
    system = Column(String, nullable=False, default="manual")
    status = Column(String, nullable=False, default="pending")
    idempotency_key = Column(String(64), nullable=False, unique=True)
    approval_request_id = Column(String, nullable=True)


class HRDocument(Base):
    __tablename__ = "hr_documents"
    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    application_id = Column(String, ForeignKey("applications.id"), nullable=True)
    candidate_id = Column(String, ForeignKey("candidates.id"), nullable=True)
    classification = Column(String, nullable=False, default="recruiting")
    sha256 = Column(String(64), nullable=True)
    storage_key = Column(String, nullable=True)
    source_path = Column(String, nullable=True)
    copy_status = Column(String, nullable=False, default="pending")
    legal_hold = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class HRCostEntry(Base):
    __tablename__ = "hr_cost_entries"
    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    requisition_id = Column(String, ForeignKey("job_requisitions.id"), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    source = Column(String, nullable=False, default="other")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class HRAgentInvocation(Base):
    __tablename__ = "hr_agent_invocations"
    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(String, nullable=True)
    tool = Column(String, nullable=False)
    autonomy = Column(String, nullable=False, default="L0")
    prompt_version = Column(String, nullable=True)
    model_id = Column(String, nullable=True)
    approval_request_id = Column(String, nullable=True)
    cost_accounted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class HRWorkflowMeasure(Base):
    __tablename__ = "hr_workflow_measures"
    id = Column(String, primary_key=True, default=_id)
    workflow_id = Column(String, ForeignKey("workflows.id"), nullable=False, unique=True)
    baseline_manual_minutes = Column(Integer, nullable=True)
    duration_ms = Column(Integer, nullable=True)


class HRReminder(Base):
    __tablename__ = "hr_reminders"
    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    application_id = Column(String, ForeignKey("applications.id"), nullable=False)
    reason = Column(String, nullable=False)
    status = Column(String, nullable=False, default="open")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SkillTerm(Base):
    __tablename__ = "skill_terms"
    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    normalized_name = Column(String, nullable=False)
    parent_id = Column(String, ForeignKey("skill_terms.id"), nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "normalized_name", name="uq_skill_term_name"),
    )


class SkillEvidence(Base):
    __tablename__ = "skill_evidence"
    id = Column(String, primary_key=True, default=_id)
    skill_term_id = Column(String, ForeignKey("skill_terms.id"), nullable=False)
    evidence_fact_id = Column(String, ForeignKey("evidence_facts.id"), nullable=False)
    proficiency = Column(String, nullable=True)


# --- GOVERNED HR DOCUMENT PLATFORM MODELS ---

class TenantDocumentTemplate(Base):
    """Tenant-scoped registry for HR document templates."""
    __tablename__ = "tenant_document_templates"
    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    document_type = Column(String, nullable=False)  # arbitrary string: e.g. 'offer_letter', 'nda', 'joining_pack', 'tax_form', 'custom_policy'
    category = Column(String, nullable=False, default="onboarding", index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    folder_path = Column(String, nullable=False, default="/")
    tags = Column(JSON, nullable=False, default=list)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "document_type", "name", name="uq_tenant_doc_type_name"),
    )


class TemplateVersion(Base):
    """Immutable versioned template source with checksum and lifecycle state."""
    __tablename__ = "template_versions"
    id = Column(String, primary_key=True, default=_id)
    template_id = Column(String, ForeignKey("tenant_document_templates.id"), nullable=False, index=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    format = Column(String, nullable=False, default="html")  # 'html', 'markdown', 'docx'
    status = Column(String, nullable=False, default="draft")  # 'draft', 'analyzed', 'reviewed', 'validated', 'published', 'retired'
    storage_key = Column(String, nullable=False)
    content_sha256 = Column(String(64), nullable=False)
    raw_content = Column(Text, nullable=True)
    docx_structure = Column(JSON, nullable=True, default=dict)
    detected_clauses = Column(JSON, nullable=True, default=list)
    proposed_mappings = Column(JSON, nullable=True, default=list)
    published_at = Column(DateTime(timezone=True), nullable=True)
    published_by_user_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("template_id", "version", name="uq_template_version_num"),
    )


class TemplateVariableSchema(Base):
    """Typed schema definition for variables required by a template version."""
    __tablename__ = "template_variable_schemas"
    id = Column(String, primary_key=True, default=_id)
    template_version_id = Column(String, ForeignKey("template_versions.id"), nullable=False, index=True)
    variable_name = Column(String, nullable=False)  # e.g. 'candidate_legal_name', 'annual_ctc'
    data_type = Column(String, nullable=False, default="string")  # 'string', 'money', 'date', 'integer', 'boolean'
    is_required = Column(Boolean, nullable=False, default=True)
    source_field = Column(String, nullable=False)  # e.g. 'candidate.name', 'compensation.base_amount'
    sensitivity = Column(String, nullable=False, default="confidential")
    editable_by_recruiter = Column(Boolean, nullable=False, default=False)


class HRDocumentPacket(Base):
    """Encapsulates a candidate's complete frozen hiring document package."""
    __tablename__ = "hr_document_packets"
    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    application_id = Column(String, ForeignKey("applications.id"), nullable=False, index=True)
    candidate_id = Column(String, ForeignKey("candidates.id"), nullable=False, index=True)
    requisition_id = Column(String, ForeignKey("job_requisitions.id"), nullable=True)
    data_snapshot = Column(JSON, nullable=False, default=dict)  # Frozen candidate, compensation, manager, role
    data_snapshot_sha256 = Column(String(64), nullable=False)
    current_lifecycle_state = Column(String, nullable=False, default="draft")  # 'draft', 'verified', 'approved', 'offered', 'accepted', 'appointed', 'contract_executed', 'hired'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class HRDocumentArtifact(Base):
    """Immutable rendered document artifact bound to cryptographic hash."""
    __tablename__ = "hr_document_artifacts"
    id = Column(String, primary_key=True, default=_id)
    packet_id = Column(String, ForeignKey("hr_document_packets.id"), nullable=False, index=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    template_version_id = Column(String, ForeignKey("template_versions.id"), nullable=True)
    document_type = Column(String, nullable=False)  # 'offer_letter', 'appointment_letter', 'employment_contract', 'nda', etc.
    format = Column(String, nullable=False, default="html")  # 'html', 'pdf', 'docx'
    storage_key = Column(String, nullable=False)
    artifact_sha256 = Column(String(64), nullable=False, index=True)
    byte_size = Column(Integer, nullable=False, default=0)
    rendered_at = Column(DateTime(timezone=True), server_default=func.now())


class DocumentVerificationRun(Base):
    """Audit record of verification runs and findings."""
    __tablename__ = "document_verification_runs"
    id = Column(String, primary_key=True, default=_id)
    packet_id = Column(String, ForeignKey("hr_document_packets.id"), nullable=False, index=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    artifact_sha256 = Column(String(64), nullable=False)
    overall_eligibility = Column(String, nullable=False, default="BLOCKED")  # 'BLOCKED', 'REVIEW_REQUIRED', 'ELIGIBLE_FOR_APPROVAL'
    findings = Column(JSON, nullable=False, default=list)  # List of VerificationFinding dicts
    agent_model_id = Column(String, nullable=True)
    rule_version = Column(String, nullable=False, default="2026.1")
    executed_at = Column(DateTime(timezone=True), server_default=func.now())


class HRArtifactApproval(Base):
    """Human approval bound cryptographically to exact artifact SHA-256."""
    __tablename__ = "hr_artifact_approvals"
    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    packet_id = Column(String, ForeignKey("hr_document_packets.id"), nullable=False)
    artifact_id = Column(String, ForeignKey("hr_document_artifacts.id"), nullable=False)
    bound_artifact_sha256 = Column(String(64), nullable=False)
    approver_user_id = Column(String, nullable=False)
    approver_role = Column(String, nullable=False)
    decision = Column(String, nullable=False, default="approved")  # 'approved', 'rejected'
    rationale = Column(Text, nullable=True)
    approved_at = Column(DateTime(timezone=True), server_default=func.now())


class CandidateAcceptanceRecord(Base):
    """Immutable audit record of candidate acceptance action."""
    __tablename__ = "candidate_acceptance_records"
    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    packet_id = Column(String, ForeignKey("hr_document_packets.id"), nullable=False)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    accepted_at = Column(DateTime(timezone=True), server_default=func.now())
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    status = Column(String, nullable=False, default="accepted")


# --- DYNAMIC HR WORKFLOW PLATFORM ENTITIES ---

class HRWorkflowDefinition(Base):
    """Tenant-scoped dynamic onboarding workflow graph (DAG)."""
    __tablename__ = "hr_workflow_definitions"
    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    folder_path = Column(String, nullable=False, default="/")
    department_id = Column(String, nullable=True, index=True)
    tags = Column(JSON, nullable=False, default=list)
    published_version_id = Column(String, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    version = Column(Integer, nullable=False, default=1)
    graph_schema = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class HRWorkflowInstance(Base):
    """Running execution of a dynamic workflow for a candidate and application."""
    __tablename__ = "hr_workflow_instances"
    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    workflow_definition_id = Column(String, ForeignKey("hr_workflow_definitions.id"), nullable=False, index=True)
    application_id = Column(String, ForeignKey("applications.id"), nullable=False, index=True)
    candidate_id = Column(String, ForeignKey("candidates.id"), nullable=False, index=True)
    current_state = Column(String, nullable=False, default="intake_pending")
    candidate_token_hash = Column(String(64), nullable=False, unique=True, index=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=False)
    token_revoked = Column(Boolean, nullable=False, default=False)
    context_data = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class HRWorkflowTask(Base):
    """Granular task node inside a running workflow instance."""
    __tablename__ = "hr_workflow_tasks"
    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    instance_id = Column(String, ForeignKey("hr_workflow_instances.id"), nullable=False, index=True)
    node_id = Column(String, nullable=False)
    task_type = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")  # 'pending', 'in_progress', 'completed', 'blocked', 'skipped'
    assigned_role = Column(String, nullable=True)
    output_payload = Column(JSON, nullable=True, default=dict)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CandidateEvidence(Base):
    """Candidate uploaded document evidence item."""
    __tablename__ = "candidate_evidence_items"
    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    instance_id = Column(String, ForeignKey("hr_workflow_instances.id"), nullable=False, index=True)
    document_name = Column(String, nullable=False)
    document_category = Column(String, nullable=False)  # 'passport', 'national_id', 'resume', 'tax_form', 'degree_certificate'
    storage_key = Column(String, nullable=False)
    file_sha256 = Column(String(64), nullable=False)
    mime_type = Column(String, nullable=False)
    extracted_data = Column(JSON, nullable=False, default=dict)  # {field_key: {value, confidence, page, snippet}}
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())


class CandidateFieldValue(Base):
    """Reconciled multi-source canonical value with provenance and conflict tracking."""
    __tablename__ = "candidate_field_values"
    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    instance_id = Column(String, ForeignKey("hr_workflow_instances.id"), nullable=False, index=True)
    canonical_key = Column(String, nullable=False, index=True)
    resolved_value = Column(JSON, nullable=True)
    candidate_provided_value = Column(JSON, nullable=True)
    document_extracted_value = Column(JSON, nullable=True)
    hr_approved_value = Column(JSON, nullable=True)
    source_provenance = Column(JSON, nullable=True)  # {evidence_id, page, confidence}
    has_conflict = Column(Boolean, nullable=False, default=False)
    conflict_details = Column(JSON, nullable=True)
    status = Column(String, nullable=False, default="pending")  # 'pending', 'reconciled', 'hr_overridden', 'conflict'
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class DocumentDraft(Base):
    """Editable document draft in Review Studio with tracked changes and approval binding."""
    __tablename__ = "hr_document_drafts"
    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    instance_id = Column(String, ForeignKey("hr_workflow_instances.id"), nullable=False, index=True)
    template_version_id = Column(String, ForeignKey("template_versions.id"), nullable=False)
    document_name = Column(String, nullable=False)
    format = Column(String, nullable=False, default="docx")  # 'docx', 'html'
    storage_key = Column(String, nullable=False)
    content_sha256 = Column(String(64), nullable=False)
    field_overrides = Column(JSON, nullable=False, default=dict)
    editor_revisions = Column(JSON, nullable=False, default=list)  # [{timestamp, user_id, diff_summary}]
    current_approval_status = Column(String, nullable=False, default="draft")  # 'draft', 'pending_approval', 'approved', 'rejected'
    approved_by_user_id = Column(String, nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    bound_approval_sha256 = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class DocumentReviewComment(Base):
    """Paragraph-anchored or draft-level review comment."""
    __tablename__ = "hr_document_review_comments"
    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    draft_id = Column(String, ForeignKey("hr_document_drafts.id"), nullable=False, index=True)
    user_id = Column(String, nullable=False)
    user_name = Column(String, nullable=False)
    paragraph_index = Column(Integer, nullable=True)
    comment_text = Column(Text, nullable=False)
    is_resolved = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ScheduledDelivery(Base):
    """Timezone-aware scheduled release of an approved draft."""
    __tablename__ = "hr_scheduled_deliveries"
    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    draft_id = Column(String, ForeignKey("hr_document_drafts.id"), nullable=False, index=True)
    scheduled_for = Column(DateTime(timezone=True), nullable=False)
    timezone = Column(String, nullable=False, default="UTC")
    recipient_email = Column(String, nullable=False)
    status = Column(String, nullable=False, default="scheduled")  # 'scheduled', 'dispatched', 'failed', 'cancelled'
    retry_count = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    dispatched_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class HRWorkflowVersion(Base):
    """Immutable published version of an HR workflow graph."""
    __tablename__ = "hr_workflow_versions"
    id = Column(String, primary_key=True, default=_id)
    definition_id = Column(String, ForeignKey("hr_workflow_definitions.id"), nullable=False, index=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    graph_schema = Column(JSON, nullable=False, default=dict)
    published_by_user_id = Column(String, nullable=True)
    change_summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("definition_id", "version", name="uq_workflow_definition_version"),
    )


class HRWorkflowImportRecord(Base):
    """Audit log of cross-folder or cross-department workflow and template imports."""
    __tablename__ = "hr_workflow_import_records"
    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    source_definition_id = Column(String, ForeignKey("hr_workflow_definitions.id"), nullable=False)
    target_definition_id = Column(String, ForeignKey("hr_workflow_definitions.id"), nullable=False)
    source_folder_path = Column(String, nullable=False)
    target_folder_path = Column(String, nullable=False)
    remapped_node_ids = Column(JSON, nullable=False, default=dict)
    cloned_template_ids = Column(JSON, nullable=False, default=dict)
    imported_by_user_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TenantEmployeeSequence(Base):
    """Tenant-scoped atomic sequential counter for employee numbering."""
    __tablename__ = "tenant_employee_sequences"
    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    prefix = Column(String, nullable=False, default="EMP")
    current_val = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "prefix", name="uq_tenant_employee_sequence"),
    )


class HROutboxEvent(Base):
    """Transactional outbox for reliable asynchronous HR domain events."""
    __tablename__ = "hr_outbox_events"
    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)  # e.g. 'hr.employee.provisioned', 'hr.interview.scheduled'
    aggregate_type = Column(String, nullable=False, default="employee")
    aggregate_id = Column(String, nullable=False, index=True)
    payload = Column(JSON, nullable=False, default=dict)
    status = Column(String, nullable=False, default="pending", index=True)  # 'pending', 'processed', 'failed'
    retry_count = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


