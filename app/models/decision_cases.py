import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Numeric, DateTime,
    ForeignKey, JSON, Text, Boolean, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import Base


class DecisionCase(Base):
    """
    Core Decision Intelligence & Assurance Model:
    Every consequential business decision gets a durable case containing
    the proposal, business rationale, alternatives, assumptions, evidence,
    financial exposure, deadlines, and accountable decision owner.
    """
    __tablename__ = "decision_cases"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    case_number = Column(String(64), nullable=False)  # e.g., "DEC-2026-0001"
    
    # Linkage to Business Autonomy & Workflows
    objective_id = Column(String, ForeignKey("business_objectives.id", ondelete="SET NULL"), nullable=True, index=True)
    workflow_id = Column(String, ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True, index=True)
    plan_version_id = Column(String, ForeignKey("plan_versions.id", ondelete="SET NULL"), nullable=True, index=True)

    title = Column(String(255), nullable=False)
    proposal_summary = Column(Text, nullable=False)
    business_rationale = Column(Text, nullable=False)
    risk_class = Column(String(32), nullable=False, default="R1_INTERNAL_REVERSIBLE")
    # 'R0_INFORMATIONAL', 'R1_INTERNAL_REVERSIBLE', 'R2_EXTERNAL_REVERSIBLE', 'R3_EXTERNAL_IRREVERSIBLE', 'R4_FINANCIAL_CRITICAL'
    
    financial_exposure = Column(Numeric(12, 2), nullable=False, default=0.00)
    reversibility = Column(String(16), nullable=False, default="MEDIUM")  # HIGH, MEDIUM, LOW, IRREVERSIBLE
    cost_of_delay_per_week = Column(Numeric(12, 2), nullable=False, default=0.00)
    
    # Ownership and Delegation
    decision_owner_user_id = Column(String(64), nullable=False)
    requester_user_id = Column(String(64), nullable=True)  # Enforces anti-self-approval
    deadline = Column(DateTime(timezone=True), nullable=True)
    
    status = Column(String(32), nullable=False, default="PROPOSED")
    # PROPOSED | UNDER_ASSURANCE | REQUIRE_APPROVAL | AUTHORIZED | REJECTED | EXECUTED | VERIFIED | EXPIRED

    # Multi-Disciplinary Independent Assurance Snapshots (Real Decision Science)
    assumptions = Column(JSON, nullable=False, default=list)
    uncertainties = Column(JSON, nullable=False, default=list)
    financial_assessment = Column(JSON, nullable=False, default=dict)
    # e.g., {"downside_p10": -500, "expected_value": 2400, "margin_impact_bps": -20, "payback_months": 3.5}
    compliance_assessment = Column(JSON, nullable=False, default=dict)
    # e.g., {"passed": true, "evaluated_rules_count": 4, "violations": []}
    operational_feasibility = Column(JSON, nullable=False, default=dict)
    # e.g., {"credentials_valid": true, "capacity_score": 0.95, "rate_limit_headroom": 0.88}

    selected_alternative_code = Column(String(16), nullable=True)
    active_grant_id = Column(String(64), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    alternatives = relationship("DecisionAlternative", back_populates="case", cascade="all, delete-orphan")
    grants = relationship("DecisionGrant", back_populates="case", cascade="all, delete-orphan")
    outcomes = relationship("DecisionOutcomeReview", back_populates="case", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("tenant_id", "case_number", name="uq_tenant_case_number"),
    )


class DecisionAlternative(Base):
    """
    Quantified options modeled for a decision case.
    Always includes at least do-nothing, pilot/staged, and full execution options.
    """
    __tablename__ = "decision_alternatives"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String, ForeignKey("decision_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    alternative_code = Column(String(16), nullable=False)  # "A", "B", "C"
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    
    is_do_nothing = Column(Boolean, nullable=False, default=False)
    is_pilot = Column(Boolean, nullable=False, default=False)
    reversibility = Column(String(16), nullable=False, default="MEDIUM")
    
    financial_model = Column(JSON, nullable=False, default=dict)
    # {"estimated_cost": 2000, "downside_p10": -500, "expected_outcome": 5000, "confidence": 0.85}
    score = Column(Float, nullable=False, default=0.0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    case = relationship("DecisionCase", back_populates="alternatives")


class DecisionGrant(Base):
    """
    Formal, cryptographically bound authorization token issued by an authorized human
    or delegated policy authority. Records exact policy version, payload hash, and scope.
    """
    __tablename__ = "decision_grants"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    case_id = Column(String, ForeignKey("decision_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    
    decision = Column(String(16), nullable=False)  # "APPROVE", "REJECT"
    granter_user_id = Column(String(64), nullable=False)
    granter_role = Column(String(32), nullable=False)
    delegation_level = Column(String(32), nullable=False)  # "DELEGATED_L1", "MANAGER_L2", "EXECUTIVE_L3", "DUAL_KEY_L4"
    
    action_hash = Column(String(64), nullable=False)  # SHA-256 hash of the exact execution payload
    policy_version = Column(String(32), nullable=False, default="1.0")
    rationale = Column(Text, nullable=False)
    conditions = Column(JSON, nullable=False, default=list)
    
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_revoked = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    case = relationship("DecisionCase", back_populates="grants")


class DecisionOutcomeReview(Base):
    """
    Decision Outcome Review & Calibration:
    Compares predicted consequences with actual business telemetry at 30/90/180 days.
    Calculates Brier calibration scores and triggers tripwires on failed assumptions.
    """
    __tablename__ = "decision_outcome_reviews"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    case_id = Column(String, ForeignKey("decision_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    
    milestone = Column(String(32), nullable=False)  # "30d", "90d", "180d", "incident_triggered"
    scheduled_for = Column(DateTime(timezone=True), nullable=False)
    
    tripwires = Column(JSON, nullable=False, default=list)  # e.g., [{"metric": "cac", "operator": ">", "threshold": 300}]
    tripwire_triggered = Column(Boolean, nullable=False, default=False)
    
    predicted_metrics = Column(JSON, nullable=False, default=dict)
    actual_metrics = Column(JSON, nullable=False, default=dict)
    brier_score = Column(Float, nullable=True)  # Prediction calibration accuracy
    
    review_notes = Column(Text, nullable=True)
    reviewed_by_user_id = Column(String(64), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    case = relationship("DecisionCase", back_populates="outcomes")
