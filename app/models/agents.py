from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from app.models.base import Base
import uuid
from sqlalchemy.sql import func

class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    department = Column(String, nullable=False) # e.g. "Marketing", "General"
    doc_type = Column(String, nullable=False) # e.g. "Brand Guidelines", "FAQ", "Pricing"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ActivityLog(Base):
    __tablename__ = "activity_logs"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    agent_name = Column(String, nullable=False) # e.g. "Marketing AI", "Orchestrator AI"
    action = Column(String, nullable=False)
    description = Column(Text)
    status = Column(String, default="success") # success, pending, failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
