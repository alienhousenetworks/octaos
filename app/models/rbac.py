"""
Django-compatible Role-Based Access Control (RBAC) models.
Defines Permissions, Groups, and Many-to-Many association tables for Groups and Users.
"""
from __future__ import annotations

import uuid
from typing import List
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Table, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


# Association table between Groups and Permissions (like Django's auth_group_permissions)
group_permissions = Table(
    "group_permissions",
    Base.metadata,
    Column("group_id", String, ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", String, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)

# Association table between Users and Groups (like Django's auth_user_groups)
user_groups = Table(
    "user_groups",
    Base.metadata,
    Column("user_id", String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("group_id", String, ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True),
)

# Association table for direct User-specific Permissions (like Django's auth_user_user_permissions)
user_permissions = Table(
    "user_permissions",
    Base.metadata,
    Column("user_id", String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", String, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


class Permission(Base):
    """
    Fine-grained system permission (similar to Django's auth.Permission).
    Format:
      - name: Human-readable display label (e.g. 'Can view leads')
      - codename: Unique identifier (e.g. 'sales.view_leads')
      - content_type: Target module or vertical (e.g. 'sales', 'hr', 'marketing')
    """
    __tablename__ = "permissions"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False)
    codename = Column(String, nullable=False, unique=True, index=True)
    content_type = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "codename": self.codename,
            "content_type": self.content_type,
            "description": self.description or "",
        }


class Group(Base):
    """
    Tenant-scoped Role/Group container (similar to Django's auth.Group).
    Groups bundle a set of permissions that are collectively granted to their member users.
    """
    __tablename__ = "groups"

    id = Column(String, primary_key=True, default=_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_group_tenant_name"),
    )

    # Relationships
    permissions = relationship("Permission", secondary=group_permissions, backref="groups", lazy="selectin")
    users = relationship("User", secondary=user_groups, back_populates="groups", lazy="selectin")

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "description": self.description or "",
            "members_count": len(self.users) if self.users is not None else 0,
            "permissions_count": len(self.permissions) if self.permissions is not None else 0,
            "permission_ids": [p.id for p in self.permissions] if self.permissions else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
