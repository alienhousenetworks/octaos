"""Relational models for OctaOS External Agent Connections, Webhooks, Commands, and Activity Events."""
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


def _id() -> str:
    return str(uuid.uuid4())


class ExternalAgentConnection(Base):
    """
    Registered external agent controller (e.g. Grok Bot, Claude Agent, ChatGPT Custom GPT, n8n webhook).
    Stores endpoint URL, authentication configuration, and status.
    """
    __tablename__ = "external_agent_connections"

    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    endpoint_url = Column(String(500), nullable=False)
    auth_type = Column(String(30), nullable=False, default="bearer")  # bearer | hmac | custom_header
    auth_secret_encrypted = Column(Text, nullable=True)  # Fernet encrypted token or secret
    custom_header_name = Column(String(120), nullable=True)
    enabled = Column(Boolean, default=True)
    description = Column(Text, nullable=True)
    created_by = Column(String, ForeignKey("users.id"), nullable=True)
    last_tested_at = Column(DateTime(timezone=True), nullable=True)
    last_test_status = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_ext_agent_conn_tenant_name"),
    )

    tenant = relationship("Tenant")
    user = relationship("User")
    subscriptions = relationship("WebhookSubscription", back_populates="connection", cascade="all, delete-orphan")


class WebhookSubscription(Base):
    """
    Subscribed event types for an external agent connection.
    """
    __tablename__ = "webhook_subscriptions"

    id = Column(String, primary_key=True, default=_id)
    connection_id = Column(String, ForeignKey("external_agent_connections.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    event_type = Column(String(80), nullable=False, index=True)
    filter_json = Column(JSON, nullable=True)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("connection_id", "event_type", name="uq_webhook_sub_conn_event"),
    )

    connection = relationship("ExternalAgentConnection", back_populates="subscriptions")


class WebhookDelivery(Base):
    """
    Outbound delivery attempt record and idempotency ledger for webhooks.
    """
    __tablename__ = "webhook_deliveries"

    id = Column(String, primary_key=True)  # = envelope id (evt_...)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    connection_id = Column(String, ForeignKey("external_agent_connections.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type = Column(String(80), nullable=False)
    correlation_id = Column(String(120), nullable=True, index=True)
    payload_json = Column(JSON, nullable=False)
    status = Column(String(30), default="pending", index=True)  # pending | delivered | failed | dead
    attempt_count = Column(Integer, default=0)
    next_attempt_at = Column(DateTime(timezone=True), nullable=True, index=True)
    last_http_status = Column(Integer, nullable=True)
    last_error = Column(Text, nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class ControllerCommand(Base):
    """
    Command dispatched by an OctaOS user or AI workforce to an external agent.
    """
    __tablename__ = "controller_commands"

    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    connection_id = Column(String, ForeignKey("external_agent_connections.id", ondelete="SET NULL"), nullable=True, index=True)
    correlation_id = Column(String(120), unique=True, index=True, nullable=False)
    command = Column(Text, nullable=False)
    context_json = Column(JSON, default=dict)
    status = Column(String(30), default="queued", index=True)  # queued | sent | acked | completed | failed
    issued_by = Column(String, nullable=True)
    reply_summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ActivityEvent(Base):
    """
    First-class activity feed event for OctaOS.
    Captures status notes, results, errors, and progress reports from external controllers
    as well as internal AI workforce state changes, with support for media and document attachments.
    """
    __tablename__ = "activity_events"

    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    correlation_id = Column(String(120), nullable=True, index=True)
    source = Column(String(40), default="controller")  # controller | octaos | user | system
    actor = Column(String(120), nullable=False)
    kind = Column(String(40), default="status")  # status | result | error | progress | command | webhook | approval | media
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    attachments_json = Column(JSON, default=list)  # List of {name, url, mime_type, size_bytes}
    data_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
