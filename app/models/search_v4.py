"""Durable search jobs, cached provider results, and reconciled spend."""
import uuid

from sqlalchemy import Column, DateTime, Float, ForeignKey, JSON, String
from sqlalchemy.sql import func

from app.models.base import Base


def _id() -> str:
    return str(uuid.uuid4())


class SearchV4Job(Base):
    __tablename__ = "search_v4_jobs"

    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    status = Column(String, nullable=False, default="running")
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SearchV4TaskRow(Base):
    __tablename__ = "search_v4_tasks"

    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="planned")
    result = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SearchV4LedgerRow(Base):
    __tablename__ = "search_v4_ledger"

    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    correlation_id = Column(String, nullable=True, index=True)
    provider = Column(String, nullable=False)
    operation = Column(String, nullable=False)
    estimated_cost_inr = Column(Float, nullable=False, default=0.0)
    actual_cost_inr = Column(Float, nullable=False, default=0.0)
    currency = Column(String, nullable=False, default="INR")
    status = Column(String, nullable=False, default="reconciled")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
