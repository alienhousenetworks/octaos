from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float, Text, JSON
from sqlalchemy.orm import relationship
from app.models.base import Base
import uuid
from sqlalchemy.sql import func

# --- SALES & MARKETING (Phase 1) ---

class Lead(Base):
    __tablename__ = "leads"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    name = Column(String)
    email = Column(String, index=True)
    phone = Column(String)
    company = Column(String)
    source = Column(String)
    score = Column(Integer, default=0)
    status = Column(String, default="captured")
    data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ContentPost(Base):
    __tablename__ = "content_posts"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    platform = Column(String)
    content = Column(Text)
    image_url = Column(String, nullable=True)
    video_url = Column(String, nullable=True)
    day = Column(Integer, nullable=True)
    status = Column(String, default="draft")
    approval_status = Column(String, default="pending") # pending, approved, rejected, published
    scheduled_at = Column(DateTime(timezone=True))
    published_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# --- LEGAL (Phase 4) ---

class Contract(Base):
    __tablename__ = "contracts"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    title = Column(String)
    file_url = Column(String)
    risk_score = Column(String) # Critical, Advisory, Informational
    analysis = Column(JSON)
    approval_status = Column(String, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# --- FINANCE (Phase 4) ---

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    amount = Column(Float)
    currency = Column(String, default="INR")
    description = Column(String)
    is_anomaly = Column(Boolean, default=False)
    category = Column(String)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

# --- HR (Phase 5) ---

class Candidate(Base):
    __tablename__ = "candidates"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    name = Column(String)
    email = Column(String)
    role = Column(String)
    scorecard = Column(JSON)
    status = Column(String, default="sourced") # sourced, screened, interviewed, offered, hired
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# --- SUPPORT (Phase 3) ---

class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    subject = Column(String)
    description = Column(Text)
    status = Column(String, default="open")
    priority = Column(String, default="medium")
    channel = Column(String) # email, whatsapp, chat
    customer_contact = Column(String, nullable=True) # email address or whatsapp number
    approval_status = Column(String, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    messages = relationship("TicketMessage", back_populates="ticket", cascade="all, delete-orphan")

class TicketMessage(Base):
    __tablename__ = "ticket_messages"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    ticket_id = Column(String, ForeignKey("tickets.id"), nullable=False)
    sender = Column(String) # "customer" or "agent"
    content = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    ticket = relationship("Ticket", back_populates="messages")

class AgentMeeting(Base):
    __tablename__ = "agent_meetings"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    title = Column(String, nullable=False)
    status = Column(String, default="active") # active, completed
    trigger_type = Column(String) # support_ticket, transaction_anomaly, candidate_hiring, manual
    trigger_id = Column(String, nullable=True) # ID of ticket, lead, candidate, etc.
    context_summary = Column(Text, nullable=True)
    participants = Column(JSON, nullable=False) # list of agent names e.g., ["Support AI", "Sales AI", "CEO AI"]
    transcript = Column(JSON, default=[]) # list of message objects
    action_items = Column(JSON, default=[]) # list of action item objects
    created_at = Column(DateTime(timezone=True), server_default=func.now())
