"""Relational models for the Governed Dynamic MCP Platform."""
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


class SystemMCPCredential(Base):
    """
    Client credential for external AI/software connecting to OctaOS MCP.
    Stores hashed credentials, scoped role, client type, and rate limits.
    """
    __tablename__ = "system_mcp_credentials"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    name = Column(String, nullable=False)  # e.g. "Claude Desktop - Strategy", "Cursor Local Dev"
    client_type = Column(String, default="generic")  # claude_desktop, cursor, windsurf, zed, langchain, n8n, custom
    key_hash = Column(String, nullable=False, unique=True, index=True)  # SHA-256 hash
    key_prefix = Column(String, nullable=False)  # e.g. "octa_mcp_3f8a"
    role = Column(String, default="read_only")  # read_only, standard_operator, admin, custom
    rate_limit_rpm = Column(Integer, default=120)
    max_records_per_query = Column(Integer, default=100)
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    tenant = relationship("Tenant")
    user = relationship("User")
    grants = relationship("CapabilityGrant", back_populates="credential", cascade="all, delete-orphan")


class DynamicConnector(Base):
    """
    Registered data source (OctaOS Internal, REST/OpenAPI, GraphQL, PostgreSQL).
    """
    __tablename__ = "dynamic_connectors"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False, index=True)
    connector_type = Column(String, nullable=False)  # internal_octaos, rest_openapi, graphql, postgres
    is_read_only = Column(Boolean, default=False)
    encrypted_config = Column(Text, nullable=True)  # MultiFernet encrypted connection secrets / headers
    status = Column(String, default="active")  # active, degraded, suspended, drift_detected
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_dynamic_connector_tenant_slug"),
    )
    objects = relationship("DynamicObjectDefinition", back_populates="connector", cascade="all, delete-orphan")


class DynamicObjectDefinition(Base):
    """
    Discovered business object (e.g. lead, ticket, customer_account, invoice).
    Stores versioned JSON Schema definitions and relationships.
    """
    __tablename__ = "dynamic_object_definitions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    connector_id = Column(String, ForeignKey("dynamic_connectors.id"), nullable=False, index=True)
    object_name = Column(String, nullable=False, index=True)  # e.g. "lead", "ticket", "customer_account"
    display_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    primary_key_field = Column(String, default="id")
    supported_operations = Column(JSON, default=lambda: ["read", "query"])  # ["discover", "read", "query", "create", "update", "delete", "invoke"]
    schema_fingerprint = Column(String, nullable=False)  # SHA-256 of fields definition
    schema_json = Column(JSON, nullable=False)  # Full JSON Schema definition for record validation
    relationships = Column(JSON, default=dict)  # e.g. {"company": {"target_object": "account", "type": "many_to_one"}}
    is_stale = Column(Boolean, default=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    connector = relationship("DynamicConnector", back_populates="objects")
    __table_args__ = (
        UniqueConstraint("tenant_id", "connector_id", "object_name", name="uq_dynamic_obj_tenant_conn_name"),
    )


class CapabilityGrant(Base):
    """
    Fine-grained permission grant for a principal/credential on a specific object and fields.
    """
    __tablename__ = "mcp_capability_grants"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    credential_id = Column(String, ForeignKey("system_mcp_credentials.id"), nullable=False, index=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    connector_slug = Column(String, nullable=False)  # or "*" for all
    object_name = Column(String, nullable=False)  # or "*" for all
    allowed_actions = Column(JSON, default=lambda: ["read", "query"])  # read, query, create, update, delete, invoke
    permitted_fields = Column(JSON, default=list)  # empty list = all non-denied fields
    denied_fields = Column(JSON, default=list)  # sensitive fields blocked / redacted
    requires_approval = Column(Boolean, default=False)

    credential = relationship("SystemMCPCredential", back_populates="grants")
