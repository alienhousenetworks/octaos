import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Numeric, DateTime,
    ForeignKey, JSON, Text, Boolean, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import Base


class BusinessObjective(Base):
    """
    Core Business Autonomy Model:
    Stores company objectives as measurable, versioned commitments.
    Connects each objective to target KPIs, baselines, deadlines, accountable owners,
    dependencies, and permitted budget ceilings.
    """
    __tablename__ = "business_objectives"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    department = Column(String(64), nullable=True)  # None = Corporate / Enterprise-wide
    owner_user_id = Column(String(64), nullable=False)
    
    # Target Metric & Measurable Commitment
    target_metric = Column(String(128), nullable=False)  # e.g. "mrr_growth", "churn_reduction", "leads_sourced"
    baseline_value = Column(Float, nullable=False)
    target_value = Column(Float, nullable=False)
    current_value = Column(Float, nullable=False, default=0.0)
    unit = Column(String(32), nullable=False)  # "USD", "percent", "count", "ratio"
    priority = Column(Integer, nullable=False, default=1)  # 1 = Highest
    
    # Financial Envelopes
    budget_limit = Column(Numeric(12, 2), nullable=False, default=0.00)
    consumed_budget = Column(Numeric(12, 2), nullable=False, default=0.00)
    
    # Lifecycle & Constraints
    deadline = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(32), nullable=False, default="ACTIVE")  # DRAFT, ACTIVE, PAUSED, COMPLETED, MISSED, CANCELLED
    constraints = Column(JSON, nullable=False, default=dict)  # e.g. {"max_cac": 250, "min_gross_margin": 0.50}
    success_criteria = Column(JSON, nullable=False, default=list)  # list of explicit rule dicts
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    plans = relationship("PlanVersion", back_populates="objective_rel")
    metric_snapshots = relationship("ObjectiveMetric", back_populates="objective", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("tenant_id", "title", "version", name="uq_tenant_objective_version"),
    )


class ObjectiveMetric(Base):
    """
    Time-series verification snapshots of an objective's measured progress,
    linking real telemetry and evidence to strategic goals.
    """
    __tablename__ = "objective_metrics"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    objective_id = Column(String, ForeignKey("business_objectives.id", ondelete="CASCADE"), nullable=False, index=True)
    
    measured_value = Column(Float, nullable=False)
    budget_spent_to_date = Column(Numeric(12, 2), nullable=False, default=0.00)
    evidence_source = Column(String(64), nullable=True)  # e.g., "stripe_sync", "crm_deal_sync", "manual"
    evidence_reference_id = Column(String(128), nullable=True)
    variance_pct = Column(Float, nullable=False, default=0.0)  # (measured - target) / target
    
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())

    objective = relationship("BusinessObjective", back_populates="metric_snapshots")
