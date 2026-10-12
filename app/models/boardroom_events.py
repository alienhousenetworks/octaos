"""
Boardroom V2 — append-only event log, evidence catalog, and governed action table.
These three tables replace the JSON-column approach for auditability and governance.
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text, JSON, Float
from app.models.base import Base
import uuid
from sqlalchemy.sql import func


class MeetingEvent(Base):
    """
    Append-only ordered log of everything that happens in a boardroom meeting.
    Serves as: live-stream source (Redis pub/sub), audit trail, and SSE replay buffer.
    `seq` is monotonically increasing per meeting and used as SSE Last-Event-ID.
    """
    __tablename__ = "meeting_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    meeting_id = Column(String, ForeignKey("agent_meetings.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    seq = Column(Integer, nullable=False)           # ordered, resumable
    event_type = Column(String, nullable=False)
    # meeting.started | phase.changed | agent.thinking | agent.completed | agent.failed |
    # evidence.added | critique.posted | synthesis.posted |
    # action.proposed | action.approved | action.rejected | action.executed |
    # meeting.completed | meeting.failed | meeting.cancelled
    phase = Column(String, nullable=True)           # boardroom phase at time of event
    actor = Column(String, nullable=True)           # agent name, user ID, or "system"
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MeetingEvidence(Base):
    """
    Typed, trust-scored evidence sources collected before agent analysis begins.
    Each row is a source the agents can cite by `source_ref`.
    The `redacted` flag allows PII-safe exports.
    """
    __tablename__ = "meeting_evidence"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    meeting_id = Column(String, ForeignKey("agent_meetings.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    source_ref = Column(String, nullable=False)     # e.g., "ticket:abc123", "knowledge:xyz"
    source_type = Column(String, nullable=False)
    # support_ticket | knowledge_base | db_query | credential_inventory | meeting_context
    trust_score = Column(Integer, nullable=True)    # 0-100 overall
    freshness_score = Column(Integer, nullable=True)
    reliability_score = Column(Integer, nullable=True)
    completeness_score = Column(Integer, nullable=True)
    excerpt = Column(Text, nullable=True)           # short human-readable summary
    redacted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MeetingAction(Base):
    """
    A proposed action item from the boardroom, with risk-tiered approval state.
    Replaces the ad-hoc `action_items` JSON column with a proper governance record.
    `idempotency_key` ensures retries never create duplicate leads/replies/promotions.
    """
    __tablename__ = "meeting_actions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    meeting_id = Column(String, ForeignKey("agent_meetings.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    action_type = Column(String, nullable=False)
    # create_lead | send_customer_reply | promote_candidate | update_ticket_status |
    # create_internal_note | tag_lead | unknown
    assigned_to = Column(String, nullable=False)    # e.g., "Sales AI", "Support AI"
    description = Column(Text, nullable=False)
    risk_tier = Column(String, nullable=False)      # low | medium | high
    status = Column(String, default="pending")
    # pending | awaiting_approval | executing | completed | failed | rejected
    idempotency_key = Column(String, nullable=True, unique=True)
    approved_by = Column(String, nullable=True)     # user ID, "auto", or "auto-confidence"
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejected_by = Column(String, nullable=True)
    rejected_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    result = Column(JSON, nullable=True)            # execution output
    evidence_ids = Column(JSON, default=list)       # list of MeetingEvidence.id
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DecisionCharter(Base):
    """
    Stage 2 — Decision Charter.
    Locks criteria weights, decision owner, approvers, and cost of delay BEFORE options are debated.
    """
    __tablename__ = "boardroom_charters"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    meeting_id = Column(String, ForeignKey("agent_meetings.id", ondelete="CASCADE"),
                        nullable=False, unique=True, index=True)
    decision_type = Column(String, default="type_1")  # type_1 (irreversible) | type_2 (reversible)
    question = Column(Text, nullable=False)
    decision_owner = Column(String, default="CEO AI")
    approvers = Column(JSON, default=list)            # ["CFO AI", "Legal AI"]
    deadline = Column(DateTime(timezone=True), nullable=True)
    cost_of_delay_per_week = Column(Float, default=0.0)
    criteria_weights = Column(JSON, default=list)     # [{"name": "margin", "weight": 0.35}, ...]
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MeetingOption(Base):
    """
    Stage 5 & 6 — Quantified Options Generation & Modeling.
    Always includes at least 3 options: do nothing / defer, pilot / staged, and full scale.
    """
    __tablename__ = "boardroom_options"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    meeting_id = Column(String, ForeignKey("agent_meetings.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    option_code = Column(String, nullable=False)      # A, B, C...
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    is_do_nothing = Column(Boolean, default=False)
    is_pilot = Column(Boolean, default=False)
    reversibility = Column(String, default="medium")  # high, medium, low
    financial_model = Column(JSON, default=dict)      # {ev, payback_months, downside_p10, assumptions}
    weighted_score = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MeetingPosition(Base):
    """
    Stage 4 & 8 — Blind First Positions & Structured Multi-Round Debate.
    Mandatory claim format: Position → Evidence IDs → Assumptions → Confidence (0-100) → What would change my mind.
    """
    __tablename__ = "boardroom_positions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    meeting_id = Column(String, ForeignKey("agent_meetings.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    round = Column(Integer, default=1)                # 1 = blind first position, 2+ = debate
    agent = Column(String, nullable=False)
    preferred_option = Column(String, nullable=True)  # Option code (A, B, C)
    position_statement = Column(Text, nullable=False)
    evidence_ids = Column(JSON, default=list)
    assumptions = Column(JSON, default=list)
    confidence = Column(Integer, nullable=False)      # 0-100
    what_would_change_mind = Column(Text, nullable=True)
    is_veto = Column(Boolean, default=False)
    veto_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DissentRecord(Base):
    """
    Stage 10 — Dissent Register.
    Tracks explicit unaddressed objections and overrides for audit and compliance.
    """
    __tablename__ = "boardroom_dissents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    meeting_id = Column(String, ForeignKey("agent_meetings.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    agent = Column(String, nullable=False)
    dissent_position = Column(Text, nullable=False)
    preferred_option = Column(String, nullable=True)
    addressed = Column(Boolean, default=False)
    override_rationale = Column(Text, nullable=True)
    requires_human_signoff = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DecisionOutcome(Base):
    """
    Stage 11 & 12 — Governed Tripwires, Review Milestones, and Brier Score Calibration.
    Compares predicted vs actual at 30/90/180 days to update agent reliability.
    """
    __tablename__ = "boardroom_outcomes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    meeting_id = Column(String, ForeignKey("agent_meetings.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    review_milestone = Column(String, nullable=False) # 30d, 90d, 180d
    review_date = Column(DateTime(timezone=True), nullable=False)
    tripwires = Column(JSON, default=list)            # ["CAC > $350", "Margin < 40%"]
    tripwire_triggered = Column(Boolean, default=False)
    predicted_metrics = Column(JSON, default=dict)
    actual_metrics = Column(JSON, default=dict)
    agent_brier_scores = Column(JSON, default=dict)   # {"CFO AI": 0.12, "CRO AI": 0.38}
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
