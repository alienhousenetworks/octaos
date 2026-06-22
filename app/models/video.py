from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON, Float, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import Base
import uuid

class VideoProject(Base):
    __tablename__ = "video_projects"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    organization_id = Column(String, nullable=True, index=True)
    title = Column(String, nullable=False)
    prompt = Column(Text, nullable=True)
    llm_provider = Column(String, nullable=True)
    llm_model = Column(String, nullable=True)
    status = Column(String, default="draft") # draft, planning, rendering, completed, failed
    duration_seconds = Column(Integer, default=30)
    blueprint = Column(JSON, default={})
    final_video_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    tenant = relationship("Tenant")
    assets = relationship("VideoAsset", back_populates="project", cascade="all, delete-orphan")
    renders = relationship("VideoRender", back_populates="project", cascade="all, delete-orphan")

class VideoAsset(Base):
    __tablename__ = "video_assets"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    project_id = Column(String, ForeignKey("video_projects.id"), nullable=False)
    type = Column(String, nullable=False) # image, audio, logo
    url = Column(String, nullable=False)
    prompt = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    tenant = relationship("Tenant")
    project = relationship("VideoProject", back_populates="assets")

class VideoRender(Base):
    __tablename__ = "video_renders"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("video_projects.id"), nullable=False)
    status = Column(String, default="processing") # processing, success, error
    progress = Column(Float, default=0.0)
    error_logs = Column(Text, nullable=True)
    render_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    project = relationship("VideoProject", back_populates="renders")
