import uuid
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base

class DecisionRecord(Base):
    """
    Logs a structured decision record for every action an agent takes.
    Acts as the evidence store for learning and optimization.
    """
    __tablename__ = "decision_records"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    
    agent_name = Column(String, nullable=False, index=True)
    task_type = Column(String, nullable=False, index=True)
    strategy_used = Column(String, nullable=False)
    prompt_version = Column(String, nullable=False)
    confidence_score = Column(Float, nullable=False)
    
    # Key signals used for decision
    context_features = Column(JSON, default={})
    
    # Outcome Tracking
    result_status = Column(String, nullable=True) # success, failure, partial
    quality_score = Column(Float, nullable=True) # 0-100 normalized
    user_feedback_score = Column(Float, nullable=True)
    behavioral_signals = Column(JSON, default={}) # e.g. {"reply_received": True, "conversion": False}
    
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    outcome_timestamp = Column(DateTime(timezone=True), nullable=True)


class StrategyPerformance(Base):
    """
    Maintains an evolving Strategy Performance Model for EMA and Multi-Armed Bandit selection.
    """
    __tablename__ = "strategy_performance"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    
    agent_name = Column(String, nullable=False, index=True)
    task_type = Column(String, nullable=False, index=True)
    strategy_name = Column(String, nullable=False, index=True)
    
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    
    weighted_reward_score = Column(Float, default=0.0)
    rolling_success_rate = Column(Float, default=0.0)
    recent_trend_score = Column(Float, default=0.0)
    
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class NegativePatternMemory(Base):
    """
    Stores failure signatures to actively bias future decisions away from similar failures.
    """
    __tablename__ = "negative_pattern_memory"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    
    agent_name = Column(String, nullable=False, index=True)
    task_type = Column(String, nullable=False)
    
    failure_reason_category = Column(String, nullable=False) # e.g., tone_mismatch, overly_long_response
    pattern_signature = Column(String, nullable=False) # textual or regex signature
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
