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
    organization_id = Column(String, nullable=True, index=True)
    name = Column(String)
    email = Column(String, index=True)
    phone = Column(String)
    company = Column(String)
    source = Column(String)
    score = Column(Integer, default=0)
    status = Column(String, default="captured")
    personal_email = Column(String, nullable=True)
    company_email = Column(String, nullable=True)
    mobile_no = Column(String, nullable=True)
    company_contact_no = Column(String, nullable=True)
    need_of_what = Column(Text, nullable=True)
    how_much = Column(String, nullable=True)
    why = Column(Text, nullable=True)
    target_context = Column(Text, nullable=True)
    priority = Column(String, default="medium")
    assigned_to = Column(String, default="Sales AI Agent", nullable=True)
    data = Column(JSON)
    sales_company_id = Column(String, ForeignKey("sales_companies.id"), nullable=True, index=True)
    sales_contact_id = Column(String, ForeignKey("sales_account_contacts.id"), nullable=True)
    sales_opportunity_id = Column(String, ForeignKey("sales_opportunities.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class ContentPost(Base):
    __tablename__ = "content_posts"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    organization_id = Column(String, nullable=True, index=True)
    platform = Column(String)
    content = Column(Text)
    image_url = Column(String, nullable=True)
    video_url = Column(String, nullable=True)
    media_prompt = Column(Text, nullable=True)
    media_prompt_enabled = Column(Boolean, default=False)
    image_prompt = Column(Text, nullable=True)
    image_prompt_enabled = Column(Boolean, default=False)
    video_prompt = Column(Text, nullable=True)
    video_prompt_enabled = Column(Boolean, default=False)
    remotion_prompt = Column(Text, nullable=True)
    remotion_prompt_enabled = Column(Boolean, default=False)
    remotion_provider = Column(String, default="gemini")
    remotion_model = Column(String, default="gemini-2.5-flash")

    is_manual_media = Column(Boolean, default=False)
    day = Column(Integer, nullable=True)
    status = Column(String, default="draft")
    approval_status = Column(String, default="pending") # pending, approved, rejected, published
    scheduled_at = Column(DateTime(timezone=True))
    published_at = Column(DateTime(timezone=True))
    # Platform publish + analytics
    external_post_id = Column(String, nullable=True, index=True)  # FB/IG/LinkedIn id after publish
    external_url = Column(String, nullable=True)
    impressions = Column(Float, default=0.0)
    reach = Column(Float, default=0.0)
    engagement = Column(Float, default=0.0)  # likes+comments+shares+saves aggregate
    likes = Column(Float, default=0.0)
    comments = Column(Float, default=0.0)
    shares = Column(Float, default=0.0)
    clicks = Column(Float, default=0.0)
    ctr = Column(Float, default=0.0)  # clicks / impressions
    engagement_rate = Column(Float, default=0.0)  # engagement / impressions
    performance_score = Column(Float, default=0.0)  # 0-100 learned quality signal
    insights_raw = Column(JSON, default=dict)
    insights_synced_at = Column(DateTime(timezone=True), nullable=True)
    learning_tags = Column(JSON, default=list)  # e.g. ["question_hook", "short_cta"]
    # Model tracking & fallback provenance
    used_model = Column(String, nullable=True)  # Concrete model slug used
    fallback_reason = Column(Text, nullable=True)  # Fallback alert note if applicable
    cost_usd = Column(Float, default=0.0)  # Estimated or actual cost
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TenantModelRegistry(Base):
    """Tenant-specific registry for curated and custom Bring-Your-Own-Model entries."""
    __tablename__ = "tenant_model_registry"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    provider = Column(String, nullable=False, index=True)  # openrouter, together
    slug = Column(String, nullable=False, index=True)
    modality = Column(String, nullable=False)  # text, image, video
    mode = Column(String, default="text_to_text")  # text_to_text, text_to_image, image_to_image, text_to_video, image_to_video
    status = Column(String, default="available")  # available | incompatible | not_found | unverified | disabled
    capabilities = Column(JSON, default=dict)
    pricing = Column(JSON, default=dict)
    source = Column(String, default="curated")  # curated | custom
    last_verified_at = Column(DateTime(timezone=True), server_default=func.now())
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class GenerationJob(Base):
    """Asynchronous media generation jobs (video, image-to-video, heavy render)."""
    __tablename__ = "generation_jobs"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    post_id = Column(String, ForeignKey("content_posts.id"), nullable=True, index=True)
    kind = Column(String, default="video")  # video | image | remotion
    provider = Column(String, nullable=False)  # openrouter | together
    model = Column(String, nullable=False)
    request_payload = Column(JSON, default=dict)
    provider_job_id = Column(String, nullable=True, index=True)
    status = Column(String, default="queued")  # queued | in_progress | completed | failed
    attempts = Column(Integer, default=0)
    result_url = Column(String, nullable=True)
    error = Column(Text, nullable=True)
    cost_estimate = Column(Float, default=0.0)
    cost_actual = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MarketingInsightSnapshot(Base):
    """Time-series snapshots of post performance for learning curves."""
    __tablename__ = "marketing_insight_snapshots"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    post_id = Column(String, ForeignKey("content_posts.id"), nullable=False, index=True)
    platform = Column(String, nullable=True)
    impressions = Column(Float, default=0.0)
    reach = Column(Float, default=0.0)
    engagement = Column(Float, default=0.0)
    likes = Column(Float, default=0.0)
    comments = Column(Float, default=0.0)
    shares = Column(Float, default=0.0)
    clicks = Column(Float, default=0.0)
    ctr = Column(Float, default=0.0)
    engagement_rate = Column(Float, default=0.0)
    raw = Column(JSON, default=dict)
    captured_at = Column(DateTime(timezone=True), server_default=func.now())


class MarketingLearningPattern(Base):
    """What works / fails for this tenant — used to improve generation prompts."""
    __tablename__ = "marketing_learning_patterns"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    platform = Column(String, nullable=True, index=True)  # linkedin, facebook, instagram, or null=all
    pattern_type = Column(String, nullable=False)  # hook_style, cta, length, emoji, media_type, topic
    pattern_key = Column(String, nullable=False)  # e.g. "question_open", "short_cta", "with_image"
    sample_count = Column(Integer, default=0)
    avg_engagement_rate = Column(Float, default=0.0)
    avg_ctr = Column(Float, default=0.0)
    avg_performance_score = Column(Float, default=0.0)
    weight = Column(Float, default=0.0)  # positive = boost, negative = avoid
    examples = Column(JSON, default=list)  # short content samples
    banned = Column(Boolean, default=False)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# --- LEGAL (Phase 4) ---

class Contract(Base):
    __tablename__ = "contracts"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    organization_id = Column(String, nullable=True, index=True)
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
    organization_id = Column(String, nullable=True, index=True)
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
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    organization_id = Column(String, nullable=True, index=True)
    name = Column(String)
    email = Column(String)
    phone = Column(String, nullable=True)
    role = Column(String)
    scorecard = Column(JSON)
    status = Column(String, default="sourced") # sourced, screened, interviewed, offered, hired
    merged_into_candidate_id = Column(String, ForeignKey("candidates.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class HRResumeIngestionJob(Base):
    __tablename__ = "hr_resume_ingestion_jobs"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    role = Column(String)
    total_files = Column(Integer, default=0)
    processed_files = Column(Integer, default=0)
    progress_percent = Column(Integer, default=0)
    current_file = Column(String, nullable=True)
    status = Column(String, default="running")  # running, completed, failed
    logs = Column(JSON, default=list)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# --- SUPPORT (Phase 3) ---

class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    organization_id = Column(String, nullable=True, index=True)
    subject = Column(String)
    description = Column(Text)
    status = Column(String, default="open") # open, pending_human, human_handling, resolved, closed
    priority = Column(String, default="medium")
    channel = Column(String) # email, whatsapp, chat, widget
    customer_contact = Column(String, nullable=True) # email address or whatsapp number
    customer_name = Column(String, nullable=True)
    customer_email = Column(String, nullable=True)
    customer_phone = Column(String, nullable=True)
    claimed_by = Column(String, nullable=True) # user_id of claiming agent
    claimed_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    session_id = Column(String, nullable=True, index=True)
    mode = Column(String, default="ai") # ai, human
    extra_data = Column(JSON, default=dict)
    approval_status = Column(String, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Conversation Ownership & Multi-Channel Handoff
    owner_type = Column(String, default="ai") # "ai", "pending_human", "human_handling", "waiting_customer", "escalated", "resolved"
    handoff_started_at = Column(DateTime(timezone=True), nullable=True)
    handoff_deadline_at = Column(DateTime(timezone=True), nullable=True)
    handoff_generation = Column(Integer, default=0)
    customer_id = Column(String, ForeignKey("support_customers.id"), nullable=True, index=True)

    messages = relationship("TicketMessage", back_populates="ticket", cascade="all, delete-orphan")
    customer = relationship("SupportCustomer", back_populates="tickets", foreign_keys=[customer_id])

class TicketMessage(Base):
    __tablename__ = "ticket_messages"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    ticket_id = Column(String, ForeignKey("tickets.id"), nullable=False)
    sender = Column(String) # "customer", "agent", or "system"
    content = Column(Text)
    direction = Column(String, default="inbound") # "inbound", "outbound", "internal_note"
    channel = Column(String, nullable=True) # "whatsapp", "email", "widget"
    provider_message_id = Column(String, nullable=True, index=True)
    delivery_status = Column(String, default="sent") # "received", "queued", "sent_to_provider", "delivered", "failed"
    extra_data = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    ticket = relationship("Ticket", back_populates="messages")

class SupportCustomer(Base):
    __tablename__ = "support_customers"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    display_name = Column(String, nullable=True)
    primary_email = Column(String, nullable=True, index=True)
    primary_phone = Column(String, nullable=True, index=True)
    verified = Column(Boolean, default=False)
    extra_data = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    tickets = relationship("Ticket", back_populates="customer", cascade="all, delete-orphan")
    identities = relationship("SupportCustomerIdentity", back_populates="customer", cascade="all, delete-orphan")

class SupportCustomerIdentity(Base):
    __tablename__ = "support_customer_identities"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    customer_id = Column(String, ForeignKey("support_customers.id"), nullable=False, index=True)
    channel = Column(String, nullable=False) # "whatsapp", "email", "widget"
    normalized_identifier = Column(String, nullable=False, index=True) # E.164 phone or lowercase email
    verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    customer = relationship("SupportCustomer", back_populates="identities")

class SupportAgentPresence(Base):
    __tablename__ = "support_agent_presences"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    user_name = Column(String, nullable=True)
    is_online = Column(Boolean, default=True)
    last_heartbeat = Column(DateTime(timezone=True), server_default=func.now())

class AgentMeeting(Base):
    __tablename__ = "agent_meetings"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    organization_id = Column(String, nullable=True, index=True)
    title = Column(String, nullable=False)
    status = Column(String, default="active")
    # active | awaiting_approval | completed | failed | cancelled
    current_phase = Column(String, nullable=True)
    # assembly | evidence | analysis | critique | synthesis | approval | execution | completed
    trigger_type = Column(String) # support_ticket, transaction_anomaly, candidate_hiring, manual
    trigger_id = Column(String, nullable=True) # ID of ticket, lead, candidate, etc.
    context_summary = Column(Text, nullable=True)
    participants = Column(JSON, nullable=False) # list of agent names e.g., ["Support AI", "Sales AI", "CEO AI"]
    transcript = Column(JSON, default=[]) # kept for backward compat; superseded by meeting_events
    action_items = Column(JSON, default=[]) # kept for backward compat; superseded by meeting_actions
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    total_tokens = Column(Integer, default=0)
    total_cost_usd = Column(Float, default=0.0)
    failure_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class BusinessProfile(Base):
    __tablename__ = "business_profiles"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    organization_id = Column(String, nullable=True, index=True)
    company_name = Column(String, nullable=True)
    website = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    service_description = Column(Text, nullable=True)
    target_countries = Column(JSON, nullable=True)
    target_industries = Column(JSON, nullable=True)
    target_company_size = Column(String, nullable=True)
    target_budget_range = Column(String, nullable=True)
    target_decision_makers = Column(JSON, nullable=True)
    usp = Column(Text, nullable=True)
    case_studies = Column(Text, nullable=True)
    offer_details = Column(Text, nullable=True)
    calendars = Column(JSON, nullable=True)
    communication_channels = Column(JSON, nullable=True)
    extra_context = Column(Text, nullable=True)
    v3_workflow_status = Column(JSON, nullable=True)
    sales_emails = Column(JSON, nullable=True)
    support_emails = Column(JSON, nullable=True)
    lead_freshness = Column(String, default="30_days", nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Contact(Base):
    __tablename__ = "contacts"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    organization_id = Column(String, nullable=True, index=True)
    name = Column(String, nullable=True)
    email = Column(String, index=True, nullable=True)
    phone = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Campaign(Base):
    __tablename__ = "campaigns"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    organization_id = Column(String, nullable=True, index=True)
    name = Column(String, nullable=False)
    status = Column(String, default="draft")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Message(Base):
    __tablename__ = "messages"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    organization_id = Column(String, nullable=True, index=True)
    sender = Column(String, nullable=True)
    recipient = Column(String, nullable=True)
    content = Column(Text, nullable=True)
    channel = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Meeting(Base):
    __tablename__ = "meetings"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    organization_id = Column(String, nullable=True, index=True)
    title = Column(String, nullable=False)
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Integration(Base):
    __tablename__ = "integrations"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    organization_id = Column(String, nullable=True, index=True)
    provider = Column(String, nullable=False)
    config = Column(JSON, default={})
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    organization_id = Column(String, nullable=True, index=True)
    user_id = Column(String, nullable=True)
    action = Column(String, nullable=False)
    resource = Column(String, nullable=True)
    resource_id = Column(String, nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# Lead foreign keys point at sales_* tables. Importing them here registers those
# tables on Base.metadata before create_all or Alembic autogenerate runs.
import app.models.sales_intelligence  # noqa: E402, F401
import app.models.hr  # noqa: E402, F401

