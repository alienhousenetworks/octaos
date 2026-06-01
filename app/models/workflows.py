from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
from app.models.base import Base
import uuid
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

class Workflow(Base):
    __tablename__ = "workflows"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    name = Column(String)
    vertical = Column(String)
    department = Column(String)
    status = Column(String, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    tasks = relationship("WorkflowTask", back_populates="workflow", cascade="all, delete-orphan")

class WorkflowTask(Base):
    __tablename__ = "workflow_tasks"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String, ForeignKey("workflows.id"), nullable=False)
    name = Column(String)
    task_type = Column(String, nullable=True) # e.g. email_sequence, linkedin_dm, yelp_auto_reply
    status = Column(String, default="pending") # pending, in_progress, completed, failed
    result = Column(JSON, nullable=True)
    payload = Column(JSON, nullable=True) # stores arguments/parameters
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    workflow = relationship("Workflow", back_populates="tasks")
