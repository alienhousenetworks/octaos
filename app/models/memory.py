import uuid
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from app.models.base import Base

class GlobalMemory(Base):
    """
    Stores company-wide truths, guidelines, and rules.
    Read-only for most agents; updated by human managers or the Learning Service.
    """
    __tablename__ = "global_memory"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    
    category = Column(String, nullable=False, index=True) # e.g., "Brand Voice", "ICP", "Compliance"
    rule_name = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class EpisodicMemory(Base):
    """
    Stores past actions and their outcomes (e.g., successful emails, rejected tickets).
    Uses pgvector to allow agents to perform semantic search for similar past situations.
    """
    __tablename__ = "episodic_memory"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    
    department = Column(String, nullable=False, index=True) # e.g., "sales", "support"
    action_type = Column(String, nullable=False) # e.g., "outbound_email", "ticket_reply"
    
    context = Column(Text, nullable=False) # What the agent was trying to do
    action_taken = Column(Text, nullable=False) # What the agent actually did/wrote
    outcome = Column(String, nullable=False) # e.g., "success", "failure", "manager_edited"
    
    # 1536 is standard for OpenAI embeddings, change if using a different embedding model
    embedding = Column(Vector(1536), nullable=True) 
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class CrossAgentContext(Base):
    """
    A real-time blackboard for agents to share state and context with each other.
    """
    __tablename__ = "cross_agent_context"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    
    entity_id = Column(String, nullable=False, index=True) # e.g., a Lead ID or Company Domain
    entity_type = Column(String, nullable=False) # e.g., "lead", "company"
    
    source_agent = Column(String, nullable=False) # Who wrote this (e.g., "support")
    target_agent = Column(String, nullable=True) # Who this is meant for (e.g., "sales", or null for broadcast)
    
    message = Column(Text, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True) # Temporary context expires
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ManagerFeedback(Base):
    """
    Stores the Delta when a human manager edits an agent's drafted action.
    Used by the Learning Service to generate new Global Rules.
    """
    __tablename__ = "manager_feedback"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    
    department = Column(String, nullable=False)
    task_id = Column(String, nullable=True) # Reference to the specific task/execution
    
    original_output = Column(Text, nullable=False)
    edited_output = Column(Text, nullable=False)
    
    manager_comment = Column(Text, nullable=True) # "Too aggressive, soften tone"
    
    is_processed = Column(Boolean, default=False) # Set to True after Learning Service analyzes it
    created_at = Column(DateTime(timezone=True), server_default=func.now())
