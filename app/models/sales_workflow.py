"""Durable, tenant-scoped Sales AI run and step ledger."""
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, JSON, String, Text, UniqueConstraint
from sqlalchemy.sql import func

from app.models.base import Base


def _id() -> str:
    return str(uuid.uuid4())


class SalesWorkflowRun(Base):
    __tablename__ = "sales_workflow_runs"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_sales_run_tenant_idempotency"),
        Index("ix_sales_run_tenant_status", "tenant_id", "status"),
    )

    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    campaign_id = Column(String, nullable=False, index=True)
    idempotency_key = Column(String, nullable=False)
    status = Column(String, nullable=False, default="queued")
    current_stage = Column(String, nullable=False, default="discovery")
    input_payload = Column(JSON, nullable=False, default=dict)
    result_payload = Column(JSON, nullable=True)
    failure_code = Column(String, nullable=True)
    failure_detail = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class SalesWorkflowStep(Base):
    __tablename__ = "sales_workflow_steps"
    __table_args__ = (
        UniqueConstraint("tenant_id", "run_id", "step_key", name="uq_sales_step_run_key"),
        Index("ix_sales_step_tenant_run_status", "tenant_id", "run_id", "status"),
    )

    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    run_id = Column(String, ForeignKey("sales_workflow_runs.id"), nullable=False, index=True)
    step_key = Column(String, nullable=False)
    stage = Column(String, nullable=False)
    status = Column(String, nullable=False, default="queued")
    attempt = Column(String, nullable=False, default="0")
    idempotency_key = Column(String, nullable=False)
    input_payload = Column(JSON, nullable=False, default=dict)
    result_payload = Column(JSON, nullable=True)
    error_code = Column(String, nullable=True)
    error_detail = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
