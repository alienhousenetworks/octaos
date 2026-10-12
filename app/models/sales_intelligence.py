"""Canonical Sales OS records. Lead remains a compatibility projection."""
import uuid

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, text
from sqlalchemy.sql import func

from app.models.base import Base


def _id() -> str:
    return str(uuid.uuid4())


class SalesCompany(Base):
    """Tenant-scoped canonical account. Unknown fields stay null."""

    __tablename__ = "sales_companies"

    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    canonical_domain = Column(String, nullable=True, index=True)
    legal_name = Column(String, nullable=True)
    display_name = Column(String, nullable=True)
    aliases = Column(JSON, default=list)
    industry = Column(String, nullable=True)
    employee_count = Column(Integer, nullable=True)
    employee_band = Column(String, nullable=True)
    hq_country = Column(String, nullable=True)
    hq_city = Column(String, nullable=True)
    website = Column(String, nullable=True)
    icp_score = Column(Float, nullable=True)
    intent_score = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)
    deal_room_id = Column(String, ForeignKey("deal_rooms.id"), nullable=True, index=True)
    field_provenance = Column(JSON, default=dict)
    conflicts = Column(JSON, default=list)
    version = Column(Integer, nullable=False, default=1)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index(
            "uq_sales_company_domain",
            "tenant_id",
            "canonical_domain",
            unique=True,
            sqlite_where=text("canonical_domain IS NOT NULL"),
            postgresql_where=text("canonical_domain IS NOT NULL"),
        ),
    )


class AccountContact(Base):
    """Person attached to a company. Distinct from the legacy contacts table."""

    __tablename__ = "sales_account_contacts"

    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    company_id = Column(String, ForeignKey("sales_companies.id"), nullable=False, index=True)
    full_name = Column(String, nullable=True)
    role_title = Column(String, nullable=True)
    seniority = Column(String, nullable=True)
    department = Column(String, nullable=True)
    email = Column(String, nullable=True, index=True)
    phone = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)
    provider_ids = Column(JSON, default=dict)
    channels = Column(JSON, default=list)
    is_inferred = Column(Integer, nullable=False, default=0)
    inference_method = Column(String, nullable=True)
    inference_model = Column(String, nullable=True)
    inference_evidence_ids = Column(JSON, default=list)
    confidence = Column(Float, nullable=True)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index(
            "uq_sales_contact_email",
            "tenant_id",
            "email",
            unique=True,
            sqlite_where=text("email IS NOT NULL"),
            postgresql_where=text("email IS NOT NULL"),
        ),
    )


class SignalEvidence(Base):
    """Immutable provenance for one captured source payload."""

    __tablename__ = "sales_signal_evidence"

    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    company_id = Column(String, ForeignKey("sales_companies.id"), nullable=True, index=True)
    source_key = Column(String, nullable=False, index=True)
    source_url = Column(Text, nullable=True)
    publisher = Column(String, nullable=True)
    observed_at = Column(DateTime(timezone=True), nullable=True)
    retrieved_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    raw_payload_ref = Column(Text, nullable=True)
    excerpt = Column(Text, nullable=True)
    claim = Column(Text, nullable=True)
    payload_hash = Column(String, nullable=False, index=True)
    confidence = Column(Float, nullable=True)
    license_class = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "payload_hash", "source_key", name="uq_sales_evidence_hash"),
    )


class SalesSignal(Base):
    """Normalized buying or market event. Strength and source confidence stay separate."""

    __tablename__ = "sales_signals"

    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    company_id = Column(String, ForeignKey("sales_companies.id"), nullable=False, index=True)
    evidence_id = Column(String, ForeignKey("sales_signal_evidence.id"), nullable=True, index=True)
    signal_type = Column(String, nullable=False, index=True)
    family = Column(String, nullable=False, index=True)
    base_strength = Column(Float, nullable=True)
    source_confidence = Column(Float, nullable=True)
    half_life_days = Column(Integer, nullable=False)
    observed_at = Column(DateTime(timezone=True), nullable=True)
    retrieved_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    source_key = Column(String, nullable=False)
    independent_key = Column(String, nullable=True, index=True)
    summary = Column(Text, nullable=True)
    is_inferred = Column(Integer, nullable=False, default=0)
    inference_method = Column(String, nullable=True)
    inference_model = Column(String, nullable=True)
    payload_hash = Column(String, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "company_id", "signal_type", "payload_hash", name="uq_sales_signal_event"
        ),
    )


class CompanyTechnology(Base):
    __tablename__ = "sales_company_technologies"

    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    company_id = Column(String, ForeignKey("sales_companies.id"), nullable=False, index=True)
    technology = Column(String, nullable=False)
    first_observed_at = Column(DateTime(timezone=True), nullable=True)
    last_observed_at = Column(DateTime(timezone=True), nullable=True)
    confidence = Column(Float, nullable=True)
    source_key = Column(String, nullable=False)
    evidence_id = Column(String, ForeignKey("sales_signal_evidence.id"), nullable=True)
    change_history = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "company_id", "technology", "source_key", name="uq_sales_technology"),
    )


class EmploymentRecord(Base):
    __tablename__ = "sales_employment_records"

    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    contact_id = Column(String, ForeignKey("sales_account_contacts.id"), nullable=False, index=True)
    company_id = Column(String, ForeignKey("sales_companies.id"), nullable=False, index=True)
    role_title = Column(String, nullable=True)
    department = Column(String, nullable=True)
    seniority = Column(String, nullable=True)
    started_on = Column(String, nullable=True)
    ended_on = Column(String, nullable=True)
    is_current = Column(Integer, nullable=True)
    evidence_id = Column(String, ForeignKey("sales_signal_evidence.id"), nullable=True)
    confidence = Column(Float, nullable=True)
    source_key = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ContactVerification(Base):
    __tablename__ = "sales_contact_verifications"

    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    contact_id = Column(String, ForeignKey("sales_account_contacts.id"), nullable=False, index=True)
    tier = Column(Integer, nullable=False)
    status = Column(String, nullable=False)
    verifier = Column(String, nullable=False)
    score = Column(Float, nullable=True)
    failure_reason = Column(Text, nullable=True)
    details = Column(JSON, default=dict)
    checked_at = Column(DateTime(timezone=True), server_default=func.now())


class SourceRun(Base):
    __tablename__ = "sales_source_runs"

    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    trigger = Column(String, nullable=False, default="manual")
    status = Column(String, nullable=False, default="planned", index=True)
    query = Column(Text, nullable=True)
    cursor = Column(String, nullable=True)
    checkpoint = Column(JSON, default=dict)
    counts = Column(JSON, default=dict)
    error_summary = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SourceRecord(Base):
    __tablename__ = "sales_source_records"

    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    source_run_id = Column(String, ForeignKey("sales_source_runs.id"), nullable=True, index=True)
    provider_key = Column(String, nullable=False, index=True)
    operation = Column(String, nullable=False)
    status = Column(String, nullable=False)
    request_id = Column(String, nullable=False, index=True)
    latency_ms = Column(Integer, nullable=True)
    credits = Column(Float, nullable=True)
    estimated_cost = Column(Float, nullable=True)
    actual_cost = Column(Float, nullable=True)
    response_hash = Column(String, nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SalesOpportunity(Base):
    __tablename__ = "sales_opportunities"

    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    company_id = Column(String, ForeignKey("sales_companies.id"), nullable=False, index=True)
    stage = Column(String, nullable=False, default="discovered", index=True)
    score = Column(Float, nullable=True)
    component_scores = Column(JSON, default=dict)
    explanation = Column(JSON, default=dict)
    rationale = Column(Text, nullable=True)
    score_version = Column(String, nullable=True)
    config_hash = Column(String, nullable=True)
    tier6_state = Column(String, nullable=True, index=True)
    confidence = Column(Float, nullable=True)
    evidence_ids = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class OutreachPermission(Base):
    __tablename__ = "sales_outreach_permissions"

    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    contact_id = Column(String, ForeignKey("sales_account_contacts.id"), nullable=True, index=True)
    company_id = Column(String, ForeignKey("sales_companies.id"), nullable=True, index=True)
    channel = Column(String, nullable=False)
    jurisdiction = Column(String, nullable=True)
    legal_basis = Column(String, nullable=True)
    permission_state = Column(String, nullable=False, default="unknown")
    evidence_id = Column(String, ForeignKey("sales_signal_evidence.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SourceCost(Base):
    __tablename__ = "sales_source_costs"

    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    provider_key = Column(String, nullable=False, index=True)
    source_record_id = Column(String, ForeignKey("sales_source_records.id"), nullable=True)
    operation = Column(String, nullable=False)
    currency = Column(String, nullable=False, default="USD")
    estimated_amount = Column(Float, nullable=True)
    actual_amount = Column(Float, nullable=True)
    credits = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SourceOutcome(Base):
    """A touch linked to a later commercial event. This is attribution, not causation."""

    __tablename__ = "sales_source_outcomes"

    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    provider_key = Column(String, nullable=False, index=True)
    company_id = Column(String, ForeignKey("sales_companies.id"), nullable=True, index=True)
    contact_id = Column(String, ForeignKey("sales_account_contacts.id"), nullable=True)
    opportunity_id = Column(String, ForeignKey("sales_opportunities.id"), nullable=True)
    lead_id = Column(String, ForeignKey("leads.id"), nullable=True)
    outcome_type = Column(String, nullable=False, index=True)
    amount = Column(Float, nullable=True)
    touch_role = Column(String, nullable=False, default="unknown")
    occurred_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
