from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
from typing import Optional
import uuid

import contextvars
import contextlib

tenant_context: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("tenant_id", default=None)
org_context: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("organization_id", default=None)

@contextlib.contextmanager
def bypass_tenant_isolation():
    t_token = tenant_context.set(None)
    o_token = org_context.set(None)
    try:
        yield
    finally:
        tenant_context.reset(t_token)
        org_context.reset(o_token)

Base = declarative_base()

class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    subdomain = Column(String, unique=True, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Company fields
    company_website = Column(String, nullable=True)
    company_email = Column(String, nullable=True, unique=True, index=True)
    company_address = Column(String, nullable=True)
    
    users = relationship("User", back_populates="tenant")
    api_credentials = relationship("APICredential", back_populates="tenant")

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    organization_id = Column(String, nullable=True, index=True)
    email = Column(String, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    
    # User Profile & Verification fields
    name = Column(String, nullable=True)
    phone_no = Column(String, nullable=True)
    is_verified = Column(Boolean, default=False)
    otp = Column(String, nullable=True)
    otp_expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # SaaS Multi-Tenancy & Access Control fields
    role = Column(String, default="member")
    allowed_sections = Column(JSON, nullable=True)
    is_system_admin = Column(Boolean, default=False)
    
    tenant = relationship("Tenant", back_populates="users")

class Invitation(Base):
    __tablename__ = "invitations"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    organization_id = Column(String, nullable=True, index=True)
    created_by_id = Column(String, ForeignKey("users.id"), nullable=False)
    email = Column(String, nullable=True)
    token = Column(String, unique=True, index=True, nullable=False)
    is_used = Column(Boolean, default=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    tenant = relationship("Tenant")
    creator = relationship("User", foreign_keys=[created_by_id])


class APICredential(Base):
    __tablename__ = "api_credentials"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    organization_id = Column(String, nullable=True, index=True)
    provider = Column(String, nullable=False) # anthropic, openai, meta, etc.
    encrypted_key = Column(String, nullable=False)
    settings = Column(JSON, default={})
    is_main = Column(Boolean, default=False)
    
    tenant = relationship("Tenant", back_populates="api_credentials")

class ProviderUsage(Base):
    __tablename__ = "provider_usage"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    organization_id = Column(String, nullable=True, index=True)
    provider = Column(String, nullable=False)
    model = Column(String, nullable=False)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    cost = Column(Float, default=0.0)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Cost & Performance metrics
    latency = Column(Float, default=0.0)
    cache_hit = Column(Boolean, default=False)
    cached_tokens = Column(Integer, default=0)
    is_batch = Column(Boolean, default=False)
    task_type = Column(String, default="general") # marketing, sales, support, finance, general
    status = Column(String, default="success") # success, failed, failover
    error_message = Column(String, nullable=True)
    failover_from = Column(String, nullable=True)

class AIBatchJob(Base):
    __tablename__ = "ai_batch_jobs"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    organization_id = Column(String, nullable=True, index=True)
    provider = Column(String, nullable=False)
    model = Column(String, nullable=False)
    status = Column(String, default="pending") # pending, processing, completed, failed
    total_tasks = Column(Integer, default=0)
    completed_tasks = Column(Integer, default=0)
    failed_tasks = Column(Integer, default=0)
    results = Column(JSON, default=[]) # list of task results
    provider_batch_id = Column(String, nullable=True) # ID from provider native batch API
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    tenant = relationship("Tenant")

class SystemSetting(Base):
    __tablename__ = "system_settings"
    key = Column(String, primary_key=True, index=True)
    value = Column(String, nullable=True)


