"""Durable, tenant-scoped Orchestra data intelligence runs and source artifacts."""
import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON, Text, Float, Index
from sqlalchemy.sql import func
from app.models.base import Base


class DataAnalysisRun(Base):
    __tablename__ = "data_analysis_runs"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    created_by_user_id = Column(String, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    status = Column(String(24), nullable=False, default="queued", index=True)
    idempotency_key = Column(String(128), nullable=True)
    request_fingerprint = Column(String(64), nullable=False)
    file_count = Column(Integer, nullable=False, default=0)
    total_bytes = Column(Integer, nullable=False, default=0)
    profile = Column(JSON, nullable=False, default=dict)
    findings = Column(JSON, nullable=False, default=list)
    report = Column(JSON, nullable=False, default=dict)
    error_code = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    __table_args__ = (Index("ix_data_analysis_tenant_created", "tenant_id", "created_at"),)


class DataAnalysisArtifact(Base):
    __tablename__ = "data_analysis_artifacts"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String(36), ForeignKey("data_analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    filename = Column(String(512), nullable=False)
    media_type = Column(String(255), nullable=False)
    sha256 = Column(String(64), nullable=False, index=True)
    byte_size = Column(Integer, nullable=False)
    extraction_status = Column(String(24), nullable=False)
    extraction_summary = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
