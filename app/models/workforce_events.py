"""Persistent tenant-scoped workforce event log."""
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, JSON, String, UniqueConstraint
from sqlalchemy.sql import func

from app.models.base import Base


class WorkforceEvent(Base):
    __tablename__ = "workforce_events"
    __table_args__ = (
        UniqueConstraint("tenant_id", "event_key", name="uq_workforce_event_tenant_key"),
        Index("ix_workforce_event_tenant_created", "tenant_id", "created_at", "id"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    event_key = Column(String, nullable=False)
    event_type = Column(String, nullable=False, index=True)
    source = Column(String, nullable=False, default="system")
    run_id = Column(String, nullable=True, index=True)
    agent_id = Column(String, nullable=True, index=True)
    actor_user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
