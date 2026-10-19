"""Relational models for the Governed Dynamic Knowledge Connector Platform."""
from __future__ import annotations

import uuid
from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    Integer,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import Base
from app.models import flow_engine  # noqa: F401 - ensures agents table is registered


class KnowledgeConnector(Base):
    """Core connector record managing lifecycle, tenant ownership, and status."""
    __tablename__ = "knowledge_connectors"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    connector_type = Column(String, nullable=False)  # rest_api, postgres, google_sheets, s3, notion, etc.
    state = Column(String, nullable=False, default="draft")  # draft, testing, active, degraded, suspended
    current_config_version = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_connector_tenant_slug"),
        Index("ix_connector_tenant_state", "tenant_id", "state"),
    )

    secret_references = relationship("ConnectorSecretReference", back_populates="connector", cascade="all, delete-orphan")
    config_versions = relationship("ConnectorConfigVersion", back_populates="connector", cascade="all, delete-orphan")
    permissions = relationship("ConnectorPermission", back_populates="connector", cascade="all, delete-orphan")
    executions = relationship("ConnectorExecution", back_populates="connector", cascade="all, delete-orphan")
    schema_versions = relationship("ConnectorSchemaVersion", back_populates="connector", cascade="all, delete-orphan")
    audit_events = relationship("ConnectorAuditEvent", back_populates="connector", cascade="all, delete-orphan")
    cache_entries = relationship("ConnectorCacheEntry", back_populates="connector", cascade="all, delete-orphan")


class ConnectorSecretReference(Base):
    """Encrypted secret references backed by envelope encryption."""
    __tablename__ = "connector_secret_references"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    connector_id = Column(String, ForeignKey("knowledge_connectors.id"), nullable=False, index=True)
    secret_provider = Column(String, nullable=False, default="fernet_vault")  # fernet_vault, aws_kms, gcp_kms, vault
    secret_ref = Column(String, nullable=True)  # Optional remote KMS key ARN or Vault path
    encrypted_key_material = Column(Text, nullable=False)  # AES-256 / MultiFernet encrypted JSON string
    version = Column(Integer, nullable=False, default=1)
    rotation_status = Column(String, nullable=False, default="current")  # current, rotating, retired, revoked

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    connector = relationship("KnowledgeConnector", back_populates="secret_references")


class ConnectorConfigVersion(Base):
    """Versioned endpoint settings, parameter schemas, and extraction rules."""
    __tablename__ = "connector_config_versions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    connector_id = Column(String, ForeignKey("knowledge_connectors.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    endpoint_template = Column(String, nullable=True)  # e.g. "https://api.acme.com/v1/customers?email={email}"
    http_method = Column(String, nullable=False, default="GET")
    parameter_schema = Column(JSON, default=dict)  # {"email": {"type": "string", "required": True}}
    extraction_rules = Column(JSON, default=dict)  # {"jsonpath": "$.data", "max_depth": 5}
    allowed_query_templates = Column(JSON, default=list)  # For SQL/DB: list of parameterized query templates
    timeout_seconds = Column(Integer, nullable=False, default=10)
    max_response_bytes = Column(Integer, nullable=False, default=2 * 1024 * 1024)  # 2MB streaming cap
    allow_redirects = Column(Boolean, nullable=False, default=False)
    cache_ttl_seconds = Column(Integer, nullable=False, default=300)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    connector = relationship("KnowledgeConnector", back_populates="config_versions")
    __table_args__ = (
        UniqueConstraint("connector_id", "version", name="uq_connector_config_version"),
    )


class ConnectorPermission(Base):
    """Granular access control per agent, department, and field visibility."""
    __tablename__ = "connector_permissions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    connector_id = Column(String, ForeignKey("knowledge_connectors.id"), nullable=False, index=True)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=True, index=True)  # Null = All agents in department
    department = Column(String, nullable=False, default="general")  # sales, support, hr, marketing, general
    allowed_operations = Column(JSON, default=lambda: ["read"])  # ["read", "search", "describe"]
    permitted_fields = Column(JSON, default=list)  # Empty list = all non-denied fields
    denied_fields = Column(JSON, default=list)  # Explicitly masked/redacted fields (e.g. ["ssn", "password", "bank_account"])
    requires_human_approval = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    connector = relationship("KnowledgeConnector", back_populates="permissions")


class ConnectorExecution(Base):
    """Audit log of every live execution with byte, record, and timing metrics."""
    __tablename__ = "connector_executions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    connector_id = Column(String, ForeignKey("knowledge_connectors.id"), nullable=False, index=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    request_id = Column(String, nullable=False, index=True)
    acting_agent_id = Column(String, nullable=True, index=True)
    acting_user_id = Column(String, nullable=True, index=True)
    status = Column(String, nullable=False)  # success, partial, stale, denied, timeout, error
    duration_ms = Column(Integer, nullable=False, default=0)
    bytes_received = Column(Integer, nullable=False, default=0)
    records_returned = Column(Integer, nullable=False, default=0)
    truncated = Column(Boolean, nullable=False, default=False)
    truncation_reason = Column(String, nullable=True)
    error_code = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    provenance = Column(JSON, default=list)

    executed_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    connector = relationship("KnowledgeConnector", back_populates="executions")


class ConnectorSchemaVersion(Base):
    """Schema fingerprint tracking and drift detection."""
    __tablename__ = "connector_schema_versions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    connector_id = Column(String, ForeignKey("knowledge_connectors.id"), nullable=False, index=True)
    schema_fingerprint = Column(String, nullable=False, index=True)
    observed_fields = Column(JSON, default=dict)  # {"field_name": "type"}
    inferred_types = Column(JSON, default=dict)
    sample_response_redacted = Column(JSON, nullable=True)
    drift_detected = Column(Boolean, nullable=False, default=False)

    observed_at = Column(DateTime(timezone=True), server_default=func.now())

    connector = relationship("KnowledgeConnector", back_populates="schema_versions")


class ConnectorAuditEvent(Base):
    """Administrative and security audit trail for configuration changes and decisions."""
    __tablename__ = "connector_audit_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    connector_id = Column(String, ForeignKey("knowledge_connectors.id"), nullable=False, index=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    actor_type = Column(String, nullable=False)  # user, agent, system
    actor_id = Column(String, nullable=False)
    event_type = Column(String, nullable=False)  # created, updated, secret_rotated, tested, suspended, access_denied, ssrf_blocked
    event_details = Column(JSON, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    connector = relationship("KnowledgeConnector", back_populates="audit_events")


class ConnectorCacheEntry(Base):
    """Policy-aware cache with tenant, identity, and query isolation."""
    __tablename__ = "connector_cache_entries"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    connector_id = Column(String, ForeignKey("knowledge_connectors.id"), nullable=False, index=True)
    query_hash = Column(String, nullable=False, index=True)
    acting_identity_hash = Column(String, nullable=False, index=True)
    cached_envelope = Column(JSON, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    connector = relationship("KnowledgeConnector", back_populates="cache_entries")
    __table_args__ = (
        Index("ix_cache_tenant_connector_query", "tenant_id", "connector_id", "query_hash"),
    )
