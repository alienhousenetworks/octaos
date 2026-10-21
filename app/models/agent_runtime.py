"""Enterprise Agent Runtime models: durable runs, tasks, tool invocations, and agent handoffs."""
import uuid
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, JSON, Text, Index
from sqlalchemy.sql import func

from app.models.base import Base


def _id() -> str:
    return str(uuid.uuid4())


class AgentRun(Base):
    """A durable execution session for an agent or orchestrator."""

    __tablename__ = "agent_runs"

    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    agent_id = Column(String, nullable=False, index=True)
    version = Column(String, nullable=False, default="1.0.0")
    status = Column(
        String,
        nullable=False,
        default="pending",
        index=True,
    )  # pending | running | waiting_for_approval | retrying | completed | failed | cancelled
    goal = Column(Text, nullable=True)
    deal_room_id = Column(String, ForeignKey("deal_rooms.id"), nullable=True, index=True)
    company_id = Column(String, ForeignKey("sales_companies.id"), nullable=True, index=True)
    lead_id = Column(String, ForeignKey("leads.id"), nullable=True, index=True)
    idempotency_key = Column(String, nullable=True, index=True)
    input_payload = Column(JSON, default=dict)
    output_payload = Column(JSON, default=dict)
    error_summary = Column(Text, nullable=True)
    tokens_used = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_agent_runs_tenant_agent", "tenant_id", "agent_id"),
        Index("ix_agent_runs_tenant_status", "tenant_id", "status"),
    )


class AgentTask(Base):
    """A discrete unit of reasoning, planning, or tool dispatch inside a run."""

    __tablename__ = "agent_tasks"

    id = Column(String, primary_key=True, default=_id)
    run_id = Column(String, ForeignKey("agent_runs.id"), nullable=False, index=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    agent_id = Column(String, nullable=False)
    task_type = Column(String, nullable=False, index=True)
    status = Column(
        String,
        nullable=False,
        default="pending",
        index=True,
    )  # pending | executing | verified | failed
    input_data = Column(JSON, default=dict)
    output_data = Column(JSON, default=dict)
    verification_result = Column(JSON, default=dict)
    retries = Column(Integer, default=0)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ToolInvocation(Base):
    """Immutable audit record of a tool execution with side-effect verification."""

    __tablename__ = "agent_tool_invocations"

    id = Column(String, primary_key=True, default=_id)
    run_id = Column(String, ForeignKey("agent_runs.id"), nullable=True, index=True)
    task_id = Column(String, ForeignKey("agent_tasks.id"), nullable=True, index=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    agent_id = Column(String, nullable=False)
    tool_name = Column(String, nullable=False, index=True)
    parameters = Column(JSON, default=dict)
    parameters_hash = Column(String, nullable=True, index=True)
    result = Column(JSON, default=dict)
    verified = Column(Boolean, default=True)
    verification_details = Column(Text, nullable=True)
    latency_ms = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AgentHandoff(Base):
    """Traceable task handoff between two specialized agents."""

    __tablename__ = "agent_handoffs"

    id = Column(String, primary_key=True, default=_id)
    run_id = Column(String, ForeignKey("agent_runs.id"), nullable=False, index=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    from_agent = Column(String, nullable=False, index=True)
    to_agent = Column(String, nullable=False, index=True)
    objective = Column(Text, nullable=False)
    payload = Column(JSON, default=dict)
    constraints = Column(JSON, default=dict)
    status = Column(
        String,
        nullable=False,
        default="pending",
        index=True,
    )  # pending | accepted | completed | rejected
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
