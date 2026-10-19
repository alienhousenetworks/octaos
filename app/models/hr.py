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
    starts_at = Column(DateTime(timezone=True), nullable=True)
    ends_at = Column(DateTime(timezone=True), nullable=True)
    feedback_due_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class InterviewPanelist(Base):
    __tablename__ = "interview_panelists"
    id = Column(String, primary_key=True, default=_id)
    interview_id = Column(String, ForeignKey("interviews.id"), nullable=False)
    user_id = Column(String, nullable=False)

    __table_args__ = (
        UniqueConstraint("interview_id", "user_id", name="uq_interview_panelist"),
    )


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
