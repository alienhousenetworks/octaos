import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DecisionRecord(Base):
    __tablename__ = "decision_records"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True, nullable=False)
    agent_name: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    task_type: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    strategy_used: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), default="v1")
    confidence_score: Mapped[float] = mapped_column(Float, default=0.7)
    context_features: Mapped[dict] = mapped_column(JSON, default=dict)

    result_status: Mapped[str | None] = mapped_column(String(32), nullable=True)  # success|failure|partial
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    user_feedback_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    behavioral_signals: Mapped[dict] = mapped_column(JSON, default=dict)

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    outcome_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class StrategyPerformance(Base):
    __tablename__ = "strategy_performance"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True, nullable=False)
    agent_name: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    task_type: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    strategy_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)

    success_count: Mapped[int] = mapped_column(Integer, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    weighted_reward_score: Mapped[float] = mapped_column(Float, default=0.0)
    rolling_success_rate: Mapped[float] = mapped_column(Float, default=0.0)
    recent_trend_score: Mapped[float] = mapped_column(Float, default=0.0)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class NegativePatternMemory(Base):
    __tablename__ = "negative_pattern_memory"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True, nullable=False)
    agent_name: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    task_type: Mapped[str] = mapped_column(String(128), nullable=False)
    failure_reason_category: Mapped[str] = mapped_column(String(128), nullable=False)
    pattern_signature: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
