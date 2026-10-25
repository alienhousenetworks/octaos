"""Persistent records for OctaOS autonomous work.

These tables intentionally separate the user's goal from execution events so tasks
can be resumed, audited, and verified without treating an LLM response as success.
"""
import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.sql import func

from app.models.base import Base


def _id() -> str:
    return str(uuid.uuid4())


class AutonomousTask(Base):
    __tablename__ = "autonomous_tasks"

    id = Column(String, primary_key=True, default=_id, index=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    organization_id = Column(String, nullable=True, index=True)
    created_by_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(240), nullable=False)
    goal = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="queued", index=True)
    autonomy_level = Column(String(24), nullable=False, default="supervised")
    risk_level = Column(String(24), nullable=False, default="standard")
    acceptance_criteria = Column(JSON, nullable=False, default=list)
    context = Column(JSON, nullable=False, default=dict)
    result = Column(JSON, nullable=True)
    blocker = Column(Text, nullable=True)
    error_code = Column(String(80), nullable=True)
    idempotency_key = Column(String(160), nullable=True)
    attempt_count = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=3)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_autonomous_tasks_tenant_status_created", "tenant_id", "status", "created_at"),
        Index("ix_autonomous_tasks_tenant_idempotency", "tenant_id", "idempotency_key", unique=True),
    )


class AutonomousTaskEvent(Base):
    __tablename__ = "autonomous_task_events"

    id = Column(String, primary_key=True, default=_id, index=True)
    task_id = Column(String, ForeignKey("autonomous_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    actor_type = Column(String(24), nullable=False, default="system")
    actor_id = Column(String, nullable=True)
    event_type = Column(String(80), nullable=False, index=True)
    message = Column(Text, nullable=False)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AutonomousApproval(Base):
    __tablename__ = "autonomous_approvals"

    id = Column(String, primary_key=True, default=_id, index=True)
    task_id = Column(String, ForeignKey("autonomous_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    requested_by_agent = Column(String(120), nullable=False)
    action_name = Column(String(160), nullable=False)
    action_payload = Column(JSON, nullable=False, default=dict)
    reason = Column(Text, nullable=False)
    status = Column(String(24), nullable=False, default="pending", index=True)
    decided_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    decision_note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    decided_at = Column(DateTime(timezone=True), nullable=True)


class AutonomousSkillVersion(Base):
    __tablename__ = "autonomous_skill_versions"

    id = Column(String, primary_key=True, default=_id, index=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(160), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    description = Column(Text, nullable=False, default="")
    definition = Column(JSON, nullable=False, default=dict)
    status = Column(String(24), nullable=False, default="draft", index=True)
    created_by_id = Column(String, ForeignKey("users.id"), nullable=False)
    approved_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_autonomous_skill_tenant_name_version", "tenant_id", "name", "version", unique=True),
    )
