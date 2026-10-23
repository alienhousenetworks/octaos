"""Django-style RBAC groups and permissions tables.

Revision ID: f8a9b0c1d2e3
Revises: e7f8a9b0c1d2
Create Date: 2026-10-23
"""
from alembic import op
import sqlalchemy as sa


revision = "f8a9b0c1d2e3"
down_revision = "e7f8a9b0c1d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    # Create RBAC tables if not existing
    from app.models.base import Base
    import app.models.rbac  # noqa: F401

    rbac_table_names = [
        "permissions",
        "groups",
        "group_permissions",
        "user_groups",
        "user_permissions",
    ]
    tables_to_create = [
        Base.metadata.tables[t] for t in rbac_table_names if t in Base.metadata.tables and t not in tables
    ]

    if tables_to_create:
        Base.metadata.create_all(
            bind=bind,
            tables=tables_to_create,
            checkfirst=True,
        )

    # Add columns to users table if not already present
    if "users" in tables:
        user_cols = {c["name"] for c in inspector.get_columns("users")}
        if "is_staff" not in user_cols:
            op.add_column("users", sa.Column("is_staff", sa.Boolean(), nullable=True, server_default=sa.false()))
        if "department" not in user_cols:
            op.add_column("users", sa.Column("department", sa.String(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    for t in ["user_permissions", "user_groups", "group_permissions", "groups", "permissions"]:
        if t in tables:
            op.drop_table(t)

    if "users" in tables:
        user_cols = {c["name"] for c in inspector.get_columns("users")}
        if "is_staff" in user_cols:
            op.drop_column("users", "is_staff")
        if "department" in user_cols:
            op.drop_column("users", "department")
