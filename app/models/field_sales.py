"""Main database models for Field Sales, Dispatch Telemetry, Schedule Recovery, and Connector Usage."""
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
    JSON,
    Index,
)
from sqlalchemy.sql import func
from app.models.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class SalespersonFieldStatus(Base):
    """
    Live shift telemetry and geographic positioning of a salesperson.
    Persisted in the main tenant database.
    """

    __tablename__ = "field_sales_agent_status"

    id = Column(String, primary_key=True, default=_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    # Telemetry
    last_latitude = Column(Float, nullable=True)
    last_longitude = Column(Float, nullable=True)
    last_accuracy = Column(Float, nullable=True)  # in meters
    last_location_updated_at = Column(DateTime(timezone=True), nullable=True)
    battery_level = Column(Integer, nullable=True)  # 0 to 100 percentage
    speed = Column(Float, nullable=True)  # meters/second
    heading = Column(Float, nullable=True)  # degrees (0-360)

    # Shift & Availability
    is_shift_active = Column(Boolean, default=False)
    shift_started_at = Column(DateTime(timezone=True), nullable=True)
    shift_ended_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, default="off_duty")  # off_duty, available, en_route, in_showing, on_break
    working_hours_start = Column(String, default="09:00")
    working_hours_end = Column(String, default="18:00")
    max_visits_per_day = Column(Integer, default=6)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class FieldScheduleRecoveryProposal(Base):
    """
    Autonomous schedule recovery recommendations generated when an agent is delayed,
    a customer reschedules, or an appointment runs over time.
    """

    __tablename__ = "field_schedule_recovery_proposals"

    id = Column(String, primary_key=True, default=_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    trigger_type = Column(String, nullable=False)  # agent_delay, buyer_cancel, no_show, manual_optimizer
    affected_user_id = Column(String, nullable=True, index=True)
    affected_visit_id = Column(String, nullable=True, index=True)
    status = Column(String, default="pending_review")  # pending_review, approved, rejected, applied
    rationale = Column(Text, nullable=True)
    
    # Structured diff: list of dicts with visit_id, original_time, proposed_time, original_agent, proposed_agent, rationale
    proposed_changes = Column(JSON, default=list)

    reviewed_by_user_id = Column(String, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ConnectorUsageAudit(Base):
    """
    Audit ledger of third-party API consumption for budget control and quota governance.
    """

    __tablename__ = "connector_usage_audits"

    id = Column(String, primary_key=True, default=_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    provider = Column(String, nullable=False)  # google_maps, mapbox, local_fallback, push_notifications, sms
    endpoint = Column(String, nullable=False)  # routes, matrix, geocode, places
    call_count = Column(Integer, default=1)
    cost_estimate_usd = Column(Float, default=0.0)
    cache_hit = Column(Boolean, default=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
