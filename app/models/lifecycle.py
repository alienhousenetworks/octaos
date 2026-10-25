"""Shared Customer Lifecycle and Governance Data Models for OctaOS.

Provides unified customer identity, consent, suppression, segmentation,
lifecycle state, and auditable communication history across Sales OS and Marketing OS.
"""
import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Float, Text, JSON, Integer
from sqlalchemy.sql import func
from app.models.base import Base


class CustomerIdentity(Base):
    """Unified cross-platform identity linking CRM leads, support contacts, and subscribers."""
    __tablename__ = "customer_identities"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    primary_email = Column(String, index=True, nullable=True)
    primary_phone = Column(String, index=True, nullable=True)
    full_name = Column(String, nullable=True)
    company_name = Column(String, nullable=True)
    external_crm_id = Column(String, nullable=True, index=True)  # HubSpot, Salesforce, etc.
    lead_id = Column(String, ForeignKey("leads.id"), nullable=True, index=True)
    match_confidence = Column(Float, default=1.0)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ContactPreference(Base):
    """Granular opt-in and consent status per communication purpose."""
    __tablename__ = "contact_preferences"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    customer_id = Column(String, ForeignKey("customer_identities.id"), nullable=False, index=True)
    channel = Column(String, default="email")  # email, sms, whatsapp, phone
    purpose = Column(String, default="marketing")  # marketing, sales, transactional, newsletter
    is_opted_in = Column(Boolean, default=True)
    consent_source = Column(String, nullable=True)  # web_form, import, explicit_optin
    effective_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())


from app.models.deal_room import SuppressionRecord


class AudienceSegment(Base):
    """Versioned, tenant-scoped audience definitions and snapshots."""
    __tablename__ = "audience_segments"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    segment_type = Column(String, default="DYNAMIC_RULE")  # DYNAMIC_RULE, SNAPSHOT, EVENT_TRIGGERED
    version = Column(String, default="1.0")
    definition_json = Column(JSON, nullable=False)
    matched_count = Column(Integer, nullable=True)
    last_evaluated_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LifecycleStateRecord(Base):
    """Authoritative lifecycle progression state for contacts and accounts."""
    __tablename__ = "lifecycle_state_records"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    customer_id = Column(String, ForeignKey("customer_identities.id"), nullable=False, index=True)
    current_stage = Column(String, default="lead")  # subscriber, lead, mql, sql, opportunity, customer, at_risk, churned
    previous_stage = Column(String, nullable=True)
    transition_reason = Column(String, nullable=True)
    source_event = Column(String, nullable=True)
    changed_at = Column(DateTime(timezone=True), server_default=func.now())


class CommunicationLog(Base):
    """Central communication audit ledger recording all outbound attempts across Sales and Marketing."""
    __tablename__ = "communication_logs"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    recipient_identifier = Column(String, nullable=False, index=True)
    channel = Column(String, default="email")
    originating_system = Column(String, nullable=False)  # "sales_os" or "campaign_os"
    purpose = Column(String, default="marketing")
    content_version_ref = Column(String, nullable=True)
    subject_or_summary = Column(String, nullable=True)
    status = Column(String, default="sent")  # queued, sent, delivered, bounced, opened, clicked, suppressed
    provider = Column(String, nullable=True)  # ses, sendgrid, smtp, twilio
    external_provider_id = Column(String, nullable=True, index=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RiskSignalRecord(Base):
    """Recorded customer attrition, renewal risk, and churn signals with explainable evidence."""
    __tablename__ = "risk_signal_records"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    customer_id = Column(String, ForeignKey("customer_identities.id"), nullable=False, index=True)
    risk_band = Column(String, default="LOW")  # LOW, MEDIUM, HIGH, CRITICAL
    risk_score = Column(Float, nullable=True)
    contributing_signals = Column(JSON, default=list)
    recommended_intervention = Column(String, nullable=True)
    recommended_owner = Column(String, default="customer_success")
    status = Column(String, default="active")  # active, addressed, dismissed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
