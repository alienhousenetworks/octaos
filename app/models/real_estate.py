"""Dedicated tenant-scoped operational tables for Real Estate."""
import uuid
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
    JSON,
)
from sqlalchemy.sql import func
from app.models.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class RealEstateProject(Base):
    """Tenant-scoped property development/project."""

    __tablename__ = "real_estate_projects"

    id = Column(String, primary_key=True, default=_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    code = Column(String, nullable=True, index=True)
    location = Column(String, nullable=True)
    city = Column(String, nullable=True)
    status = Column(String, default="active")  # planning, pre_launch, active, sold_out
    total_units = Column(Integer, default=0)
    available_units = Column(Integer, default=0)
    hold_duration_hours = Column(Integer, default=48)  # Configurable hold window
    rera_number = Column(String, nullable=True)
    amenities = Column(JSON, default=list)
    address = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    geocoded_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_re_project_code"),
    )


class RealEstateUnit(Base):
    """Authoritative inventory record with optimistic locking."""

    __tablename__ = "real_estate_units"

    id = Column(String, primary_key=True, default=_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    project_id = Column(String, ForeignKey("real_estate_projects.id"), nullable=False, index=True)
    tower = Column(String, nullable=True)
    unit_number = Column(String, nullable=False)
    floor = Column(Integer, nullable=True)
    unit_type = Column(String, nullable=False)  # 1BHK, 2BHK, 3BHK, Penthouse, Villa
    carpet_sqft = Column(Float, nullable=True)
    base_price = Column(Float, nullable=False)
    status = Column(String, nullable=False, default="available", index=True)  # available, hold_requested, confirmed_hold, booked, maintenance
    version = Column(Integer, nullable=False, default=1)  # Optimistic concurrency lock
    attributes = Column(JSON, default=dict)  # facing, parking, view
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "project_id", "unit_number", name="uq_re_unit_number"),
    )


class RealEstateSiteVisit(Base):
    """Site visit & property tour itinerary linked to CRM lead."""

    __tablename__ = "real_estate_site_visits"

    id = Column(String, primary_key=True, default=_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    lead_id = Column(String, ForeignKey("leads.id"), nullable=False, index=True)
    project_id = Column(String, ForeignKey("real_estate_projects.id"), nullable=False, index=True)
    unit_id = Column(String, ForeignKey("real_estate_units.id"), nullable=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    duration_minutes = Column(Integer, default=45)
    sequence_order = Column(Integer, default=0)
    estimated_travel_minutes = Column(Integer, default=0)
    estimated_arrival_at = Column(DateTime(timezone=True), nullable=True)
    actual_arrival_at = Column(DateTime(timezone=True), nullable=True)
    actual_departure_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, nullable=False, default="scheduled")  # scheduled, en_route, arrived, completed, cancelled, no_show, delayed
    assigned_agent = Column(String, nullable=True)
    escort_contact = Column(String, nullable=True)
    pickup_required = Column(Boolean, default=False)
    tour_feedback = Column(Text, nullable=True)
    buyer_interest_level = Column(String, nullable=True)  # high, medium, cold
    buyer_objections = Column(JSON, default=list)  # ["price_high", "floor_too_low", "possession_timeline"]
    agreed_next_step = Column(String, nullable=True)
    check_in_latitude = Column(Float, nullable=True)
    check_in_longitude = Column(Float, nullable=True)
    check_in_accuracy = Column(Float, nullable=True)
    check_in_verified = Column(Boolean, default=False)
    check_in_exception_reason = Column(Text, nullable=True)
    rescheduled_from_id = Column(String, nullable=True)
    recovery_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class RealEstateUnitHold(Base):
    """Transactional reservation with expiration timer and audit trail."""

    __tablename__ = "real_estate_unit_holds"

    id = Column(String, primary_key=True, default=_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    unit_id = Column(String, ForeignKey("real_estate_units.id"), nullable=False, index=True)
    lead_id = Column(String, ForeignKey("leads.id"), nullable=False, index=True)
    status = Column(String, nullable=False, default="requested")  # requested, confirmed, expired, released, converted_to_booking
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    deposit_amount = Column(Float, default=0.0)
    deposit_verified = Column(Boolean, default=False)
    deposit_evidence_ref = Column(String, nullable=True)
    verified_by_user_id = Column(String, nullable=True)
    concurrency_token = Column(String, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class RealEstateBrokerAttribution(Base):
    """Channel partner / broker commission and source attribution."""

    __tablename__ = "real_estate_broker_attributions"

    id = Column(String, primary_key=True, default=_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    lead_id = Column(String, ForeignKey("leads.id"), nullable=False, index=True)
    brokerage_name = Column(String, nullable=False)
    broker_agent_name = Column(String, nullable=True)
    broker_email = Column(String, nullable=True)
    broker_phone = Column(String, nullable=True)
    rera_id = Column(String, nullable=True)
    commission_pct = Column(Float, default=2.0)
    agreement_verified = Column(Boolean, default=False)
    agreement_doc_url = Column(String, nullable=True)
    status = Column(String, default="active")  # active, contested, approved, paid
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RealEstateBooking(Base):
    """Authoritative booking contract locking a unit to a buyer."""

    __tablename__ = "real_estate_bookings"

    id = Column(String, primary_key=True, default=_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    booking_reference = Column(String, unique=True, nullable=False, index=True)  # e.g. BK-2026-0042
    unit_id = Column(String, ForeignKey("real_estate_units.id"), nullable=False, index=True)
    project_id = Column(String, ForeignKey("real_estate_projects.id"), nullable=False, index=True)
    lead_id = Column(String, ForeignKey("leads.id"), nullable=False, index=True)
    hold_id = Column(String, ForeignKey("real_estate_unit_holds.id"), nullable=True)

    # Financial & Price Snapshot (immutable once confirmed)
    base_price = Column(Float, nullable=False)
    agreed_price = Column(Float, nullable=False)
    deposit_paid = Column(Float, default=0.0)
    balance_due = Column(Float, nullable=False)
    currency = Column(String, default="INR")

    # Lifecycle State: draft, pending_payment, payment_verified, agreement_signed, registered, completed, cancelled, refunded
    status = Column(String, nullable=False, default="draft")

    # Buyer & Co-buyer Details Snapshot
    buyer_legal_name = Column(String, nullable=False)
    buyer_id_number = Column(String, nullable=True)  # PAN / Aadhaar / National ID
    co_buyers = Column(JSON, default=list)
    payment_plan = Column(JSON, default=dict)  # construction-linked milestones

    # Approvals & Auditing
    sales_rep_id = Column(String, nullable=True)
    approved_by_user_id = Column(String, nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    cancellation_reason = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class RealEstatePaymentTransaction(Base):
    """Immutable ledger of payment events verified against banking or gateway sources."""

    __tablename__ = "real_estate_payment_transactions"

    id = Column(String, primary_key=True, default=_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    booking_id = Column(String, ForeignKey("real_estate_bookings.id"), nullable=True, index=True)
    hold_id = Column(String, ForeignKey("real_estate_unit_holds.id"), nullable=True, index=True)
    lead_id = Column(String, ForeignKey("leads.id"), nullable=False, index=True)

    transaction_type = Column(String, nullable=False)  # token_deposit, milestone_payment, refund, maintenance_fee
    amount = Column(Float, nullable=False)
    currency = Column(String, default="INR")
    status = Column(String, nullable=False, default="pending")  # pending, verified, rejected, refunded

    payment_method = Column(String, nullable=False)  # wire, card, upi, cheque, gateway
    payment_reference = Column(String, nullable=True, index=True)  # UTR, Gateway charge ID
    idempotency_key = Column(String, unique=True, nullable=False, index=True)

    proof_document_url = Column(String, nullable=True)
    verified_by_user_id = Column(String, nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RealEstateCommissionLedger(Base):
    """Channel partner commission accruals, milestones, and payout tracking."""

    __tablename__ = "real_estate_commission_ledgers"

    id = Column(String, primary_key=True, default=_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    booking_id = Column(String, ForeignKey("real_estate_bookings.id"), nullable=False, index=True)
    broker_attribution_id = Column(String, ForeignKey("real_estate_broker_attributions.id"), nullable=False, index=True)

    total_commission_amount = Column(Float, nullable=False)
    milestone_number = Column(Integer, default=1)
    milestone_name = Column(String, nullable=False)  # e.g., "Token Deposit (20%)", "Agreement Registered (80%)"
    payable_amount = Column(Float, nullable=False)
    status = Column(String, nullable=False, default="accrued")  # accrued, approved, paid, reversed, disputed

    due_date = Column(DateTime(timezone=True), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    payout_reference = Column(String, nullable=True)
    approved_by_user_id = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class RealEstateProjectAssignment(Base):
    """Mapping between Real Estate Projects and Sales Persons / Agents."""

    __tablename__ = "real_estate_project_assignments"

    id = Column(String, primary_key=True, default=_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    project_id = Column(String, ForeignKey("real_estate_projects.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String, default="site_specialist")  # primary_lead, site_specialist, relationship_manager
    is_active = Column(Boolean, default=True)
    ai_recommended = Column(Boolean, default=False)
    ai_recommendation_reason = Column(Text, nullable=True)
    ai_match_score = Column(Float, nullable=True)
    assigned_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "project_id", "user_id", name="uq_project_agent_assignment"),
    )

