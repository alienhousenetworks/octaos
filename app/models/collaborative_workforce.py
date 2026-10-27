"""Durable, tenant-isolated records for cross-agent collaboration.

Messages and delegation receipts are persisted independently of an LLM turn so a
worker restart does not erase hand-offs or make a generated answer count as success.
"""
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.sql import func

from app.models.base import Base


def _id() -> str:
    return str(uuid.uuid4())


class AgentMessage(Base):
    __tablename__ = "agent_messages"

    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    correlation_id = Column(String(120), nullable=False, index=True)
    idempotency_key = Column(String(180), nullable=False)
    from_agent = Column(String(160), nullable=False)
    to_agent = Column(String(160), nullable=False, index=True)
    message_type = Column(String(40), nullable=False, default="request")
    status = Column(String(24), nullable=False, default="queued", index=True)
    payload = Column(JSON, nullable=False, default=dict)
    response = Column(JSON, nullable=True)
    error_code = Column(String(80), nullable=True)
    attempt_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("uq_agent_message_tenant_idempotency", "tenant_id", "idempotency_key", unique=True),
        Index("ix_agent_message_inbox", "tenant_id", "to_agent", "status", "created_at"),
    )


class DelegationReceipt(Base):
    """A claimed result is not verified until required checks have been recorded."""
    __tablename__ = "agent_delegation_receipts"

    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    task_id = Column(String, nullable=False, index=True)
    parent_agent = Column(String(160), nullable=False)
    child_agent = Column(String(160), nullable=False)
    request_message_id = Column(String, ForeignKey("agent_messages.id"), nullable=False, unique=True)
    status = Column(String(24), nullable=False, default="requested", index=True)
    acceptance_criteria = Column(JSON, nullable=False, default=list)
    evidence = Column(JSON, nullable=False, default=list)
    result = Column(JSON, nullable=True)
    verification_errors = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class KnowledgeSyncRun(Base):
    """Durable sync cursor/status; content must be verified before replacing active truth."""
    __tablename__ = "knowledge_sync_runs"

    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    source_id = Column(String, ForeignKey("knowledge_sources.id"), nullable=False, index=True)
    status = Column(String(24), nullable=False, default="queued", index=True)
    cursor = Column(Text, nullable=True)
    pages_seen = Column(Integer, nullable=False, default=0)
    documents_changed = Column(Integer, nullable=False, default=0)
    error_code = Column(String(80), nullable=True)
    error_detail = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
