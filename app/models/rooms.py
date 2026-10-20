"""Section Rooms model for modular, folder-style departmental workspaces."""
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import Base


class SectionRoom(Base):
    """A scoped room/folder within a section (HR, Marketing, Sales, Support)."""
    __tablename__ = "section_rooms"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    organization_id = Column(String, nullable=True, index=True)

    # Section identifier: 'hr', 'marketing', 'sales', 'support'
    section = Column(String, nullable=False, index=True)

    # Display name e.g. "Senior Full Stack Engineer Hiring", "Q4 Brand Campaign"
    name = Column(String, nullable=False)

    # URL-friendly slug unique per tenant and section
    slug = Column(String, nullable=False, index=True)

    description = Column(Text, nullable=True)
    status = Column(String, default="active", nullable=False)  # active, draft, archived

    # Access control: 'internal_public' | 'private' | 'public'
    visibility = Column(String, default="internal_public", nullable=False)

    # Public sharing token (for public links or external embed)
    share_token = Column(String, nullable=True, unique=True, index=True)

    # Explicit staff permissions: [{"user_id": str, "email": str, "name": str, "role": str, "added_at": str}]
    access_list = Column(JSON, default=list)

    # Section-specific workspace data:
    # HR: {"role": "...", "requirements": "...", "salary": "...", "headcount": 1, ...}
    # Marketing: {"target_audience": "...", "channels": [...], ...}
    # Sales: {"company": "...", "industry": "...", "target_deal": "...", ...}
    # Support: {"sla_hours": 24, "priority": "high", ...}
    data = Column(JSON, default=dict)

    # Creator attribution
    created_by_user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    created_by_user = relationship("User", foreign_keys=[created_by_user_id])

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "section", "slug", name="uq_tenant_section_room_slug"),
    )
