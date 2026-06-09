from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import uuid

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
    company_email = Column(String, nullable=True)
    company_address = Column(String, nullable=True)
    
    users = relationship("User", back_populates="tenant")
    api_credentials = relationship("APICredential", back_populates="tenant")

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
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
    
    tenant = relationship("Tenant", back_populates="users")

class APICredential(Base):
    __tablename__ = "api_credentials"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    provider = Column(String, nullable=False) # anthropic, openai, meta, etc.
    encrypted_key = Column(String, nullable=False)
    settings = Column(JSON, default={})
    
    tenant = relationship("Tenant", back_populates="api_credentials")

class ProviderUsage(Base):
    __tablename__ = "provider_usage"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
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

