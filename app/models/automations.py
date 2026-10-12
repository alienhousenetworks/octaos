from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import Base
import uuid


class AutomationTenantEnvironment(Base):
    """
    Manages tenant-isolated Activepieces automation engine workspaces/containers.
    Tracks resource allocations, provisioning state, and isolated subdomains.
    """
    __tablename__ = "automation_tenant_environments"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, unique=True, index=True)
    engine_type = Column(String, nullable=False, default="activepieces")
    subdomain = Column(String, nullable=True)  # e.g. tenant-123.flows.octaos.org
    workspace_url = Column(String, nullable=True)
    workspace_api_key = Column(String, nullable=True)  # Encrypted master API key for this workspace
    status = Column(String, default="active", index=True)  # active, idle, suspended, provisioning, recovering, decommissioning

    # Resource quotas & limits
    cpu_limit = Column(String, default="1.0")
    memory_limit = Column(String, default="1Gi")
    execution_limit_monthly = Column(Integer, default=5000)
    concurrency_limit = Column(Integer, default=5)
    workflow_limit = Column(Integer, default=50)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AutomationWorkflow(Base):
    """
    Core OctaOS Automation definition.
    Stores the canonical Intermediate Representation (IR) and compiles to Activepieces.
    """
    __tablename__ = "automation_workflows"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    category = Column(String, nullable=False, default="operations")  # sales, support, marketing, operations, hr, executive

    # Lifecycle state
    status = Column(String, default="draft", index=True)  # draft, validating, ready, active, paused, failed, archived
    engine_type = Column(String, default="activepieces")
    external_flow_id = Column(String, nullable=True, index=True)  # Activepieces flowId

    # Trigger metadata
    trigger_type = Column(String, default="octaos_event")  # octaos_event, webhook, schedule, manual
    trigger_event = Column(String, nullable=True, index=True)  # e.g. lead.qualified, ticket.escalated

    # Intermediate Representation (OctaOS canonical definition)
    definition_ir = Column(JSON, nullable=False, default=dict)
    # Compiled target schema (Activepieces JSON)
    compiled_schema = Column(JSON, nullable=False, default=dict)

    current_version = Column(Integer, default=1)
    is_ai_generated = Column(Boolean, default=False)
    ai_prompt = Column(Text, nullable=True)

    # Governance & Safety
    requires_approval = Column(Boolean, default=False)
    risk_level = Column(String, default="low")  # low, medium, high, critical
    created_by_user_id = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    versions = relationship("AutomationWorkflowVersion", back_populates="workflow", cascade="all, delete-orphan", order_by="desc(AutomationWorkflowVersion.version)")
    executions = relationship("AutomationExecution", back_populates="workflow", cascade="all, delete-orphan", order_by="desc(AutomationExecution.created_at)")


class AutomationWorkflowVersion(Base):
    """
    Version history for auditing, rollback, and comparison.
    """
    __tablename__ = "automation_workflow_versions"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String, ForeignKey("automation_workflows.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    definition_ir = Column(JSON, nullable=False, default=dict)
    compiled_schema = Column(JSON, nullable=False, default=dict)
    change_reason = Column(String, nullable=True)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    workflow = relationship("AutomationWorkflow", back_populates="versions")


class AutomationExecution(Base):
    """
    Unified execution observability across all automation engines.
    Classifies failures into explicit enterprise diagnostics.
    """
    __tablename__ = "automation_executions"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    workflow_id = Column(String, ForeignKey("automation_workflows.id"), nullable=False, index=True)
    external_execution_id = Column(String, nullable=True, index=True)

    trigger_type = Column(String, default="octaos_event")
    trigger_event = Column(String, nullable=True)
    status = Column(String, default="running", index=True)  # running, succeeded, failed, retrying, cancelled

    # Failure Classification & Root Cause
    failure_classification = Column(String, nullable=True)  # user_configuration, workflow_logic, external_service, platform_runtime, security_policy, quota_exceeded
    failure_reason = Column(Text, nullable=True)

    trigger_context = Column(JSON, default=dict)
    inputs = Column(JSON, default=dict)
    outputs = Column(JSON, default=dict)

    duration_ms = Column(Integer, default=0)
    attempt = Column(Integer, default=1)
    max_attempts = Column(Integer, default=3)

    started_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    workflow = relationship("AutomationWorkflow", back_populates="executions")


class AutomationConnection(Base):
    """
    Tenant integration connection status in the OctaOS Connection Center.
    Exposes availability and health without revealing third-party credentials to AI or users.
    """
    __tablename__ = "automation_connections"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    piece_name = Column(String, nullable=False)  # slack, hubspot, google_sheets, gmail, salesforce, octaos
    display_name = Column(String, nullable=False)
    status = Column(String, default="disconnected")  # connected, expired, disconnected
    account_name = Column(String, nullable=True)  # e.g. "Acme Slack (#sales)"
    scopes = Column(JSON, default=list)
    last_verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
